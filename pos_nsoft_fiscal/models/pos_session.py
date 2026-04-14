# -*- coding: utf-8 -*-
from odoo import models, api
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
        """Atidarant sesija - siunciame cash-in i nSoft jei balance > 0."""
        try:
            cash_float = float(opening_cash or 0.0)
        except (TypeError, ValueError):
            cash_float = 0.0

        res = super().set_opening_control(opening_notes, cash_float)

        if cash_float > 0:
            try:
                opened = self.env['pos.session'].sudo().search([
                    ('state', '=', 'opened'),
                    ('config_id.nsoft_enabled', '=', True),
                ], order='id desc', limit=5)
                for session in opened:
                    session._send_nsoft_cash_operation('in', cash_float)
                    _logger.info("nSoft: Atidarymo cash-in %.2f EUR (%s)", cash_float, session.name)
            except Exception as ex:
                _logger.error("nSoft: Atidarymo cash-in klaida: %s", ex)
