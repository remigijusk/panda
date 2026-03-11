from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    npd_taikymas = fields.Selection([
        ('taikyti', 'Taikyti NPD'),
        ('netaikyti', 'Netaikyti NPD')
    ], string='NPD Pasirinkimas', default='netaikyti', tracking=True)
    
    npd_data = fields.Date(string='NPD Taikymo Data', tracking=True)
    
    npd_suma = fields.Float(string='Individuali NPD Suma', 
                            help='Pildyti tik jei taikoma nestandartinė suma')
