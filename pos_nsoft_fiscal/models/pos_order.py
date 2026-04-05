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
        # 1. Gauname kasos sesiją ir konfigūraciją iš užsakymo duomenų
        session_id = order_data.get('pos_session_id')
        if not session_id:
            return {'success': True, 'ignored': True}
            
        session = self.env['pos.session'].browse(session_id)
        config = session.config_id
        
        # 2. PATIKRA: Ar šiai kasai išvis įjungtas nSoft? Jei ne - tyliai praleidžiame.
        if not config.nsoft_enabled:
            return {'success': True, 'ignored': True}

        # Jei įjungtas - imame šios konkrečios kasos API nustatymus
        api_url = config.nsoft_api_url
        pos_id = config.nsoft_pos_id
        token = config.nsoft_token

        if not token:
            return {'success': False, 'error': 'API Token nerastas šiai kasai.'}

        # Tikroji suma iš JS
        true_total = order_data.get('true_total', 0.0)
        is_refund = true_total < 0

        items_list = []
        sum_of_lines = 0.0
        
        for l in order_data.get('lines', []):
            qty = l.get('qty', 0)
            price = l.get('price', 0)
            line_total = l.get('total', 0)

            # 1 TAISYKLĖ: ABSOLIUČIAI Viskas teigiama (net ir grąžinimuose)
            abs_qty = abs(qty)
            abs_price = abs(price)
            abs_line_total = abs(line_total)

            line_amt = round(abs_line_total, 2)
            sum_of_lines += line_amt
            
            orig_qty = round(abs_qty, 3)
            orig_price = round(abs_price, 2)
            
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

            if is_refund:
                item_data['origDocNumber'] = 1
                item_data['origCRNumber'] = pos_id
                item_data['otherDocNumber'] = "Grąžinimas"

            items_list.append(item_data)
        
        # 2 TAISYKLĖ: Apvalinimų gaudymas
        abs_true_total = round(abs(true_total), 2)
        sum_of_lines = round(sum_of_lines, 2)
        rounding_diff = round(abs_true_total - sum_of_lines, 2)

        # Jei Odoo pritaikė apvalinimą, informuojame nSoft
        if rounding_diff != 0.0:
            if rounding_diff > 0:
                # Pridedame apvalinimo eilutę
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
                # Jei reikia atimti centus, tiesiog pamažiname paskutinės prekės kainą, 
                # kad išvengtume neigiamų skaičių
                if items_list:
                    items_list[-1]['unitPrice'] = round(items_list[-1]['unitPrice'] + rounding_diff, 2)
                    items_list[-1]['lineAmount'] = round(items_list[-1]['lineAmount'] + rounding_diff, 2)

        # Mokėjimas visada lygus tikrajai, teigiamai apvalintai sumai
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
