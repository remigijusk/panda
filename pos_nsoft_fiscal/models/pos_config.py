# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # --- Connection ----------------------------------------------------
    nsoft_enabled = fields.Boolean(string="Naudoti nSoft fiskalizaciją", default=False)
    nsoft_api_url = fields.Char(string="nSoft API URL",
                                help="Pvz.: https://nvf.app3.nsoft.eu:30032")
    nsoft_pos_id = fields.Char(string="nSoft POS ID",
                               help="Pvz.: CR-000019280 (Cash Register Number)")
    nsoft_token = fields.Char(string="nSoft Token (Bearer)")

    # --- Print Agent (lokalus tiltas tarp Odoo Cloud ir spausdintuvo) ---
    nsoft_print_agent_url = fields.Char(
        string="nSoft Print Agent URL",
        default='https://localhost:8443/print',
        help="Lokalaus print agent'o URL. Agentas paima nVF kvito tekstą iš "
             "naršyklės ir persiunčia į spausdintuvą per port 9100. "
             "Reikalingas, kai Odoo veikia debesyje (HTTPS), o spausdintuvas "
             "yra LAN'e. Palik tuščią — tada bus naudojamas Odoo standartinis "
             "ePos integracija.")
    nsoft_printer_host = fields.Char(
        string="Spausdintuvo IP",
        help="Lokalaus spausdintuvo IP adresas (pvz. 192.168.192.168). "
             "Naudojamas TIK su Print Agent.")
    nsoft_printer_port = fields.Integer(
        string="Spausdintuvo portas",
        default=9100,
        help="Spausdintuvo TCP portas (Epson default = 9100, raw ESC/POS).")

    # --- Cash register administrative settings -------------------------
    nsoft_mod = fields.Selection(
        [('BP', 'BP — Bendros paskirties'), ('RV', 'RV — Restoranai / Viešbučiai')],
        string="nSoft režimas", default='BP',
        help="BP — bendros paskirties kasa. RV — restoranų/viešbučių režimas "
             "(įgalina pre-order ir transfer endpoint'us).")
    nsoft_cashier = fields.Char(string="Kasininko vardas",
                                help="Rašomas ant kvitų (PATCH /cr/{id})")
    nsoft_round_cash = fields.Boolean(string="Apvalinti grynųjų operacijas (5 ct)",
                                      default=False)
    nsoft_retain_cash = fields.Boolean(string="Išlaikyti grynuosius po Z",
                                       default=True)

    # --- Default output format -----------------------------------------
    nsoft_output_format = fields.Selection(
        [('native', 'native'), ('plain', 'plain'), ('image', 'image')],
        string="Dokumentų formatas", default='native')
    nsoft_line_width = fields.Integer(string="Eilutės plotis (40-80)", default=80)

    # --- Payment method names (must match API enum) --------------------
    # API enum: cash, paymentCard, otherCard, coupon, transfer, other
    nsoft_payment_cash = fields.Char(
        string="nSoft: Grynųjų metodas", default='cash',
        help="nSoft mokėjimo metodo pavadinimas grynųjų mokėjimams (cash).")
    nsoft_payment_card = fields.Char(
        string="nSoft: Banko kortelės metodas", default='paymentCard',
        help="nSoft mokėjimo metodo pavadinimas banko kortelių mokėjimams "
             "(paymentCard).")
    nsoft_payment_other_card = fields.Char(
        string="nSoft: Kitos kortelės metodas", default='otherCard',
        help="Kitos kortelės (lojalumo ir pan.) — otherCard.")
    nsoft_payment_voucher = fields.Char(
        string="nSoft: Kupono metodas", default='coupon',
        help="Kupono mokėjimas — coupon.")
    nsoft_payment_transfer = fields.Char(
        string="nSoft: Banko pavedimo metodas", default='transfer',
        help="Banko pavedimas — transfer.")
    nsoft_payment_other = fields.Char(
        string="nSoft: Kitas metodas", default='other',
        help="Kitoks mokėjimas — other.")

    # --- VAT groups (match i.EKA VAT table) ----------------------------
    nsoft_vat_group_21 = fields.Char(
        string="PVM grupė 21%", default='A',
        help="Standartinio 21% tarifo grupės identifikatorius (viena raidė).")
    nsoft_vat_group_9 = fields.Char(
        string="PVM grupė 9%", default='E',
        help="9% tarifo grupės identifikatorius.")
    nsoft_vat_group_5 = fields.Char(
        string="PVM grupė 5%", default='C',
        help="5% tarifo grupės identifikatorius (jei naudojamas).")
    nsoft_vat_group_0 = fields.Char(
        string="PVM grupė 0% (neapmokestinama)", default='F',
        help="0% tarifo grupės identifikatorius.")
    nsoft_vat_group_alcohol = fields.Char(
        string="Alkoholio grupė", default='B',
        help="Specialiai alkoholiui priskirta PVM grupė.")
    nsoft_vat_group_deposit = fields.Char(
        string="Taros / depozito grupė", default='T',
        help="Taros ar depozito operacijoms priskirtas identifikatorius.")
    nsoft_vat_group_other = fields.Char(
        string="Ne-PVM (paslaugos/surinkimai) grupė", default='N',
        help="Kitiems (ne-PVM) mokėjimams priskirtas identifikatorius.")
