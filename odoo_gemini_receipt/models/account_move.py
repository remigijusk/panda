import requests
import json
import base64
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_scan_receipt_ai(self):
        self.ensure_one()
        
        # Pasiimame parametrus iš nustatymų
        api_key = self.env['ir.config_parameter'].sudo().get_param('gemini.api.key')
        model_id = self.env['ir.config_parameter'].sudo().get_param('gemini.model', 'gemini-2.5-flash')

        if not api_key:
            raise UserError(_("Sistemos parametruose nerastas 'gemini.api.key'!"))

        # Surandame nuotrauką arba PDF
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('mimetype', 'ilike', 'image')
        ], limit=1)
        
        if not attachment:
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', self.id),
                ('mimetype', 'ilike', 'pdf')
            ], limit=1)

        if not attachment:
            raise UserError(_("Prie šios sąskaitos nėra prisegto kvito nuotraukos ar PDF failo!"))

        # Google užklausa
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        
        prompt = """Extract data from this receipt and return it ONLY in JSON format.
        IMPORTANT: 
        1. Look for any HANDWRITTEN text on the receipt (usually written with a pen). 
        2. Specifically look for vehicle plate numbers (e.g., HTT570, HTT 570).
        3. vendor_name is the SELLER (e.g. Viada, Circle K).
        4. quantity is liters, unit_price is price per liter.
        
        JSON Structure:
        {
            "vendor_name": "string",
            "date": "YYYY-MM-DD",
            "total_without_vat": 0.00,
            "quantity": 0.00,
            "unit_price": 0.00,
            "receipt_number": "string",
            "vehicle_plate": "string"
        }"""

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": attachment.mimetype,
                            "data": attachment.datas.decode('utf-8')
                        }
                    }
                ]
            }]
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code != 200:
                raise UserError(_("Google Klaida: %s") % response.text)

            result = response.json()
            ai_text = result['candidates'][0]['content']['parts'][0]['text']
            
            # Nuvalome AI atsakymą
            clean_json = ai_text.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_json)

            # Surašome pagrindinius duomenis
            vals = {}
            
            # 1. Tiekėjo nustatymas
            if data.get('vendor_name'):
                partner = self.env['res.partner'].search([
                    ('name', 'ilike', data['vendor_name']),
                    ('supplier_rank', '>', 0)
                ], limit=1)
                if not partner:
                    partner = self.env['res.partner'].search([('name', 'ilike', data['vendor_name'])], limit=1)
                
                if partner:
                    vals['partner_id'] = partner.id

            # 2. Datos (Sąskaitos data = Apskaitos data)
            if data.get('date'):
                vals['invoice_date'] = data['date']
                vals['date'] = data['date']
            
            if data.get('receipt_number'):
                vals['ref'] = data['receipt_number']

            # 3. Kiekio ir kainos logika (Sustiprinimas)
            quantity = float(data.get('quantity', 0))
            unit_price = float(data.get('unit_price', 0))
            total_no_vat = float(data.get('total_without_vat', 0))

            # Heuristika: jei kiekis mažesnis už kainą (pvz. 1.45 ltr už 70 eur), greičiausiai jie sumaišyti
            if quantity > 0 and unit_price > 0 and quantity < unit_price:
                # Sukeičiame vietomis, nes kuras paprastai perkamas litrais (didelis skaičius), o kaina yra maža
                quantity, unit_price = unit_price, quantity
            
            # Jei AI negrąžino unit_price, bet turime sumą ir kiekį
            if unit_price == 0 and quantity > 0:
                unit_price = total_no_vat / quantity

            # 4. Automobilio paieška pagal numerį
            vehicle_id = False
            plate_for_msg = ""
            if data.get('vehicle_plate'):
                import re
                plate_raw = data['vehicle_plate'].upper()
                plate_clean = re.sub(r'[^A-Z0-9]', '', plate_raw)
                plate_for_msg = plate_clean
                
                # Ieškome fleet.vehicle (pagal numerį arba pavadinimą)
                vehicle = self.env['fleet.vehicle'].search([
                    '|', ('license_plate', 'ilike', plate_clean),
                    ('name', 'ilike', plate_clean)
                ], limit=1)
                
                # Jei neradome tikslaus, bandom ieškoti su originaliu tekstu (jei Odoo numeris su tarpais)
                if not vehicle:
                    vehicle = self.env['fleet.vehicle'].search([
                        '|', ('license_plate', 'ilike', plate_raw),
                        ('name', 'ilike', plate_raw)
                    ], limit=1)
                
                if vehicle:
                    vehicle_id = vehicle.id
                    plate_for_msg = vehicle.display_name

            # 5. Matavimo vienetas (Litrai)
            uom_liters = self.env['uom.uom'].search([('name', 'ilike', 'litr')], limit=1)
            
            # 6. Mokesčiai (Pirkimo 21%)
            tax_21 = self.env['account.tax'].search([
                ('name', 'ilike', '21'),
                ('type_tax_use', '=', 'purchase')
            ], limit=1)

            # Sukuriame sąskaitos eilutę
            line_vals = {
                'name': 'Dyzelinis kuras L.',
                'quantity': quantity,
                'price_unit': unit_price,
            }
            if vehicle_id:
                line_vals['vehicle_id'] = vehicle_id
            if uom_liters:
                line_vals['product_uom_id'] = uom_liters.id
            if tax_21:
                line_vals['tax_ids'] = [fields.Command.set([tax_21.id])]

            vals['invoice_line_ids'] = [fields.Command.clear(), fields.Command.create(line_vals)]

            self.write(vals)
            
            msg = _("Sėkmingai nuskaityta: %s") % data.get('vendor_name', 'Nežinomas')
            if vehicle_id:
                msg += _(" (Automobilis: %s)") % plate_for_msg

            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': msg,
                    'type': 'rainbow_man',
                }
            }

        except Exception as e:
            _logger.error("Gemini klaida: %s", str(e))
            raise UserError(_("Klaida apdorojant kvitą: %s") % str(e))
