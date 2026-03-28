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

        # 1. Formuojame pardavimus
        sales = []
        for l in order_data.get('lines', []):
            sales.append({
                'description': l.get('name', 'Prekė'),
                'quantity': round(l.get('qty', 0), 3),
                'unitPrice': round(l.get('price', 0), 2),
                'lineAmount': round(l.get('total', 0), 2),
                'vatCode': 'A'
            })

        # 2. Formuojame mokėjimus (kad sutaptų su sales suma)
        # nSoft reikalauja, kad suma sutaptų centas į centą
        total_sales = round(sum(s['lineAmount'] for s in sales), 2)
        
        # Paimame realius mokėjimus iš JS
        payments = []
        raw_payments = order_data.get('payments', [])
        
        if raw_payments:
            for p in raw_payments:
                payments.append({
                    'method': p.get('method', 'cash'),
                    'amount': round(p.get('amount', 0), 2)
                })
        else:
            # Apsidraudimas: jei nėra mokėjimų, siunčiame bendrą sumą kaip grynuosius
            payments.append({'method': 'cash', 'amount': total_sales})

        payload = {
            'sales': sales,
            'payments': payments
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
        res = super(PosOrder, self)._order_fields(ui_order)
        if ui_order.get('nsoft_id'):
            res['nsoft_receipt_id'] = ui_order.get('nsoft_id')
        return res
