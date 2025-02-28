from odoo import api, models, fields


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def update_pos_reference(self, order_id, aspa_receipt_number):
        order = self.browse(order_id)
        if order:
            order.write({
                'pos_reference': order.pos_reference + ' - ' + aspa_receipt_number,
            })
