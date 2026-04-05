# -*- coding: utf-8 -*-
from odoo import fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    nsoft_enabled = fields.Boolean(string="Naudoti nSoft fiskalizaciją", default=False)
    nsoft_api_url = fields.Char(string="nSoft API URL", help="Pvz.: https://nvf.app3.nsoft.eu:30032")
    nsoft_pos_id = fields.Char(string="nSoft POS ID", help="Pvz.: CR-000019280")
    nsoft_token = fields.Char(string="nSoft Token")
