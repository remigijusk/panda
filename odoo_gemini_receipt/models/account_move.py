import requests
import json
import base64
import logging
import re
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
        1. Look for any HANDWRITTEN text on the receipt (usually vehicle plate numbers).
        2. vendor_vat: Seller's VAT number (e.g. LT100010288216).
        3. total_without_vat: Look for "Be PVM". This is the taxable base.
        4. total_with_vat: Look for "Su PVM" or "Mokėti".
        5. quantity: liters (L).
        6. unit_price: price per liter.
        7. rounding_amount: Look for "Apvalinimas".
        
        JSON Structure:
        {
            "vendor_name": "string",
            "vendor_vat": "string",
            "date": "YYYY-MM-DD",
            "total_without_vat": 0.00,
            "total_with_vat": 0.00,
            "quantity": 0.00,
            "unit_price": 0.00,
            "rounding_amount": 0.00,
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
            
            # 1. Tiekėjo nustatymas (Paieška pagal PVM arba Pavadinimą)
            partner = False
            if data.get('vendor_vat'):
                vat_clean = re.sub(r'[^A-Z0-9]', '', data['vendor_vat'].upper())
                partner = self.env['res.partner'].search([
                    '|', ('vat', 'ilike', vat_clean),
                    ('vat', 'ilike', data['vendor_vat'])
                ], limit=1)
            
            if not partner and data.get('vendor_name'):
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

            # 3. Kiekio ir kainos logika (Odoo 15 principas: Suma be PVM / Kiekis)
            quantity = float(data.get('quantity', 0))
            total_no_vat = float(data.get('total_without_vat', 0))
            
            # Jei AI suklydo ir paėmė sumą su PVM kaip sumą be PVM (dažna klaida)
            total_with_vat = float(data.get('total_with_vat', 0))
            if total_no_vat == total_with_vat and total_no_vat > 0:
                # Perskaičiuojame atgal: Suma su PVM / 1.21
                total_no_vat = total_no_vat / 1.21

            if quantity > 0:
                unit_price = total_no_vat / quantity
            else:
                unit_price = total_no_vat
                quantity = 1.0

            # 3.1 Grynųjų pinigų apvalinimas (nuo 2025 m.)
            if 'cash_rounding_id' in self._fields:
                try:
                    rounding_raw = data.get('rounding_amount', 0)
                    if isinstance(rounding_raw, str):
                        rounding_raw = rounding_raw.replace(',', '.')
                    
                    rounding_val = float(rounding_raw or 0)
                    if abs(rounding_val) > 0:
                        # Prioritetas metodui pavadinimu 'Up'
                        rounding = self.env['account.cash.rounding'].search([('name', '=', 'Up')], limit=1)
                        if not rounding:
                            rounding = self.env['account.cash.rounding'].search([
                                '|', ('name', 'ilike', 'apvalinimas'),
                                ('rounding', '=', 0.05)
                            ], limit=1)
                        
                        if rounding:
                            vals['cash_rounding_id'] = rounding.id
                except Exception as e:
                    _logger.warning("Nepavyko pritaikyti apvalinimo: %s", str(e))

            # 4. Automobilio paieška pagal numerį
            vehicle_id = False
            plate_for_msg = ""
            if data.get('vehicle_plate'):
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
