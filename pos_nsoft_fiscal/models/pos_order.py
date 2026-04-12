# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    nsoft_receipt_id = fields.Char(
        string='nSoft Receipt ID',
        readonly=True,
        copy=False,
        index=True,
    )
    nsoft_error = fields.Char(
        string='nSoft Klaida',
        readonly=True,
        copy=False,
    )

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
        sum_of_lines = 0.0

        for line in self.lines:
            qty = abs(line.qty)
            price = abs(line.price_unit)
            line_amt = round(abs(line.price_subtotal_incl), 2)
            sum_of_lines += line_amt
            name = line.full_product_name or line.product_id.display_name or "Preke"
            if round(qty, 3) != 1.0 and round(qty, 3) != 0.0:
                name = f"{name} ({round(qty, 3)} x {round(price, 2)} EUR)"

            tax_rate = 21
            tax_name = 'PVM21'
            if line.tax_ids:
                tax = line.tax_ids[0]
                tax_rate = int(tax.amount)
                tax_name = f'PVM{tax_rate}'
            tax_amount = round(line_amt - line_amt / (1 + tax_rate / 100), 2)
            base_amount = round(line_amt - tax_amount, 2)

            items_list.append({
                'description': name[:50],
                'quantity': 1.0,
                'unitPrice': line_amt,
                'lineAmount': line_amt,
                'taxes': [{'name': tax_name, 'rate': tax_rate, 'amount': tax_amount, 'base': base_amount}],
            })

        abs_true_total = round(abs(self.amount_total), 2)
        sum_of_lines = round(sum_of_lines, 2)
        rounding_diff = round(abs_true_total - sum_of_lines, 2)
        if abs(rounding_diff) > 0.001:
            if abs(rounding_diff) <= 0.05:
                items_list.append({
                    'description': 'Suapvalinimas',
                    'quantity': 1.0,
                    'unitPrice': rounding_diff,
                    'lineAmount': rounding_diff,
                    'taxes': [{'name': 'PVM21', 'rate': 21, 'amount': 0.0, 'base': rounding_diff}],
                })
            elif items_list:
                items_list[-1]['unitPrice'] = round(items_list[-1]['unitPrice'] + rounding_diff, 2)
                items_list[-1]['lineAmount'] = round(items_list[-1]['lineAmount'] + rounding_diff, 2)

        # Build payments - nSoft types: cashFis, cardFis, voucherFis
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
            payments = [{'method': 'cashFis', 'amount': abs_true_total}]

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
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if not response.ok:
                # nSoft atmetė – keliam klaidą kad Odoo pardavimas nesisaugotų
                err_msg = response.json().get('message', response.text[:200]) if response.text else str(response.status_code)
                _logger.error("nSoft atmetė %s: %s | payload: %s", self.name, err_msg, str(payload)[:200])
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
            raise UserError("i.EKA klaida: Serveris neatsakė laiku (timeout). Bandykite dar kartą.")
        except Exception as e:
            _logger.error("nSoft: Klaida siunčiant %s: %s", self.name, e)
            raise UserError(f"i.EKA klaida: {e}")
