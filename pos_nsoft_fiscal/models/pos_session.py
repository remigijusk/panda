# -*- coding: utf-8 -*-
from odoo import models
import requests
import logging

_logger = logging.getLogger(__name__)

class PosSession(models.Model):
    _inherit = 'pos.session'

    def action_pos_session_closing_control(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        res = super(PosSession, self).action_pos_session_closing_control(balancing_account, amount_to_balance, bank_payment_method_diffs)
        self._send_nsoft_z_report()
        return res

    def set_cashbox_pos(self, cashbox_value, notes):
        res = super(PosSession, self).set_cashbox_pos(cashbox_value, notes)
        if cashbox_value > 0:
            self._send_nsoft_cash_operation('in', cashbox_value)
        return res

    def try_cash_in_out(self, _type, amount, reason, extras, *args, **kwargs):
        res = super(PosSession, self).try_cash_in_out(_type, amount, reason, extras, *args, **kwargs)
        if amount > 0:
            self._send_nsoft_cash_operation(_type, amount)
        return res

    def _get_nsoft_credentials(self):
        # Traukiame URL, POS ID ir Svarbiausia - TOKEN!
        api_url = self.env['ir.config_parameter'].sudo().get_param('nsoft_api_url')
        pos_id = self.env['ir.config_parameter'].sudo().get_param('nsoft_pos_id')
        token = self.env['ir.config_parameter'].sudo().get_param('nsoft_token')
        
        if not api_url:
            api_url = self.env['ir.config_parameter'].sudo().get_param('pos_nsoft_fiscal.nsoft_api_url')
            pos_id = self.env['ir.config_parameter'].sudo().get_param('pos_nsoft_fiscal.nsoft_pos_id')
            token = self.env['ir.config_parameter'].sudo().get_param('pos_nsoft_fiscal.nsoft_token')
            
        return api_url, pos_id, token

    def _send_nsoft_z_report(self):
        for session in self:
            api_url, pos_id, token = self._get_nsoft_credentials()
            if not api_url or not pos_id or not token:
                continue
            
            url = f"{api_url.rstrip('/')}/api/cr/{pos_id}/fis-day"
            headers = {"Authorization": f"Bearer {token}"} # Pridėtas raktas!
            payload = {
                "output": {
                    "format": "native",
                    "lineWidth": 80
                }
            }
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                _logger.info(f"nSoft Z-Ataskaita sėkminga sesijai {session.name}")
            except Exception as e:
                _logger.error(f"nSoft Z-Ataskaitos klaida: {e}")

    def _send_nsoft_cash_operation(self, direction, amount):
        for session in self:
            api_url, pos_id, token = self._get_nsoft_credentials()
            if not api_url or not pos_id or not token:
                continue
            
            url = f"{api_url.rstrip('/')}/api/cr/{pos_id}/cash"
            headers = {"Authorization": f"Bearer {token}"} # Pridėtas raktas!
            payload = {
                "output": {
                    "format": "native",
                    "lineWidth": 80
                },
                "direction": direction,
                "amount": float(amount)
            }
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                _logger.info(f"nSoft Pinigų judėjimas ({direction}: {amount}) sėkmingas sesijai {session.name}")
            except Exception as e:
                _logger.error(f"nSoft Pinigų judėjimo klaida: {e}")
