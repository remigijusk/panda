# -*- coding: utf-8 -*-
from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    nsoft_receipt_id = fields.Char(string='nSoft Receipt ID', readonly=True, copy=False)

    @api.model
    def _process_saved_order(self, draft):
        # 1. Pirmiausia Odoo išsaugo užsakymą standartiškai
        order_id = super(PosOrder, self)._process_saved_order(draft)
        
        try:
            # Randa ką tik išsaugotą užsakymą
            order = self.browse(order_id)
            if not order:
                return order_id

            session = order.session_id
            config = session.config_id

            # 2. Ar nSoft įjungtas šiai kasai? Jei ne - nieko nedarome, tęsiame toliau.
            if not config.nsoft_enabled:
                return order_id

            # Jei įjungtas - siunčiame
            api_url = config.nsoft_api_url
            pos_id = config.nsoft_pos_id
            token = config.nsoft_token

            if not api_url or not token:
                _logger.error("nSoft klaida: API URL arba Token nėra nustatyti.")
                return order_id

            # Surenkame duomenis
            true_total = order.amount_total
            is_refund = true_total < 0
            items_list = []
            sum_of_lines = 0.0

            for line in order.lines:
                qty = abs(line.qty)
                price = abs(line.price_unit)
                line_total = abs(line.price_subtotal_incl)
                
                line_amt = round(line_total, 2)
                sum_of_lines += line_amt
                
                orig_qty = round(qty, 3)
                orig_price = round(price, 2)
                
                name = line.product_id.display_name or 'Prekė'
                if orig_qty != 1.0 and orig_qty != 0.0:
                    name = f"{name} ({orig_qty} x {orig_price} EUR)"

                item_data = {
                    'description': name,
                    'quantity': 1.0,         
                    'unitPrice': line_amt,   
                    'lineAmount': line_amt,
                    'vatCode': 'A'
                }

                if is_refund:
                    item_data['origDocNumber'] = 1
                    item_data['origCRNumber'] = pos_id
                    item_data['otherDocNumber'] = "Grąžinimas"

                items_list.append(item_data)

            # Apvalinimas
            abs_true_total = round(abs(true_total), 2)
            sum_of_lines = round(sum_of_lines, 2)
            rounding_diff = round(abs_true_total - sum_of_lines, 2)

            if rounding_diff != 0.0:
                if rounding_diff > 0:
                    rounding_item = {
                        'description': "Apvalinimas",
                        'quantity': 1.0,
                        'unitPrice': abs(rounding_diff),
                        'lineAmount': abs(rounding_diff),
                        'vatCode': 'A'
                    }
                    if is_refund:
                        rounding_item['origDocNumber'] = 1
                        rounding_item['origCRNumber'] = pos_id
                        rounding_item['otherDocNumber'] = "Grąžinimas"
                    items_list.append(rounding_item)
                else:
                    if items_list:
                        items_list[-1]['unitPrice'] = round(items_list[-1]['unitPrice'] + rounding_diff, 2)
                        items_list[-1]['lineAmount'] = round(items_list[-1]['lineAmount'] + rounding_diff, 2)

            payments = [{'method': 'cash', 'amount': abs_true_total}]

            if is_refund:
                payload = {'returns': items_list, 'payments': payments}
                endpoint = '/return'
            else:
                payload = {'sales': items_list, 'payments': payments}
                endpoint = '/receipt'

            url = f"{api_url.rstrip('/')}/cr/{pos_id}{endpoint}"
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                # Jei pavyko - įrašome ID į užsakymą
                order.sudo().write({'nsoft_receipt_id': response.json().get('receiptId')})
            else:
                _logger.error(f"nSoft atmetė čekį: {response.text}")

        except Exception as e:
            _logger.error(f"Klaida siunčiant į nSoft: {str(e)}")

        return order_id
