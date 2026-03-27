# -*- coding: utf-8 -*-
from odoo import fields, models, api
import requests
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_nsoft_api_url = fields.Char(
        string='nSoft API Base URL', 
        config_parameter='pos_nsoft_fiscal.api_url', 
        default='https://nvf.app3.nsoft.eu:30032/api'
    )
    pos_nsoft_pos_id = fields.Char(
        string='nSoft Kasos ID', 
        config_parameter='pos_nsoft_fiscal.pos_id', 
        default='CR-000019280'
    )
    pos_nsoft_api_token = fields.Char(
        string='nSoft API Token', 
        config_parameter='pos_nsoft_fiscal.api_token'
    )

    def action_test_nsoft_connection(self):
        """Testuoja ryšį su nSoft API darant GET užklausą į /cr/{id}"""
        self.ensure_one()
        
        api_url = self.pos_nsoft_api_url or ''
        pos_id = self.pos_nsoft_pos_id or ''
        token = self.pos_nsoft_api_token or ''

        if not api_url or not pos_id or not token:
            raise UserError("Prašau užpildyti visus nSoft API nustatymų laukus prieš testuojant ryšį.")

        url = f"{api_url.rstrip('/')}/cr/{pos_id}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                raise UserError("Ryšys su nSoft API (i.EKA) sėkmingas! Sistema paruošta darbui.")
            else:
                raise UserError(f"Nepavyko prisijungti prie nSoft serverio.\nKlaidos kodas: {response.status_code}\nAtsakymas: {response.text}")
        except requests.exceptions.RequestException as e:
            raise UserError(f"Ryšio klaida. Patikrinkite interneto ryšį arba API adresą.\nDetalės: {str(e)}")
