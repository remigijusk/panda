# -*- coding: utf-8 -*-
from odoo import models
import requests
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_order(self):
        result = super()._loader_params_pos_order()
        result['search_params']['fields'].append('nsoft_receipt_id')
        result['search_params']['fields'].append('nsoft_error')
        return result

    def action_pos_session_closing_control(self, *args, **kwargs):
        res = super().action_pos_session_closing_control(*args, **kwargs)
        self._send_nsoft_z_report()
        return res

    def set_cashbox_pos(self, cashbox_value, notes):
        """Called when opening session with initial cash."""
        res = super().set_cashbox_pos(cashbox_value, notes)
        # Morning opening: send cash-in to nSoft (initial drawer amount)
        if cashbox_value and cashbox_value > 0:
            self._send_nsoft_cash_operation('in', cashbox_value)
        return res

    def try_cash_in_out(self, *args, **kwargs):
        """Called for cash in/out operations during session."""
        res = super().try_cash_in_out(*args, **kwargs)
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
            _logger.error("nSoft: Klaida traukiant cash_in_out duomenis: %s", e)
        return res

    def _get_nsoft_credentials(self, session):
        return (
            session.config_id.nsoft_api_url,
            session.config_id.nsoft_pos_id,
            session.config_id.nsoft_token,
        )

    def _get_nsoft_headers(self, token):
        return {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def print_nsoft_x_report(self):
        for session in self:
            if not session.config_id.nsoft_enabled:
                return False
            api_url, pos_id, token = self._get_nsoft_credentials(session)
            if not api_url or not token:
                continue
            url = f"{api_url.rstrip('/')}/cr/{pos_id}/cur-day"
            headers = self._get_nsoft_headers(token)
            payload = {"output": {"format": "native", "lineWidth": 80}}
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                lines = []
                for item in (data.get('content') or []):
                    doc = item.get('document') or {}
                    for line in (doc.get('lines') or []):
                        txt = line.get('content', '')
                        if txt:
                            lines.append(txt)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'X Ataskaita',
                        'message': 'X Ataskaita išsiųsta į spausdintuvą.',
                        'type': 'success',
                    },
                    'receipt_lines': lines,
                }
            except Exception as e:
                _logger.error("nSoft X-Ataskaitos klaida: %s", e)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Klaida',
                        'message': f'X Ataskaitos klaida: {e}',
                        'type': 'danger',
                    },
                }

    def _send_nsoft_z_report(self):
        """Send Z report when closing session. Includes cash drawer balance."""
        for session in self:
            if not session.config_id.nsoft_enabled:
                continue
            api_url, pos_id, token = self._get_nsoft_credentials(session)
            if not api_url or not token:
                continue
            url = f"{api_url.rstrip('/')}/cr/{pos_id}/fis-day"
            headers = self._get_nsoft_headers(token)
            # Calculate cash in drawer at session close
            cash_in_drawer = session.cash_register_balance_end_real or 0.0
            payload = {
                "output": {"format": "native", "lineWidth": 80},
                "cashDrawer": round(float(cash_in_drawer), 2),
            }
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=15)
                _logger.info("nSoft Z ataskaita: %s -> %s", session.name, response.status_code)
            except Exception as e:
                _logger.error("nSoft Z-Ataskaitos klaida: %s", e)

    def _send_nsoft_cash_operation(self, direction, amount):
        """Send cash in/out operation to nSoft."""
        for session in self:
            if not session.config_id.nsoft_enabled:
                continue
            api_url, pos_id, token = self._get_nsoft_credentials(session)
            if not api_url or not token:
                continue
            url = f"{api_url.rstrip('/')}/cr/{pos_id}/cash"
            headers = self._get_nsoft_headers(token)
            payload = {
                "output": {"format": "native", "lineWidth": 80},
                "direction": direction,
                "amount": round(float(amount), 2),
            }
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                _logger.info("nSoft cash %s %.2f: %s", direction, amount, response.status_code)
            except Exception as e:
                _logger.error("nSoft Pinigu judejimo klaida: %s", e)
