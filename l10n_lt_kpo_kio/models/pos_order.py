from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    has_kpo_payment = fields.Boolean(compute='_compute_has_kpo_payment', string='Turi KPO mokėjimą')
    
    # Laukai KPO PDF šablonui
    lt_amount_words = fields.Char(compute='_compute_lt_amounts')
    lt_amount_eur = fields.Integer(compute='_compute_lt_amounts')
    lt_amount_ct = fields.Integer(compute='_compute_lt_amounts')
    kpo_journal_account = fields.Char(compute='_compute_kpo_journal_account')
    cashier_name = fields.Char(compute='_compute_cashier_data')
    cashier_signature = fields.Binary(compute='_compute_cashier_data')

    @api.depends('payment_ids', 'payment_ids.payment_method_id')
    def _compute_has_kpo_payment(self):
        for order in self:
            has_kpo = False
            for payment in order.payment_ids:
                if payment.payment_method_id and 'KPO' in (payment.payment_method_id.name or '').upper():
                    has_kpo = True
                    break
            order.has_kpo_payment = has_kpo

    @api.depends('payment_ids', 'payment_ids.amount', 'amount_total')
    def _compute_lt_amounts(self):
        for order in self:
            # Suskaičiuojame sumą tų mokėjimų, kurie daryti per KPO
            kpo_amount = sum(p.amount for p in order.payment_ids if p.payment_method_id and 'KPO' in (p.payment_method_id.name or '').upper())
            
            # Jei netyčia KPO suma 0 (dėl sistemos specifikos), imame visą užsakymo sumą
            if kpo_amount <= 0:
                kpo_amount = order.amount_total
                
            eur = int(kpo_amount)
            ct = int(round((kpo_amount - eur) * 100))
            order.lt_amount_eur = eur
            order.lt_amount_ct = ct
            order.lt_amount_words = order._get_lt_words(eur)

    def _compute_kpo_journal_account(self):
        for order in self:
            account_code = ''
            try:
                for payment in order.payment_ids:
                    if payment.payment_method_id and 'KPO' in (payment.payment_method_id.name or '').upper():
                        journal = payment.payment_method_id.journal_id
                        if journal and journal.default_account_id:
                            account_code = journal.default_account_id.code
                        break
            except Exception:
                pass
            order.kpo_journal_account = account_code

    def _compute_cashier_data(self):
        for order in self:
            # Ieškome kasininko: pirmiausia POS darbuotojas, jei nėra - sistemos vartotojas
            cashier = order.employee_id.name if hasattr(order, 'employee_id') and order.employee_id else order.user_id.name
            order.cashier_name = cashier or self.env.user.name
            
            # Parašo paėmimas
            user = order.user_id or self.env.user
            if hasattr(user, 'sign_signature') and user.sign_signature:
                order.cashier_signature = user.sign_signature
            else:
                order.cashier_signature = False

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
