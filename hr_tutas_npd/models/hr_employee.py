from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Nauji loginiai laukeliai (Checkbox)
    x_is_npd_applied = fields.Boolean(string='Taikyti NPD')
    x_is_fixed_npd = fields.Boolean(string='Fiksuotas NPD')

    # Senieji laukeliai (jei reikia istorijai)
    npd_taikymas = fields.Selection([
        ('taikyti', 'Taikyti NPD'),
        ('netaikyti', 'Netaikyti NPD')
    ], string='NPD Pasirinkimas', default='netaikyti')
    npd_data = fields.Date(string='NPD Taikymo Data')
    npd_suma = fields.Float(string='Individuali NPD Suma')
