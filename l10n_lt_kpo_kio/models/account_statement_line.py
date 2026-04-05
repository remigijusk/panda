from odoo import models, fields, api

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    kpo_kio_type = fields.Selection([
        ('kpo', 'Pajamų (KPO)'),
        ('kio', 'Išlaidų (KIO)')
    ], compute='_compute_kpo_kio_type')

    lt_amount_words = fields.Char(compute='_compute_lt_amounts')
    lt_amount_eur = fields.Integer(compute='_compute_lt_amounts')
    lt_amount_ct = fields.Integer(compute='_compute_lt_amounts')
    
    cashier_name = fields.Char(compute='_compute_cashier_data')
    cashier_signature = fields.Binary(compute='_compute_cashier_data')

    @api.depends('amount')
    def _compute_kpo_kio_type(self):
        for line in self:
            line.kpo_kio_type = 'kpo' if line.amount > 0 else 'kio'

    def _compute_cashier_data(self):
        for line in self:
            line.cashier_name = self.env.user.name
            if 'sign_signature' in self.env.user._fields and self.env.user.sign_signature:
                line.cashier_signature = self.env.user.sign_signature
            else:
                line.cashier_signature = False

    @api.depends('amount')
    def _compute_lt_amounts(self):
        for line in self:
            abs_amount = abs(line.amount or 0.0)
            eur = int(abs_amount)
            ct = int(round((abs_amount - eur) * 100))
            line.lt_amount_eur = eur
            line.lt_amount_ct = ct
            line.lt_amount_words = self._get_lt_words(eur)

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
