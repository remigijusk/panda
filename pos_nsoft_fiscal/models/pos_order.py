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

        # 1. Formuojame pardavimo eilutes
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
        
        total_sales_amount = round(total_sales_amount, 2)

        # 2. APDOROJAME MOKĖJIMUS (Sutvarkome Grąžos problemą)
        # nSoft reikalauja, kad mokėjimų suma būtų LYGI pardavimų sumai.
        processed_payments = []
        current_payments_sum = 0.0
        raw_payments = order_data.get('payments', [])

        for p in raw_payments:
            p_amount = round(p.get('amount', 0), 2)
            
            # Jei šis mokėjimas viršija likusią mokėtiną sumą (tai yra grąža)
            if round(current_payments_sum + p_amount, 2) > total_sales_amount:
                p_amount = round(total_sales_amount - current_payments_sum, 2)
            
            if p_amount > 0:
                # nSoft dažnai tikisi 'cash' arba 'card' (mažosiomis)
                # Jei 'card' vis tiek mes klaidą, laikinai viską siųsime kaip 'cash'
                method = p.get('method', 'cash')
                processed_payments.append({
                    'method': method,
                    'amount': p_amount
                })
                current_payments_sum += p_amount

        # Jei dėl kokių nors priežasčių suma vis tiek nesutampa (pvz. apvalinimas)
        # Pakoreguojame paskutinį mokėjimą
        if round(current_payments_sum, 2) != total_sales_amount and processed_payments:
            diff = round(total_sales_amount - current_payments_sum, 2)
            processed_payments[-1]['amount'] = round(processed_payments[-1]['amount'] + diff, 2)

        payload = {
            'sales': sales,
            'payments': processed_payments
        }

        url = f"{api_url.rstrip('/')}/cr/{pos_id}/receipt"
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        try:
            _logger.info("nSoft Payload: %s", payload)
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
