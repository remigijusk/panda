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
            # Saugiai ištraukiame sumą ir tipą Odoo 19 versijoje
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
        # Bandom traukti iš Odoo nustatymų
        api_url = getattr(session.config_id, 'nsoft_api_url', False)
        pos_id = getattr(session.config_id, 'nsoft_pos_id', False)
        token = getattr(session.config_id, 'nsoft_token', False)
        
        # SUPER-HAKAS: Jei nustatymų neranda, imam iškart iš tavo el. laiško!
        if not api_url:
            api_url = "https://nvf.app3.nsoft.eu:30032"
        if not pos_id:
            pos_id = "CR-000019280"
        if not token:
            token = "v_M7tQTI27TDqNGGWAi4xuvnMCnRkKd4AXJMlETlOhF_Yb2_R7Tb8YnogLmfTJjnyc8dC_sNZFc1XDB-SNA="
            
        return api_url, pos_id, token

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
                _logger.info(f"nSoft Z-Ataskaita sėkminga sesijai {session.name}")
            except Exception as e:
                _logger.error(f"nSoft Z-Ataskaitos klaida: {e}")

    def _send_nsoft_cash_operation(self, direction, amount):
        for session in self:
            api_url, pos_id, token = self._get_nsoft_credentials(session)
            url = f"{api_url.rstrip('/')}/api/cr/{pos_id}/cash"
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "output": {
                    "format": "native",
                    "lineWidth": 80
                },
                "direction": direction,
                "amount": float(amount)
            }
            try:
                _logger.info(f"Siunčiamas pinigų judėjimas į nSoft: {url} | Suma: {amount}")
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                _logger.info(f"nSoft Pinigų judėjimas ({direction}: {amount}) sėkmingas sesijai {session.name}")
            except Exception as e:
                _logger.error(f"nSoft Pinigų judėjimo klaida: {e}")
