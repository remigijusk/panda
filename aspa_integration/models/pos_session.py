from odoo import api, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        res = super()._loader_params_product_product()
        res['search_params']['fields'].append('is_deposit')
        return res
