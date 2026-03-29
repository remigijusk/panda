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
        config = self.env['ir.config_parameter'].sudo()
        api_url = config.get_param('pos_nsoft_fiscal.api_url')
        pos_id = config.get_param('pos_nsoft_fiscal.pos_id')
        token = config.get_param('pos_nsoft_fiscal.api_token')

        if not token:
            return {'success': False, 'error': 'API Token nerastas.'}

        raw_total = sum(l.get('total', 0) for l in order_data.get('lines', []))
        is_refund = raw_total < 0

        items_list = []
        exact_total = 0.0
        
        for l in order_data.get('lines', []):
            line_total = l.get('total', 0)
            qty = l.get('qty', 0)
            price = l.get('price', 0)
            
            if is_refund:
                line_total = abs(line_total)
                qty = abs(qty)
                price = abs(price)

            line_amt = round(line_total, 2)
            exact_total += line_amt
            
            orig_qty = round(qty, 3)
            orig_price = round(price, 2)
            
            name = l.get('name', 'Prekė')
            if orig_qty != 1.0 and orig_qty != 0.0:
                name = f"{name} ({orig_qty} x {orig_price} EUR)"

            item_data = {
                'description': name,
                'quantity': 1.0,         
                'unitPrice': line_amt,   
                'lineAmount': line_amt,
                'vatCode': 'A'
            }

            # Jei tai grąžinimas, pridedame privalomus laukus iš Jūsų nuotraukos!
            if is_refund:
                item_data['origDocNumber'] = 1
                item_data['origCRNumber'] = pos_id
                item_data['otherDocNumber'] = "Grąžinimas"

            items_list.append(item_data)
        
        exact_total = round(exact_total, 2)
        payments = [{'method': 'cash', 'amount': exact_total}]

        if is_refund:
            payload = {'returns': items_list, 'payments': payments}
            endpoint = '/return'
        else:
            payload = {'sales': items_list, 'payments': payments}
            endpoint = '/receipt'

        url = f"{api_url.rstrip('/')}/cr/{pos_id}{endpoint}"
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        try:
            _logger.info(f"Siunčiame į nSoft {endpoint}: {payload}")
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                return {'success': True, 'receipt_id': response.json().get('receiptId')}
            return {'success': False, 'error': f"nSoft atmetė: {response.text}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        if ui_order.get('nsoft_id'):
            res['nsoft_receipt_id'] = ui_order.get('nsoft_id')
        return res
