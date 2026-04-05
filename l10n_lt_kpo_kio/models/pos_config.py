from odoo import models, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'
    
    # Sukuriame laukelį duomenų bazėje
    iface_print_kpo = fields.Boolean(string='Rodyti KPO mygtuką', default=False)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Susiejame laukelį su nustatymų langu
    pos_iface_print_kpo = fields.Boolean(
        related='pos_config_id.iface_print_kpo', 
        readonly=False
    )

class PosSession(models.Model):
    _inherit = 'pos.session'

    # Užtikriname, kad POS ekranas užsikraudamas gautų šį nustatymą
    def _loader_params_pos_config(self):
        result = super()._loader_params_pos_config()
        if 'iface_print_kpo' not in result['search_params']['fields']:
            result['search_params']['fields'].append('iface_print_kpo')
        return result
