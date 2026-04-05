from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    has_kpo_payment = fields.Boolean(compute='_compute_has_kpo_payment', string='Turi KPO mokėjimą')

    @api.depends('payment_ids', 'payment_ids.payment_method_id')
    def _compute_has_kpo_payment(self):
        for order in self:
            has_kpo = False
            for payment in order.payment_ids:
                if payment.payment_method_id and 'KPO' in (payment.payment_method_id.name or '').upper():
                    has_kpo = True
                    break
            order.has_kpo_payment = has_kpo
