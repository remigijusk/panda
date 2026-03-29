# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_nsoft_api_url = fields.Char(string='nSoft API Base URL', config_parameter='pos_nsoft_fiscal.api_url')
    pos_nsoft_pos_id = fields.Char(string='nSoft Kasos ID', config_parameter='pos_nsoft_fiscal.pos_id')
    pos_nsoft_api_token = fields.Char(string='nSoft API Token', config_parameter='pos_nsoft_fiscal.api_token')
