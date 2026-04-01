from odoo import models, fields, api
import math

class AccountMove(models.Model):
    _inherit = 'account.move'

    kpo_kio_type = fields.Selection([
        ('kpo', 'Pajamų (KPO)'),
        ('kio', 'Išlaidų (KIO)')
    ], compute='_compute_kpo_kio_type', string='Orderio tipas')

    lt_amount_words = fields.Char(compute='_compute_lt_amounts', string='Suma žodžiais')
    lt_amount_eur = fields.Integer(compute='_compute_lt_amounts')
    lt_amount_ct = fields.Integer(compute='_compute_lt_amounts')
    kpo_partner_name = fields.Char(compute='_compute_kpo_partner')

    @api.depends('line_ids', 'journal_id')
    def _compute_kpo_kio_type(self):
        for move in self:
            move.kpo_kio_type = False
            # Tikriname, ar žurnalas yra kasos tipo
            if move.journal_id.type == 'cash':
                # Randame kasos sąskaitos eilutę šiame įraše
                cash_lines = move.line_ids.filtered(lambda l: l.account_id == move.journal_id.default_account_id)
                if cash_lines:
                    balance = sum(cash_lines.mapped('balance'))
                    # Jei likutis teigiamas (Debetas) - tai KPO, jei neigiamas (Kreditas) - KIO
                    move.kpo_kio_type = 'kpo' if balance > 0 else 'kio'

    @api.depends('amount_total')
    def _compute_lt_amounts(self):
        for move in self:
            amount = move.amount_total or 0.0
            eur = int(amount)
            ct = int(round((amount - eur) * 100))
            
            move.lt_amount_eur = eur
            move.lt_amount_ct = ct
            move.lt_amount_words = self._get_lt_words(eur)

    @api.depends('partner_id', 'line_ids')
    def _compute_kpo_partner(self):
        for move in self:
            if move.partner_id:
                vat = f", Įm. kodas/PVM: {move.partner_id.vat}" if move.partner_id.vat else ""
                move.kpo_partner_name = f"{move.partner_id.name}{vat}"
            else:
                move.kpo_partner_name = ""

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
