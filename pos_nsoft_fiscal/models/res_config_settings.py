# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Ryšys su konkrečia kasa (pos.config)
    pos_nsoft_enabled = fields.Boolean(related='pos_config_id.nsoft_enabled', readonly=False)
    pos_nsoft_api_url = fields.Char(related='pos_config_id.nsoft_api_url', readonly=False)
    pos_nsoft_pos_id = fields.Char(related='pos_config_id.nsoft_pos_id', readonly=False)
    pos_nsoft_token = fields.Char(related='pos_config_id.nsoft_token', readonly=False)
