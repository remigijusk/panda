# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    nsoft_enabled = fields.Boolean(string="Naudoti nSoft fiskalizaciją", default=False)
    nsoft_api_url = fields.Char(string="nSoft API URL", help="Pvz.: https://nvf.app3.nsoft.eu:30032")
    nsoft_pos_id = fields.Char(string="nSoft POS ID", help="Pvz.: CR-000019280")
    nsoft_token = fields.Char(string="nSoft Token")

    # PVM grupių pavadinimai (priklauso nuo kasėjo konfigūracijos nSoft portale)
    nsoft_vat_group_21 = fields.Char(
        string="PVM grupė 21%", default='A',
        help="nSoft PVM grupės pavadinimas 21% tarifui (dažniausiai 'A')"
    )
    nsoft_vat_group_9 = fields.Char(
        string="PVM grupė 9%", default='E',
        help="nSoft PVM grupės pavadinimas 9% tarifui (dažniausiai 'E')"
    )
    nsoft_vat_group_0 = fields.Char(
        string="PVM grupė 0%", default='F',
        help="nSoft PVM grupės pavadinimas 0% tarifui (dažniausiai 'F')"
    )

    # Mokėjimo metodų pavadinimai (priklauso nuo kasėjo konfigūracijos nSoft portale)
    nsoft_payment_cash = fields.Char(
        string="nSoft: Grynųjų metodas", default='cash',
        help="nSoft mokėjimo metodo pavadinimas grynųjų mokėjimams (pvz.: cash arba cashFis)"
    )
    nsoft_payment_card = fields.Char(
        string="nSoft: Kortelės metodas", default='card',
        help="nSoft mokėjimo metodo pavadinimas kortelių mokėjimams (pvz.: card arba cardFis)"
    )
    nsoft_payment_voucher = fields.Char(
        string="nSoft: Voucher metodas", default='voucher',
        help="nSoft mokėjimo metodo pavadinimas kuponų mokėjimams (pvz.: voucher arba voucherFis)"
    )
