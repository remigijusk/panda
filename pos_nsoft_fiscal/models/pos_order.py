# -*- coding: utf-8 -*-
from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    # Laukas nSoft fiskaliniam numeriui saugoti duomenų bazėje
    nsoft_receipt_id = fields.Char(string='nSoft Receipt ID', readonly=True, copy=False)

    @api.model
    def action_send_receipt_to_nsoft(self, order_data):
        config = self.env['ir.config_parameter'].sudo()
        api_url = config.get_param('pos_nsoft_fiscal.api_url')
        pos_id = config.get_param('pos_nsoft_fiscal.pos_id')
        token = config.get_param('pos_nsoft_fiscal.api_token')

        if not token:
            return {'success': False, 'error': 'API Token nerastas.'}

        sales = []
        for line in order_data.get('lines', []):
            l = line[2] if isinstance(line, list) and len(line) == 3 else line
            sales.append({
                'description': l.get('full_product_name', 'Prekė'),
                'quantity': round(l.get('qty', 1.0), 3),
                'unitPrice': round(l.get('price_unit', 0.0), 2),
                'lineAmount': round(l.get('price_subtotal_incl', 0.0), 2),
                'vatCode': 'A'
            })

        payload = {
            'sales': sales,
            'payments': [{
                'method': 'cash', 
                'amount': round(order_data.get('amount_total', 0.0), 2)
            }]
        }

        url = f"{api_url.rstrip('/')}/cr/{pos_id}/receipt"
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                return {'success': True, 'receipt_id': response.json().get('receiptId')}
            return {'success': False, 'error': f"nSoft atmetė: {response.text}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @api.model
    def _order_fields(self, ui_order):
        """ Ši funkcija paima 'nsoft_id' iš kasos ir įrašo į 'nsoft_receipt_id' duomenų bazėje """
        res = super(PosOrder, self)._order_fields(ui_order)
        if ui_order.get('nsoft_id'):
            res['nsoft_receipt_id'] = ui_order.get('nsoft_id')
        return res
