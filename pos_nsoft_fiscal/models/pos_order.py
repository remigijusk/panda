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
        for l in order_data.get('lines', []):
            orig_qty = round(abs(l.get('qty', 0)), 3)
            orig_price = round(abs(l.get('price', 0)), 2)
            line_amt = round(abs(l.get('total', 0)), 2)
            
            # MAGIJA SVERIAMIEMS PRODUKTAMS
            name = l.get('name', 'Prekė')
            if orig_qty != 1.0:
                name = f"{name} ({orig_qty} x {orig_price} EUR)"

            items_list.append({
                'description': name,
                'quantity': 1.0,         # Visada fiksuojame 1
                'unitPrice': line_amt,   # Kaina prilyginama galutinei eilutės sumai
                'lineAmount': line_amt,
                'vatCode': 'A'
            })
        
        total_amount = round(abs(raw_total), 2)
        payments = [{'method': 'cash', 'amount': total_amount}]

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
