from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Tik šitie du dabar yra pagrindiniai
    x_is_npd_applied = fields.Boolean(string='Taikyti NPD')
    x_is_fixed_npd = fields.Boolean(string='Fiksuotas NPD')

    # Šituos paliekame tik jei jums reikia įrašyti datą ar sumą
    npd_data = fields.Date(string='NPD Taikymo Data')
    npd_suma = fields.Float(string='Individuali NPD Suma')
