from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    x_suma_zodziais = fields.Char(
        string='Suma žodžiais', 
        help='Įveskite sumą žodžiais kasos orderiui (pvz.: Šimtas penkiasdešimt eurų 00 ct.)'
    )