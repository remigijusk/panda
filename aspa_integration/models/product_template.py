from odoo import api, models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_deposit = fields.Boolean(
        string="Package Deposit",
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_deposit = fields.Boolean(
        related='product_tmpl_id.is_deposit',
        string="Package Deposit",
        readonly=True,
    )

