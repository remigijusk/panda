from odoo import models, fields, api

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    lt_amount_words = fields.Char(compute='_compute_lt_amounts')
    lt_amount_eur = fields.Integer(compute='_compute_lt_amounts')
    lt_amount_ct = fields.Integer(compute='_compute_lt_amounts')
    cashier_name = fields.Char(compute='_compute_cashier_data')
    cashier_signature = fields.Binary(compute='_compute_cashier_data')
    kpo_kio_base_text = fields.Char(compute='_compute_base_text')
    kpo_kio_journal_account = fields.Char(compute='_compute_journal_account')

    @api.depends('amount')
    def _compute_lt_amounts(self):
        for rec in self:
            abs_amount = abs(rec.amount)
            eur = int(abs_amount)
            ct = int(round((abs_amount - eur) * 100))
            rec.lt_amount_eur = eur
            rec.lt_amount_ct = ct
            rec.lt_amount_words = rec._get_lt_words(eur)

    def _compute_cashier_data(self):
        for rec in self:
            rec.cashier_name = rec.create_uid.name or self.env.user.name or '______'
            user = rec.create_uid or self.env.user
            if hasattr(user, 'sign_signature') and user.sign_signature:
                rec.cashier_signature = user.sign_signature
            else:
                rec.cashier_signature = False

    @api.depends('payment_ref')
    def _compute_base_text(self):
        for rec in self:
            rec.kpo_kio_base_text = rec.payment_ref or 'Kasos operacija'

    @api.depends('journal_id')
    def _compute_journal_account(self):
        for rec in self:
            rec.kpo_kio_journal_account = rec.journal_id.default_account_id.code if rec.journal_id and rec.journal_id.default_account_id else '______'

    @api.model
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
            if 10 <= rem < 20:
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
