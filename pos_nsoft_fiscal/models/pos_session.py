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

    def set_opening_control(self, opening_notes, opening_cash):
        try:
            cash_float = float(opening_cash or 0.0)
        except (TypeError, ValueError):
            cash_float = 0.0
        res = super().set_opening_control(opening_notes, cash_float)
        try:
            if cash_float > 0:
                for session in self:
                    if session.config_id.nsoft_enabled:
                        self._send_nsoft_cash_operation('in', cash_float)
                        _logger.info("nSoft: cash-in %.2f (%s)", cash_float, session.name)
        except Exception as e:
            _logger.error("nSoft: Ryto atidarymo klaida: %s", e)
        return res

    def action_pos_session_closing_control(self, *args, **kwargs):
        self._send_nsoft_z_report()
        res = super().action_pos_session_closing_control(*args, **kwargs)
        return res

    def try_cash_in_out(self, *args, **kwargs):
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
            _logger.error("nSoft: cash_in_out klaida: %s", e)
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

    def _parse_nsoft_lines(self, data):
        lines = []
        try:
            content = data if isinstance(data, list) else (data.get('content') or [])
            if isinstance(content, dict):
                content = [content]
            for item in content:
                if isinstance(item, dict):
                    doc = item.get('document') or {}
                    for line in (doc.get('lines') or []):
                        txt = line.get('content', '')
                        if txt:
                            lines.append(txt)
        except Exception as e:
            _logger.warning("nSoft: Klaida apdorojant eilutes: %s", e)
        return lines

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
                lines = self._parse_nsoft_lines(data)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'title': 'X Ataskaita', 'message': 'X Ataskaita issiusta.', 'type': 'success'},
                    'receipt_lines': lines,
                }
            except Exception as e:
                _logger.error("nSoft X klaida: %s", e)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'title': 'Klaida', 'message': f'X klaida: {e}', 'type': 'danger'},
                }

    def print_nsoft_z_report(self):
        """Z Ataskaita - isskviečiama is hamburger meniu."""
        for session in self:
            if not session.config_id.nsoft_enabled:
                return False
            api_url, pos_id, token = self._get_nsoft_credentials(session)
            if not api_url or not token:
                continue
            url = f"{api_url.rstrip('/')}/cr/{pos_id}/fis-day"
            headers = self._get_nsoft_headers(token)
            payload = {"output": {"format": "native", "lineWidth": 80}}
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=15)
                if response.ok:
                    data = response.json()
                    lines = self._parse_nsoft_lines(data)
                    _logger.info("nSoft Z %s: OK, %d eilučių", session.name, len(lines))
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {'title': 'Z Ataskaita', 'message': 'Z Ataskaita issiusta i spausdintuva.', 'type': 'success'},
                        'receipt_lines': lines,
                    }
                else:
                    err = response.text[:200]
                    _logger.error("nSoft Z klaida %s: %s", session.name, err)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {'title': 'Z klaida', 'message': f'Klaida {response.status_code}: {err}', 'type': 'danger'},
                    }
            except Exception as e:
                _logger.error("nSoft Z-Ataskaitos klaida: %s", e)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'title': 'Z klaida', 'message': f'Klaida: {e}', 'type': 'danger'},
                }

    def _send_nsoft_z_report(self):
        """Automatinis Z siuntimas uždarymo metu."""
        for session in self:
            if not session.config_id.nsoft_enabled:
                continue
            api_url, pos_id, token = self._get_nsoft_credentials(session)
            if not api_url or not token:
                continue
            url = f"{api_url.rstrip('/')}/cr/{pos_id}/fis-day"
            headers = self._get_nsoft_headers(token)
            payload = {"output": {"format": "native", "lineWidth": 80}}
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=15)
                _logger.info("nSoft Z ataskaita %s -> %s", session.name, response.status_code)
            except Exception as e:
                _logger.error("nSoft Z-Ataskaitos klaida: %s", e)

    def _send_nsoft_cash_operation(self, direction, amount):
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
                _logger.info("nSoft cash %s %.2f -> %s", direction, amount, response.status_code)
            except Exception as e:
                _logger.error("nSoft Pinigu judejimo klaida: %s", e)
