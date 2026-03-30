# -*- coding: utf-8 -*-
from odoo import models
import requests
import logging

_logger = logging.getLogger(__name__)

class PosSession(models.Model):
    _inherit = 'pos.session'

    def action_pos_session_closing_control(self, *args, **kwargs):
        res = super(PosSession, self).action_pos_session_closing_control(*args, **kwargs)
        self._send_nsoft_z_report()
        return res

    def set_cashbox_pos(self, cashbox_value, notes):
        res = super(PosSession, self).set_cashbox_pos(cashbox_value, notes)
        if cashbox_value > 0:
            self._send_nsoft_cash_operation('in', cashbox_value)
        return res

    def try_cash_in_out(self, *args, **kwargs):
        res = super(PosSession, self).try_cash_in_out(*args, **kwargs)
        try:
            _type = kwargs.get('_type') or kwargs.get('type')
            if not _type and len(args) >= 1:
                _type = args[0]
                
            amount = kwargs.get('amount')
            if amount is None and len(args) >= 2:
                amount = args[1]
                
            amount = float(amount or 0.0)
            if amount != 0:
                direction = 'out' if _type == 'out' or amount < 0 else 'in'
                self._send_nsoft_cash_operation(direction, abs(amount))
        except Exception as e:
            _logger.error(f"nSoft: Klaida traukiant cash_in_out duomenis: {e}")
        return res

    def _get_nsoft_credentials(self, session):
        api_url = getattr(session.config_id, 'nsoft_api_url', False)
        pos_id = getattr(session.config_id, 'nsoft_pos_id', False)
        token = getattr(session.config_id, 'nsoft_token', False)
        
        if not api_url:
            api_url = "https://nvf.app3.nsoft.eu:30032"
        if not pos_id:
            pos_id = "CR-000019280"
        if not token:
            token = "v_M7tQTI27TDqNGGWAi4xuvnMCnRkKd4AXJMlETlOhF_Yb2_R7Tb8YnogLmfTJjnyc8dC_sNZFc1XDB-SNA="
            
        return api_url, pos_id, token

    def print_nsoft_x_report(self):
        """Šią funkciją iškvies X ataskaitos mygtukas iš POS ekrano"""
        for session in self:
            api_url, pos_id, token = self._get_nsoft_credentials(session)
            url = f"{api_url.rstrip('/')}/api/cr/{pos_id}/cur-day"
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "output": {
                    "format": "native",
                    "lineWidth": 80
                }
            }
            try:
                _logger.info(f"Siunčiama X-Ataskaita į nSoft: {url}")
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                return True
            except Exception as e:
                _logger.error(f"nSoft X-Ataskaitos klaida: {e}")
                return False

    def _send_nsoft_z_report(self):
        for session in self:
            api_url, pos_id, token = self._get_nsoft_credentials(session)
            url = f"{api_url.rstrip('/')}/api/cr/{pos_id}/fis-day"
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "output": {
                    "format": "native",
                    "lineWidth": 80
                }
            }
            try:
                _logger.info(f"Siunčiama Z-Ataskaita į nSoft: {url}")
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
            except Exception as e:
                _logger.error(f"nSoft Z-Ataskaitos klaida: {e}")

    def _send_nsoft_cash_operation(self, direction, amount):
        for session in self:
            api_url, pos_id, token = self._get_nsoft_credentials(session)
            url = f"{api_url.rstrip('/')}/api/cr/{pos_id}/non-fis-doc"
            headers = {"Authorization": f"Bearer {token}"}
            
            op_name = "Pinigų įnešimas (Cash In)"
            if direction == 'out' or amount < 0:
                op_name = "Pinigų išėmimas (Cash Out)"
                
            text_line = f"{op_name}: {abs(amount):.2f} EUR"
            
            payload = {
                "output": {
                    "format": "native",
                    "lineWidth": 80
                },
                "name": op_name,
                "lines": [
                    {
                        "type": "text",
                        "content": text_line,
                        "format": "normal",
                        "align": "left"
                    }
                ]
            }
            try:
                _logger.info(f"Siunčiamas pinigų judėjimas į nSoft ({url}) | {text_line}")
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
            except Exception as e:
                _logger.error(f"nSoft Pinigų judėjimo klaida: {e}")
