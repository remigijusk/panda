# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError
import requests


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_nsoft_enabled = fields.Boolean(related='pos_config_id.nsoft_enabled', readonly=False)
    pos_nsoft_api_url = fields.Char(related='pos_config_id.nsoft_api_url', readonly=False)
    pos_nsoft_pos_id = fields.Char(related='pos_config_id.nsoft_pos_id', readonly=False)
    pos_nsoft_token = fields.Char(related='pos_config_id.nsoft_token', readonly=False)

    def action_test_nsoft_connection(self):
        self.ensure_one()
        if not self.pos_nsoft_enabled:
            raise UserError("Pirmiausia ijunkite nSoft fiskalizacija.")

        if not self.pos_nsoft_api_url or not self.pos_nsoft_pos_id or not self.pos_nsoft_token:
            raise UserError("Uzpildykite visus laukus (API URL, POS ID, Token)!")

        url = f"{self.pos_nsoft_api_url.rstrip('/')}/cr/{self.pos_nsoft_pos_id}/cur-day"
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.pos_nsoft_token}",
            "Content-Type": "application/json",
        }
        payload = {"output": {"format": "native", "lineWidth": 80}}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Rysys veikia!',
                        'message': 'Prisijungimas sekminas.',
                        'type': 'success',
                    },
                }
            else:
                error_text = response.text if response.text else "Nera atsakymo"
                raise UserError(f"Klaida! Kodas: {response.status_code}. {error_text}")
        except UserError:
            raise
        except Exception as e:
            raise UserError(f"Nepavyko pasiekti nSoft. Klaida: {e}")
