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
        total_incl = round(abs(self.amount_total), 2)

        for line in self.lines:
            qty = round(abs(line.qty), 3)
            line_incl = round(abs(line.price_subtotal_incl), 2)

            name = line.full_product_name or line.product_id.display_name or "Preke"

            # Tax group: A=21%, E=9%, F=0% (nSoft single-letter groups)
            tax_rate = 21
            nsoft_vat_group = 'A'
            if line.tax_ids:
                tax = line.tax_ids[0]
                tax_rate = int(round(float(tax.amount)))
                nsoft_vat_group = {21: 'A', 9: 'E', 5: 'A', 0: 'F'}.get(tax_rate, 'A')

            # unitPrice = price per unit incl VAT (= lineAmount / qty)
            unit_price = round(line_incl / qty, 4) if qty else line_incl

            items_list.append({
                'description': name[:50],
                'quantity': qty,
                'unitPrice': round(unit_price, 2),
                'lineAmount': line_incl,
                'vatGroup': nsoft_vat_group,
            })

        # Payment method mapping – use cashFis/cardFis per kasėjo konfigūraciją
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
            payments = [{'method': 'cashFis', 'amount': total_incl}]

        if is_refund:
            payload = {'returns': items_list, 'payments': payments}
            endpoint = '/return'
        else:
            payload = {'sales': items_list, 'payments': payments}
            endpoint = '/receipt'

        url = f"{api_url.rstrip('/')}/cr/{pos_id}{endpoint}"
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        _logger.info("nSoft sending %s: %s", self.name, str(payload)[:300])
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if not response.ok:
                err_msg = ''
                try:
                    err_msg = response.json().get('message', response.text[:200])
                except Exception:
                    err_msg = response.text[:200]
                _logger.error("nSoft atmetė %s: %s", self.name, err_msg)
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
