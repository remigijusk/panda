from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_iface_print_kpo = fields.Boolean(
        related='pos_config_id.iface_print_kpo', 
        readonly=False,
        string="Spausdinti KPO (A4)", 
        help="Leidžia spausdinti KPO iš POS užsakymo lango."
    )
