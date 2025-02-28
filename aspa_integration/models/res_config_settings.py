from odoo import api, models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    aspa_api_url = fields.Char(
        string="ASPA API URL",
        default="http://127.0.0.1:8111/json/fp550/Cmdline",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    aspa_api_url = fields.Char(
        related='company_id.aspa_api_url',
        string="ASPA API URL",
        readonly=False
    )
