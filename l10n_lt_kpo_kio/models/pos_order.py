from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    lt_amount_words = fields.Char(compute='_compute_lt_amounts')
    lt_amount_eur = fields.Integer(compute='_compute_lt_amounts')
    lt_amount_ct = fields.Integer(compute='_compute_lt_amounts')
    cashier_name = fields.Char(compute='_compute_cashier_data')
    cashier_signature = fields.Binary(compute='_compute_cashier_data')
    kpo_journal_account = fields.Char(compute='_compute_kpo_journal_account')

    def _compute_cashier_data(self):
        for order in self:
            order.cashier_name = self.env.user.name
            if 'sign_signature' in self.env.user._fields and self.env.user.sign_signature:
                order.cashier_signature = self.env.user.sign_signature
            else:
                order.cashier_signature = False

    @api.depends('payment_ids')
    def _compute_kpo_journal_account(self):
        for order in self:
            account_code = ""
            kpo_payment = order.payment_ids.filtered(lambda p: 'KPO' in (p.payment_method_id.name or '').upper())
            if kpo_payment and kpo_payment[0].payment_method_id.journal_id.default_account_id:
                account_code = kpo_payment[0].payment_method_id.journal_id.default_account_id.code
            elif order.payment_ids and order.payment_ids[0].payment_method_id.journal_id.default_account_id:
                account_code = order.payment_ids[0].payment_method_id.journal_id.default_account_id.code
            order.kpo_journal_account = account_code

    @api.depends('amount_total')
    def _compute_lt_amounts(self):
        for order in self:
            abs_amount = abs(order.amount_total or 0.0)
            eur = int(abs_amount)
            ct = int(round((abs_amount - eur) * 100))
            order.lt_amount_eur = eur
            order.lt_amount_ct = ct
            order.lt_amount_words = self._get_lt_words(eur)

    def _get_lt_words(self, num):
        if num == 0: return "nulis"
        vienetai = ["", "vienas", "du", "trys", "keturi", "penki", "šeši", "septyni", "aštuoni", "devyni"]
        niolikos = ["dešimt", "vienuolika", "dvylika", "trylika", "keturiolika", "penkiolika", "šešiolika", "septyniolika", "aštuoniolika", "devyniolika"]
        desimtys = ["", "dešimt", "dvidešimt", "trisdešimt", "keturiasdešimt", "penkiasdešimt", "šešiasdešimt", "septyniasdešimt", "aštuoniasdešimt", "devyniasdešimt"]
        
        def convert_hundreds(n):
            res = ""
            h = n // 100
            rem = n % 100
            if h > 0:
                res += vienetai[h] + " šimtai " if h > 1 else "šimtas "
            if rem >= 10 and rem < 20:
                res += niolikos[rem - 10] + " "
            else:
                d = rem // 10
                v = rem % 10
                if d > 0: res += desimtys[d] + " "
                if v > 0: res += vienetai[v] + " "
            return res.strip()

        words = ""
        mil = num // 1000000
        rem_mil = num % 1000000
        tho = rem_mil // 1000
        rem = rem_mil % 1000

        if mil > 0:
            words += convert_hundreds(mil) + (" milijonai " if mil > 1 else " milijonas ")
        if tho > 0:
            words += convert_hundreds(tho) + (" tūkstančiai " if tho % 10 > 1 and (tho % 100 < 10 or tho % 100 > 20) else " tūkstantis " if tho % 10 == 1 and tho % 100 != 11 else " tūkstančių ")
        if rem > 0:
            words += convert_hundreds(rem)
        return words.strip().capitalize()
