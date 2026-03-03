from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    x_suma_zodziais = fields.Char(
        string='Suma žodžiais', 
        compute='_compute_kpo_kio_data',
        store=True,
        readonly=False,
        help='Automatiškai sugeneruota suma žodžiais (galima redaguoti)'
    )
    x_pagrindas = fields.Char(
        string='Pagrindas',
        compute='_compute_kpo_kio_data',
        store=True,
        readonly=False,
        help='Automatiškai surinkta informacija iš operacijos eilučių'
    )

    @api.depends('line_ids', 'line_ids.debit', 'line_ids.credit', 'line_ids.name', 'currency_id')
    def _compute_kpo_kio_data(self):
        for move in self:
            # Randame kasos sąskaitos eilutę (asset_cash tipo)
            cash_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_cash')
            
            if cash_line:
                # Imame pirmą rastą kasos eilutę sumai nustatyti
                line = cash_line[0]
                amount = max(line.debit, line.credit)
                
                # Sugeneruojame sumą žodžiais naudojant Odoo standartinį metodą
                if move.currency_id:
                    move.x_suma_zodziais = move.currency_id.amount_to_text(amount)
                else:
                    move.x_suma_zodziais = str(amount)
                
                # Surenkame "Pagrindą" iš visų eilučių, kurios NĖRA kasos sąskaita
                other_lines = move.line_ids.filtered(lambda l: l.account_id.account_type != 'asset_cash' and not l.display_type)
                labels = [l.name for l in other_lines if l.name]
                # Pašaliname dublikatus ir sujungiame
                move.x_pagrindas = ", ".join(list(dict.fromkeys(labels)))
            else:
                move.x_suma_zodziais = ""
                move.x_pagrindas = ""

    def action_print_kpo_kio(self):
        """ Iškviečia KPO/KIO ataskaitos spausdinimą """
        return self.env.ref('l10n_lt_kpo_kio_report.action_report_lt_kpo_kio').report_action(self)