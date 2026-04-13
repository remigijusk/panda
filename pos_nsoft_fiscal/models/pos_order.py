# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    nsoft_receipt_id = fields.Char(string='nSoft Receipt ID', readonly=True, copy=False, index=True)
    nsoft_error = fields.Char(string='nSoft Klaida', readonly=True, copy=False)

    @api.model
    def _process_order(self, order, draft):
        order_id = super()._process_order(order, draft)
        try:
            pos_order = self.browse(order_id)
            if pos_order and pos_order.config_id.nsoft_enabled:
                pos_order._send_to_nsoft()
        except UserError:
            raise
        except Exception as e:
            _logger.error("nSoft: Nepavyko isssiusti uzsakymo %s: %s", order_id, e)
        return order_id

    def _get_nsoft_payment_method(self, payment):
        """Map Odoo payment method to nSoft method string using config fields."""
        config = self.config_id
        name = (payment.payment_method_id.name or '').lower().strip()

        cash_val = (config.nsoft_payment_cash or 'cash').strip()
        card_val = (config.nsoft_payment_card or 'card').strip()
        voucher_val = (config.nsoft_payment_voucher or 'voucher').strip()

        if any(k in name for k in ('card', 'kortel', 'bank', 'banko', 'visa', 'master')):
            return card_val
        if any(k in name for k in ('voucher', 'kupon', 'dovanu', 'wolt', 'bolt')):
            return voucher_val
        return cash_val

    def _get_nsoft_vat_group(self, line, config):
        """Get nSoft VAT group for order line.
        VISADA grazina reiksme - nSoft reikalauja vatGroup kiekviename item.
        Jei nesukonfiguruota - naudojam 'A' kaip default (21% grupė).
        """
        try:
            default_vat = (getattr(config, 'nsoft_vat_group_21', None) or 'A').strip() or 'A'

            if not line.tax_ids:
                # Produktas be PVM - naudojame 0% grupę arba default
                val = (getattr(config, 'nsoft_vat_group_0', None) or '').strip()
                return val if val else default_vat

            rate = int(round(float(line.tax_ids[0].amount)))
            if rate == 21:
                val = (getattr(config, 'nsoft_vat_group_21', None) or '').strip()
                return val if val else 'A'
            elif rate == 9:
                val = (getattr(config, 'nsoft_vat_group_9', None) or '').strip()
                return val if val else 'E'
            elif rate == 0:
                val = (getattr(config, 'nsoft_vat_group_0', None) or '').strip()
                return val if val else 'F'
            else:
                _logger.warning("nSoft: Nezinomas PVM tarifas %s%%, naudojamas default", rate)
                return default_vat
        except Exception as e:
            _logger.warning("nSoft: PVM grupes klaida: %s, naudojamas 'A'", e)
            return 'A'

    def _send_to_nsoft(self):
        self.ensure_one()
        config = self.config_id
        api_url = config.nsoft_api_url
        pos_id = config.nsoft_pos_id
        token = config.nsoft_token

        if not api_url or not pos_id or not token:
            _logger.warning("nSoft: Truksta nustatymu – praleidziama.")
            return

        is_refund = self.amount_total < 0

        items_list = []
        for line in self.lines:
            qty = round(abs(line.qty), 3)
            line_incl = round(abs(line.price_subtotal_incl), 2)
            name = line.full_product_name or line.product_id.display_name or "Preke"

            if qty != 1.0 and qty != 0.0:
                unit_incl = round(line_incl / qty, 2) if qty else line_incl
                name = f"{name} ({qty} x {unit_incl} EUR)"

            vat_group = self._get_nsoft_vat_group(line, config)
            unit_price = round(line_incl / qty, 4) if qty else line_incl

            items_list.append({
                'description': name[:50],
                'quantity': qty,
                'unitPrice': unit_price,
                'lineAmount': line_incl,
                'vatGroup': vat_group,
            })

        # Fix rounding
        total_incl = round(abs(self.amount_total), 2)
        sum_lines = round(sum(i['lineAmount'] for i in items_list), 2)
        diff = round(total_incl - sum_lines, 2)
        if abs(diff) > 0.001 and items_list:
            items_list[-1]['lineAmount'] = round(items_list[-1]['lineAmount'] + diff, 2)
            items_list[-1]['unitPrice'] = round(
                items_list[-1]['lineAmount'] / items_list[-1]['quantity'], 4)

        # Payments
        payments = []
        for payment in self.payment_ids:
            payments.append({
                'method': self._get_nsoft_payment_method(payment),
                'amount': round(abs(payment.amount), 2),
            })
        if not payments:
            payments = [{'method': config.nsoft_payment_cash or 'cash', 'amount': total_incl}]

        endpoint = '/return' if is_refund else '/receipt'
        payload = {
            ('returns' if is_refund else 'sales'): items_list,
            'payments': payments,
        }

        url = f"{api_url.rstrip('/')}/cr/{pos_id}{endpoint}"
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        _logger.info("nSoft %s payload: %s", self.name, str(payload)[:500])

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if not response.ok:
                try:
                    err_msg = response.json().get('message', response.text[:300])
                except Exception:
                    err_msg = response.text[:300]
                _logger.error("nSoft atmetė %s: %s", self.name, err_msg)
                raise UserError(f"i.EKA klaida ({response.status_code}): {err_msg}")

            data = response.json()
            receipt_id = str(
                data.get('content', {}).get('receiptId')
                or data.get('content', {}).get('id')
                or response.status_code
            )
            self.write({'nsoft_receipt_id': receipt_id, 'nsoft_error': False})
            _logger.info("nSoft: Kvitas %s -> id=%s", self.name, receipt_id)

        except UserError:
            raise
        except requests.Timeout:
            raise UserError("i.EKA klaida: Serveris neatsakė laiku (timeout).")
        except Exception as e:
            _logger.error("nSoft klaida %s: %s", self.name, e)
            raise UserError(f"i.EKA klaida: {e}")
