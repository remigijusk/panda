from odoo import models, fields, api

class PosConfig(models.Model):
    _inherit = 'pos.config'
    iface_print_kpo = fields.Boolean(string="Spausdinti KPO (A4)")

class PosOrder(models.Model):
    _inherit = 'pos.order'

    # Pajungiame nustatymą prie mygtuko
    has_kpo_payment = fields.Boolean(compute='_compute_has_kpo_payment', string='Rodyti KPO mygtuką')
    
    # Laukai PDF šablonui
    lt_amount_words = fields.Char(compute='_compute_lt_amounts')
    lt_amount_eur = fields.Integer(compute='_compute_lt_amounts')
    lt_amount_ct = fields.Integer(compute='_compute_lt_amounts')
    kpo_base_text = fields.Char(compute='_compute_kpo_base_text')
    kpo_journal_account = fields.Char(compute='_compute_kpo_journal_account')
    cashier_name = fields.Char(compute='_compute_cashier_data')
    cashier_signature = fields.Binary(compute='_compute_cashier_data')

    @api.depends('payment_ids', 'payment_ids.payment_method_id', 'session_id.config_id.iface_print_kpo')
    def _compute_has_kpo_payment(self):
        for order in self:
            # 1. Patikriname, ar nustatymas įjungtas POS konfigūracijoje
            setting_on = order.session_id.config_id.iface_print_kpo if order.session_id and order.session_id.config_id else False
            
            has_kpo = False
            # 2. Jei įjungtas, tikriname mokėjimų būdus
            if setting_on:
                for payment in order.payment_ids:
                    if payment.payment_method_id and 'KPO' in (payment.payment_method_id.name or '').upper():
                        has_kpo = True
                        break
            order.has_kpo_payment = has_kpo

    @api.depends('payment_ids', 'payment_ids.amount', 'amount_total')
    def _compute_lt_amounts(self):
        for order in self:
            # Paimame KPO mokėjimų sumą
            kpo_amount = sum(p.amount for p in order.payment_ids if p.payment_method_id and 'KPO' in (p.payment_method_id.name or '').upper())
            # Jei dėl kažkokių priežasčių 0 (pvz., tik nustatymai, nėra mokėjimų), imame visą sumą
            if kpo_amount <= 0:
                kpo_amount = order.amount_total
                
            abs_amount = abs(kpo_amount)
            eur = int(abs_amount)
            ct = int(round((abs_amount - eur) * 100))
            order.lt_amount_eur = eur
            order.lt_amount_ct = ct
            order.lt_amount_words = order._get_lt_words(eur)

    def _compute_kpo_base_text(self):
        for order in self:
            base_text = f"{order.pos_reference} POS Užsakymas"
            if order.partner_id:
                base_text += f", Klientas: {order.partner_id.name}"
            order.kpo_base_text = base_text

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
            order.kpo_journal_account = account_code or '______'

    def _compute_cashier_data(self):
        for order in self:
            # Ieškome kasininko vardo: arba darbuotojas, arba user'io vardas
            cashier = order.employee_id.name if order.employee_id else (order.user_id.name if order.user_id else self.env.user.name)
            order.cashier_name = cashier or '______'
            
            # Parašo paėmimas iš Odoo profilio (vartotojo)
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
