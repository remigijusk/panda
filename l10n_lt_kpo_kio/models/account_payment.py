from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    lt_amount_in_words = fields.Char(
        compute='_compute_lt_amount_in_words', 
        string='Suma žodžiu'
    )

    @api.depends('amount', 'currency_id')
    def _compute_lt_amount_in_words(self):
        for payment in self:
            if payment.currency_id:
                # Odoo standartizuotas vertimas į žodžius. 
                # Kad veiktų taisyklingai lietuviškai, įsitikinkite, kad Odoo kalbos nustatymuose įdiegta LT kalba.
                payment.lt_amount_in_words = payment.currency_id.amount_to_text(payment.amount)
            else:
                payment.lt_amount_in_words = ""
