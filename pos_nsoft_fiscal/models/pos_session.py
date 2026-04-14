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
        """Atidarant sesija – siunciame cash-in i nSoft jei balance > 0."""
        try:
            cash_float = float(opening_cash or 0.0)
        except (TypeError, ValueError):
            cash_float = 0.0

        res = super().set_opening_control(opening_notes, cash_float)

        # Siunciame cash-in i nSoft po sekmingo atidarymo
        if cash_float > 0:
            for session in self:
                if not session.config_id.nsoft_enabled:
                    continue
                try:
                    self._send_nsoft_cash_operation('in', cash_float)
                    _logger.info("nSoft: Atidarymo cash-in %.2f EUR (%s)", cash_float, session.name)
                except Exception as e:
                    _logger.error("nSoft: Atidarymo cash-in klaida: %s", e)

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
