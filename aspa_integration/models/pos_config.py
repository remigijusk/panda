from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    aspa_api_url = fields.Char(
        string="ASPA API URL",
        default="http://217.117.27.34:8111",
    )
