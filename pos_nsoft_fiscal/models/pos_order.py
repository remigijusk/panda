# -*- coding: utf-8 -*-
from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def action_send_receipt_to_nsoft(self, order_data):
        """
        Priima POS užsakymo duomenis ir išsiunčia POST užklausą į nSoft API /cr/{id}/receipt.
        """
        # Ištraukiame nustatymus
        config = self.env['ir.config_parameter'].sudo()
        api_url = config.get_param('pos_nsoft_fiscal.api_url', 'https://nvf.app3.nsoft.eu:30032/api')
        pos_id = config.get_param('pos_nsoft_fiscal.pos_id', 'CR-000019280')
        token = config.get_param('pos_nsoft_fiscal.api_token')

        if not token:
            return {'success': False, 'error': 'Nepateiktas nSoft API žetonas (Token) nustatymuose.'}

        # Formuojame pardavimų eilutes (sales)
        sales = []
        for line in order_data.get('lines', []):
            # Formate line[2] slypi eilutės duomenys iš POS frontend'o
            line_val = line[2] if len(line) == 3 else line
            
            # PVM kodo logika (laikinai 'A' standartiniam, reikės pritaikyti pagal jūsų mokesčius)
            vat_code = 'A' if line_val.get('tax_ids') else 'E'

            sales.append({
                'description': line_val.get('full_product_name', 'Prekė'),
                'quantity': round(line_val.get('qty', 1.0), 3), # Palaiko sveriamas prekes
                'unitPrice': round(line_val.get('price_unit', 0.0), 2),
                'lineAmount': round(line_val.get('price_subtotal_incl', 0.0), 2),
                'vatCode': vat_code
            })

        # Formuojame mokėjimus (payments)
        payments = []
        for payment in order_data.get('statement_ids', []):
            pay_val = payment[2] if len(payment) == 3 else payment
            
            # Pagal nutylėjimą priskiriame 'cash' (grynieji)
            # Realiame modulyje tai siesime su payment_method_id
            method = 'cash' 
            
            payments.append({
                'method': method,
                'amount': round(pay_val.get('amount', 0.0), 2)
            })

        payload = {
            'sales': sales,
            'payments': payments
        }

        url = f"{api_url.rstrip('/')}/cr/{pos_id}/receipt"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            # 10s timeout, kad apsaugotume POS nuo pakibimo
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                return {'success': True, 'response': response.json()}
            else:
                _logger.error("nSoft API klaida: %s - %s", response.status_code, response.text)
                return {'success': False, 'error': f'Klaida {response.status_code}: {response.text}'}
        except requests.exceptions.RequestException as e:
            _logger.error("Ryšio klaida su nSoft: %s", str(e))
            return {'success': False, 'error': 'Nepavyko susisiekti su i.EKA serveriu (Ryšio klaida).'}
