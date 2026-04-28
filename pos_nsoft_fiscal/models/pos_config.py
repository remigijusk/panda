# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # --- Connection ----------------------------------------------------
    nsoft_enabled = fields.Boolean(string="Naudoti nSoft fiskalizacija", default=False)
    nsoft_api_url = fields.Char(string="nSoft API URL",
                                help="Pvz.: https://nvf.app3.nsoft.eu:30032")
    nsoft_pos_id = fields.Char(string="nSoft POS ID",
                               help="Pvz.: CR-000019280 (Cash Register Number)")
    nsoft_token = fields.Char(string="nSoft Token (Bearer)")

    # --- Cash register administrative settings -------------------------
    nsoft_mod = fields.Selection(
        [('BP', 'BP - Bendros paskirties'), ('RV', 'RV - Restoranai / Viesbuciai')],
        string="nSoft rezimas", default='BP',
        help="BP - bendros paskirties kasa. RV - restoranu/viesbuciu rezimas "
             "(igalina pre-order ir transfer endpointus).")
    nsoft_cashier = fields.Char(string="Kasininko vardas",
                                help="Rasomas ant kvitu (PATCH /cr/{id})")
    nsoft_round_cash = fields.Boolean(
        string="Apvalinti grynuju operacijas (5 ct)",
        default=True,
        help="Informuoja nSoft, kad grynieji apvalinami iki 5 ct. "
             "Faktini apvalinima atlieka Odoo (Settings -> Accounting -> "
             "Cash Rounding 0.05).")
    nsoft_retain_cash = fields.Boolean(string="Islaikyti grynuosius po Z",
                                       default=True)

    # --- Default output format -----------------------------------------
    nsoft_output_format = fields.Selection(
        [('native', 'native'), ('plain', 'plain'), ('image', 'image')],
        string="Dokumentu formatas", default='native')
    nsoft_line_width = fields.Integer(string="Eilutes plotis (40-80)", default=42)

    # --- Payment method names (must match API enum) --------------------
    nsoft_payment_cash = fields.Char(
        string="nSoft: Grynuju metodas", default='cash')
    nsoft_payment_card = fields.Char(
        string="nSoft: Banko korteles metodas", default='paymentCard')
    nsoft_payment_other_card = fields.Char(
        string="nSoft: Kitos korteles metodas", default='otherCard')
    nsoft_payment_voucher = fields.Char(
        string="nSoft: Kupono metodas", default='coupon')
    nsoft_payment_transfer = fields.Char(
        string="nSoft: Banko pavedimo metodas", default='transfer')
    nsoft_payment_other = fields.Char(
        string="nSoft: Kitas metodas", default='other')

    # --- VAT groups (match i.EKA VAT table) ----------------------------
    nsoft_vat_group_21 = fields.Char(string="PVM grupe 21%", default='A')
    nsoft_vat_group_9 = fields.Char(string="PVM grupe 9%", default='E')
    nsoft_vat_group_5 = fields.Char(string="PVM grupe 5%", default='C')
    nsoft_vat_group_0 = fields.Char(string="PVM grupe 0% (neapmokestinama)", default='F')
    nsoft_vat_group_alcohol = fields.Char(string="Alkoholio grupe", default='B')
    nsoft_vat_group_deposit = fields.Char(string="Taros / depozito grupe", default='T')
    nsoft_vat_group_other = fields.Char(string="Ne-PVM grupe", default='N')
