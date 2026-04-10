# -*- coding: utf-8 -*-
from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    nsoft_receipt_id = fields.Char(string='nSoft Receipt ID', readonly=True, copy=False)

    @api.model
    def action_send_receipt_to_nsoft(self, order_data):
        config_id = order_data.get('config_id')
        if not config_id:
            return {'success': False, 'error': 'Nėra config_id'}
        
        # Saugiai atidarome kasos nustatymus iš duomenų bazės
        config = self.env['pos.config'].browse(config_id)
        
        # Tikriname, ar įjungta nSoft varnelė
        if not config.nsoft_enabled:
            return {'success': True, 'ignored': True}

        api_url = config.nsoft_api_url
        pos_id = config.nsoft_pos_id
        token = config.nsoft_token

        if not token or not api_url or not pos_id:
            return {'success': False, 'error': 'Trūksta nSoft API nustatymų.'}

        true_total = order_data.get('true_total', 0.0)
        is_refund = true_total < 0
        items_list = []
        sum_of_lines = 0.0
        
        for l in order_data.get('lines', []):
            qty = abs(l.get('qty', 0))
            price = abs(l.get('price', 0))
            line_total = abs(l.get('total', 0))
            line_amt = round(line_total, 2)
            sum_of_lines += line_amt
            
            orig_qty = round(qty, 3)
            orig_price = round(price, 2)
            
            name = l.get('name', 'Prekė')
            if orig_qty != 1.0 and orig_qty != 0.0:
                name = f"{name} ({orig_qty} x {orig_price} EUR)"

            item_data = {
                'description': name[:50], # Apsauga nuo per ilgų pavadinimų
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

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                return {'success': True, 'receipt_id': response.json().get('receiptId')}
            return {'success': False, 'error': f"nSoft atmetė: {response.text}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}
