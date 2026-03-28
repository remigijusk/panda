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
        total_sales_incl = 0.0
        for l in order_data.get('lines', []):
            amt = round(l.get('total', 0), 2)
            sales.append({
                'description': l.get('name', 'Prekė'),
                'quantity': round(l.get('qty', 0), 3),
                'unitPrice': round(l.get('price', 0), 2),
                'lineAmount': amt,
                'vatCode': 'A'
            })
            total_sales_incl += amt
        
        total_sales_incl = round(total_sales_incl, 2)

        # 2. Formuojame mokėjimus (Sutvarkome Grąžos ir Metodo problemas)
        processed_payments = []
        remaining_to_pay = total_sales_incl
        raw_payments = order_data.get('payments', [])

        for p in raw_payments:
            if remaining_to_pay <= 0:
                break
                
            p_amount = round(p.get('amount', 0), 2)
            # Jei mokėjimas didesnis nei likusi krepšelio suma (grąža) - apkerpame
            if p_amount > remaining_to_pay:
                p_amount = remaining_to_pay
            
            if p_amount > 0:
                # Keičiame 'card' į 'bank_card', nes 'card' nSoft atmetė
                m_code = p.get('method', 'cash')
                if m_code == 'card':
                    m_code = 'bank_card'
                
                processed_payments.append({
                    'method': m_code,
                    'amount': p_amount
                })
                remaining_to_pay = round(remaining_to_pay - p_amount, 2)

        # Jei po visko liko kokių nors centų paklaida - pridedame prie paskutinio mokėjimo
        if remaining_to_pay != 0 and processed_payments:
            processed_payments[-1]['amount'] = round(processed_payments[-1]['amount'] + remaining_to_pay, 2)

        payload = {
            'sales': sales,
            'payments': processed_payments
        }

        url = f"{api_url.rstrip('/')}/cr/{pos_id}/receipt"
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        try:
            _logger.info("nSoft Request: %s", payload)
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
