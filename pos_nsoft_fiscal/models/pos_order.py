# -*- coding: utf-8 -*-
from odoo import models, fields, api
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
    def _process_order(self, order, draft, existing_order=False):
        """Override to send fiscalization request AFTER the order is saved."""
        order_id = super()._process_order(order, draft, existing_order)
        try:
            pos_order = self.browse(order_id)
            if pos_order and pos_order.config_id.nsoft_enabled:
                pos_order._send_to_nsoft()
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
            item_data = {
                'description': name[:50],
                'quantity': 1.0,
                'unitPrice': line_amt,
                'lineAmount': line_amt,
                'vatCode': 'A',
            }
            if is_refund:
                item_data['origDocNumber'] = 1
                item_data['origCRNumber'] = pos_id
                item_data['otherDocNumber'] = "Grazinimas"
            items_list.append(item_data)

        abs_true_total = round(abs(self.amount_total), 2)
        sum_of_lines = round(sum_of_lines, 2)
        rounding_diff = round(abs_true_total - sum_of_lines, 2)

        if rounding_diff != 0.0:
            if rounding_diff > 0:
                rounding_item = {
                    'description': "Apvalinimas",
                    'quantity': 1.0,
                    'unitPrice': abs(rounding_diff),
                    'lineAmount': abs(rounding_diff),
                    'vatCode': 'A',
                }
                if is_refund:
                    rounding_item['origDocNumber'] = 1
                    rounding_item['origCRNumber'] = pos_id
                    rounding_item['otherDocNumber'] = "Grazinimas"
                items_list.append(rounding_item)
            elif items_list:
                items_list[-1]['unitPrice'] = round(items_list[-1]['unitPrice'] + rounding_diff, 2)
                items_list[-1]['lineAmount'] = round(items_list[-1]['lineAmount'] + rounding_diff, 2)

        payment_method = 'cash'
        for payment in self.payment_ids:
            method_name = (payment.payment_method_id.name or '').lower()
            if any(k in method_name for k in ('card', 'kortel', 'bank')):
                payment_method = 'card'
                break

        payments = [{'method': payment_method, 'amount': abs_true_total}]

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
            if response.status_code in [200, 201]:
                receipt_id = response.json().get('receiptId', str(response.status_code))
                self.sudo().write({'nsoft_receipt_id': receipt_id, 'nsoft_error': False})
                _logger.info("nSoft: Sekmingai fiskalizuota. receiptId=%s", receipt_id)
            else:
                err = f"HTTP {response.status_code}: {response.text[:200]}"
                self.sudo().write({'nsoft_error': err})
                _logger.error("nSoft: Serveris atmete – %s", err)
        except requests.exceptions.Timeout:
            err = "Timeout – nSoft serveris neatsakė per 10s"
            self.sudo().write({'nsoft_error': err})
            _logger.error("nSoft: %s", err)
        except Exception as e:
            err = str(e)[:200]
            self.sudo().write({'nsoft_error': err})
            _logger.error("nSoft: Išimtis – %s", err)
