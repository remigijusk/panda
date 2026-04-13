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
        total_payment = round(abs(self.amount_total), 2)

        for line in self.lines:
            qty = abs(line.qty)
            line_incl = round(abs(line.price_subtotal_incl), 2)

            name = line.full_product_name or line.product_id.display_name or "Preke"
            if round(qty, 3) != 1.0 and round(qty, 3) != 0.0:
                unit_price_incl = round(line_incl / qty, 4) if qty else line_incl
                name = f"{name} ({round(qty, 3)} x {round(unit_price_incl, 2)} EUR)"

            # nSoft: unitPrice = price per unit EXCL VAT
            #        lineAmount = qty * unitPrice EXCL VAT
            #        taxes.base = lineAmount (excl VAT)
            #        taxes.amount = VAT amount
            # Tax group names: A=21%, B=9%, C=5%, D=0%
            tax_rate = 21
            nsoft_tax_group = 'A'
            if line.tax_ids:
                tax = line.tax_ids[0]
                tax_rate = int(round(float(tax.amount)))
                nsoft_tax_group = {21: 'A', 9: 'B', 5: 'C', 0: 'D'}.get(tax_rate, 'A')

            divisor = 1 + tax_rate / 100.0
            line_excl = round(line_incl / divisor, 4)
            tax_amount = round(line_incl - line_excl, 4)
            unit_price_excl = round(line_excl / qty, 4) if qty else line_excl

            # Round to 2 decimal places for final values
            line_excl_2 = round(line_excl, 2)
            tax_amount_2 = round(tax_amount, 2)
            unit_price_excl_2 = round(unit_price_excl, 2)

            items_list.append({
                'description': name[:50],
                'quantity': round(qty, 3),
                'unitPrice': unit_price_excl_2,
                'lineAmount': line_excl_2,
                'taxes': [{
                    'name': nsoft_tax_group,
                    'rate': tax_rate,
                    'amount': tax_amount_2,
                    'base': line_excl_2,
                }],
            })

        # Payment method mapping - cashFis for cash, cardFis for card
        # nSoft DEMO CR-000019280 supports: cash (and cashFis for fiscal)
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
            payments = [{'method': 'cashFis', 'amount': total_payment}]

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
        _logger.info("nSoft payload for %s: %s", self.name, str(payload)[:300])
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if not response.ok:
                err_msg = ''
                try:
                    err_msg = response.json().get('message', response.text[:200])
                except Exception:
                    err_msg = response.text[:200]
                _logger.error("nSoft atmetė %s: %s | payload: %s", self.name, err_msg, str(payload)[:300])
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
