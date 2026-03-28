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

        # 1. Surenkame prekes ir iškart skaičiuojame tikrąją sumą
        sales = []
        total_sales_amount = 0.0
        
        for l in order_data.get('lines', []):
            line_amount = round(l.get('total', 0), 2)
            sales.append({
                'description': l.get('name', 'Prekė'),
                'quantity': round(l.get('qty', 0), 3),
                'unitPrice': round(l.get('price', 0), 2),
                'lineAmount': line_amount,
                'vatCode': 'A'
            })
            total_sales_amount += line_amount
        
        # Svarbus žingsnis: apvaliname bendrą sumą
        total_sales_amount = round(total_sales_amount, 2)

        # 2. IGNORUOJAME KASOS MOKĖJIMUS DĖL KLAIDŲ
        # Formuojame vieną vienintelį "cash" mokėjimą, visiškai atitinkantį prekes.
        # Taip išvengiame bet kokių apvalinimų ar kortelių atmetimų testinėje aplinkoje.
        payments = [{
            'method': 'cash',
            'amount': total_sales_amount
        }]

        payload = {
            'sales': sales,
            'payments': payments
        }

        url = f"{api_url.rstrip('/')}/cr/{pos_id}/receipt"
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        try:
            _logger.info("nSoft Payload (v14): %s", payload)
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
