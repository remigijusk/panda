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

    def _get_nsoft_vat_group(self, tax_rate):
        """Map Odoo tax rate to nSoft VAT group letter.
        nSoft VAT group mapping depends on CR device configuration.
        Default: A=21%, E=9%, F=0%
        Override nsoft_vat_group_21/9/0 in pos.config if needed."""
        config = self.config_id
        rate = int(round(float(tax_rate)))
        if rate == 21:
            return getattr(config, 'nsoft_vat_group_21', None) or 'A'
        elif rate == 9:
            return getattr(config, 'nsoft_vat_group_9', None) or 'E'
        elif rate == 0:
            return getattr(config, 'nsoft_vat_group_0', None) or 'F'
        else:
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
            qty = abs(line.qty)
            # Use incl VAT prices (price_subtotal_incl)
            line_incl = round(abs(line.price_subtotal_incl), 2)
            unit_incl = round(line_incl / qty, 4) if qty else line_incl
            unit_incl_2 = round(unit_incl, 2)

            name = line.full_product_name or line.product_id.display_name or "Preke"
            if round(qty, 3) != 1.0 and round(qty, 3) != 0.0:
                name = f"{name} ({round(qty, 3)} x {unit_incl_2} EUR)"

            # Determine VAT group
            tax_rate = 21
            if line.tax_ids:
                tax = line.tax_ids[0]
                tax_rate = int(round(float(tax.amount)))
            vat_group = self._get_nsoft_vat_group(tax_rate)

            items_list.append({
                'description': name[:50],
                'quantity': round(qty, 3),
                'unitPrice': unit_incl_2,
                'lineAmount': line_incl,
                'vatGroup': vat_group,
            })

        # Fix rounding – ensure sum of lineAmounts == total
        abs_total = round(abs(self.amount_total), 2)
        sum_lines = round(sum(i['lineAmount'] for i in items_list), 2)
        diff = round(abs_total - sum_lines, 2)
        if abs(diff) > 0.001 and items_list:
            items_list[-1]['lineAmount'] = round(items_list[-1]['lineAmount'] + diff, 2)
            items_list[-1]['unitPrice'] = round(items_list[-1]['lineAmount'] / items_list[-1]['quantity'], 4)

        # Payment methods
        payments = []
        for payment in self.payment_ids:
            method_name = (payment.payment_method_id.name or '').lower()
            amt = round(abs(payment.amount), 2)
            if any(k in method_name for k in ('card', 'kortel', 'bank', 'banko', 'visa', 'master')):
                nsoft_method = 'cardFis'
            elif any(k in method_name for k in ('voucher', 'kupon', 'dovanu', 'wolt')):
                nsoft_method = 'voucherFis'
            else:
                nsoft_method = 'cashFis'
            payments.append({'method': nsoft_method, 'amount': amt})

        if not payments:
            payments = [{'method': 'cashFis', 'amount': abs_total}]

        endpoint = '/return' if is_refund else '/receipt'
        key = 'returns' if is_refund else 'sales'
        payload = {key: items_list, 'payments': payments}

        url = f"{api_url.rstrip('/')}/cr/{pos_id}{endpoint}"
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        _logger.info("nSoft sending %s: %s", self.name, str(payload)[:400])
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if not response.ok:
                err_msg = response.text[:200]
                try:
                    err_msg = response.json().get('message', err_msg)
                except Exception:
                    pass
                _logger.error("nSoft atmetė %s (%s): %s", self.name, response.status_code, err_msg)
                raise UserError(f"i.EKA klaida ({response.status_code}): {err_msg}")
            data = response.json()
            receipt_id = str(
                data.get('content', {}).get('receiptId') or
                data.get('content', {}).get('id') or
                response.status_code
            )
            self.write({'nsoft_receipt_id': receipt_id, 'nsoft_error': False})
            _logger.info("nSoft: Kvitas %s -> receipt_id=%s", self.name, receipt_id)
        except UserError:
            raise
        except requests.Timeout:
            raise UserError("i.EKA klaida: Serveris neatsakė laiku (timeout).")
        except Exception as e:
            _logger.error("nSoft: Klaida siunčiant %s: %s", self.name, e)
            raise UserError(f"i.EKA klaida: {e}")
