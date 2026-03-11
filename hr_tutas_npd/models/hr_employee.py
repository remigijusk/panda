from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    x_is_npd_applied = fields.Boolean(string='Taikyti NPD')
    x_is_fixed_npd = fields.Boolean(string='Fiksuotas NPD')

    npd_taikymas = fields.Selection([
        ('taikyti', 'Taikyti NPD'),
        ('netaikyti', 'Netaikyti NPD')
    ], string='NPD Pasirinkimas', default='netaikyti')
    npd_data = fields.Date(string='NPD Taikymo Data')
    npd_suma = fields.Float(string='Individuali NPD Suma')
