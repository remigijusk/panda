# -*- coding: utf-8 -*-
from odoo import models
import requests
import logging

_logger = logging.getLogger(__name__)

class PosSession(models.Model):
    _inherit = 'pos.session'

    def action_pos_session_closing_control(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        # 1. Pirmiausia atliekame standartinį Odoo pamainos uždarymą
        res = super(PosSession, self).action_pos_session_closing_control(balancing_account, amount_to_balance, bank_payment_method_diffs)
        
        # 2. Užbaigus Odoo uždarymą, išsiunčiame Z ataskaitos komandą į nSoft
        self._send_nsoft_z_report()
        return res

    def set_cashbox_pos(self, cashbox_value, notes):
        # 1. Standartinis Odoo rytinio pinigų likučio patvirtinimas
        res = super(PosSession, self).set_cashbox_pos(cashbox_value, notes)
        
        # 2. Siunčiame sumą į nSoft (Pinigų įnešimas)
        if cashbox_value > 0:
            self._send_nsoft_cash_operation('in', cashbox_value)
        return res

    def try_cash_in_out(self, _type, amount, reason, extras, *args, **kwargs):
        # Veikia, jei kasininkas vidury dienos daro įnešimą/išėmimą per kasos langą
        # Pataisyta, kad priimtų visus papildomus Odoo 19 kintamuosius (*args, **kwargs)
        res = super(PosSession, self).try_cash_in_out(_type, amount, reason, extras, *args, **kwargs)
        if amount > 0:
            self._send_nsoft_cash_operation(_type, amount)
        return res

    def _get_nsoft_credentials(self):
        # Ištraukiame nSoft nustatymus iš Odoo konfigūracijos
        api_url = self.env['ir.config_parameter'].sudo().get_param('nsoft_api_url')
        pos_id = self.env['ir.config_parameter'].sudo().get_param('nsoft_pos_id')
        # Jei naudoji prefixą savo modulyje:
        if not api_url:
            api_url = self.env['ir.config_parameter'].sudo().get_param('pos_nsoft_fiscal.nsoft_api_url')
            pos_id = self.env['ir.config_parameter'].sudo().get_param('pos_nsoft_fiscal.nsoft_pos_id')
        return api_url, pos_id

    def _send_nsoft_z_report(self):
        for session in self:
            api_url, pos_id = self._get_nsoft_credentials()
            if not api_url or not pos_id:
                continue
            
            url = f"{api_url.rstrip('/')}/api/cr/{pos_id}/fis-day"
            payload = {
                "output": {
                    "format": "native",
                    "lineWidth": 80
                }
            }
            try:
                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()
                _logger.info(f"nSoft Z-Ataskaita sėkminga sesijai {session.name}")
            except Exception as e:
                _logger.error(f"nSoft Z-Ataskaitos klaida: {e}")

    def _send_nsoft_cash_operation(self, direction, amount):
        for session in self:
            api_url, pos_id = self._get_nsoft_credentials()
            if not api_url or not pos_id:
                continue
            
            url = f"{api_url.rstrip('/')}/api/cr/{pos_id}/cash"
            payload = {
                "output": {
                    "format": "native",
                    "lineWidth": 80
                },
                "direction": direction, # Bus 'in' arba 'out'
                "amount": float(amount)
            }
            try:
                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()
                _logger.info(f"nSoft Pinigų judėjimas ({direction}: {amount}) sėkmingas sesijai {session.name}")
            except Exception as e:
                _logger.error(f"nSoft Pinigų judėjimo klaida: {e}")
