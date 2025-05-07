# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    print_format = fields.Selection(
        selection_add=[('custom_dymo', 'Custom Label')],
        ondelete={'custom_dymo': 'set default'}
    )

    def process(self):
        self.ensure_one()
        print('\n🔥 Entered process() for ProductLabelLayout')

        if self.print_format == 'custom_dymo':
            xml_id = 'product_label_custom_dymo.report_product_label_custom_dymo_action'

            if self.product_ids:
                products = self.product_ids
            elif self.product_tmpl_ids:
                products = self.product_tmpl_ids.mapped('product_variant_ids')
            else:
                raise UserError(_("No product selected for printing."))

            pricelist = self.pricelist_id

            for product in products:
                quantity = 1.0

                if pricelist:
                    price = pricelist.with_context(uom=product.uom_id.id)._get_product_price(product, quantity, False)
                else:
                    price = product.list_price

                tax = product.taxes_id[:1]
                price_with_tax = price
                if tax and pricelist:
                    price_with_tax = tax.compute_all(price, currency=pricelist.currency_id, quantity=quantity)[
                        'total_included']
                elif tax:
                    price_with_tax = tax.compute_all(price, currency=product.currency_id, quantity=quantity)[
                        'total_included']

                currency_symbol = pricelist.currency_id.symbol if pricelist and pricelist.currency_id else '€'
                base_unit_name = product.uom_id.name or ''
                country_name = product.country_of_origin.name if product.country_of_origin else ''

                product.final_price_with_tax = price_with_tax
                product.final_currency_symbol = currency_symbol
                product.final_base_unit_name = base_unit_name
                product.final_country_name = country_name

            result = self.env.ref(xml_id).report_action(products.ids, config=False)
            result.update({'close_on_report_download': True})
            return result

        return super().process()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    final_price_with_tax = fields.Float('Final Price with Tax')
    final_currency_symbol = fields.Char('Currency Symbol')
    final_base_unit_name = fields.Char('Base Unit Name')
    final_country_name = fields.Char('Country of Origin')
