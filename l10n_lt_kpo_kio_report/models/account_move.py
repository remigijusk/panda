from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    x_suma_zodziais = fields.Char(
        string='Suma žodžiais', 
        compute='_compute_kpo_kio_data',
        store=True,
        readonly=False,
    )
    x_pagrindas = fields.Char(
        string='Pagrindas',
        compute='_compute_kpo_kio_data',
        store=True,
        readonly=False,
    )

    @api.depends('line_ids', 'line_ids.debit', 'line_ids.credit', 'line_ids.name', 'currency_id', 'partner_id')
    def _compute_kpo_kio_data(self):
        for move in self:
            # Randame kasos sąskaitos eilutę (asset_cash tipo)
            cash_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_cash')
            
            if cash_line:
                # Imame pirmą rastą kasos eilutę duomenims
                line = cash_line[0]
                amount = max(line.debit, line.credit)
                
                # Sugeneruojame sumą žodžiais pagal partnerio kalbą
                if move.currency_id:
                    # Naudojame partnerio kalbą, jei ji nustatyta, kitaip vartotojo kalbą
                    lang = move.partner_id.lang or self.env.user.lang or 'lt_LT'
                    move.x_suma_zodziais = move.currency_id.with_context(lang=lang).amount_to_text(amount)
                else:
                    move.x_suma_zodziais = str(amount)
                
                # Pagrindas imamas tiesiai iš kasos eilutės etiketės (name)
                move.x_pagrindas = line.name or ""
            else:
                move.x_suma_zodziais = ""
                move.x_pagrindas = ""

    def action_print_kpo_kio(self):
        """ Iškviečia KPO/KIO ataskaitos spausdinimą """
        return self.env.ref('l10n_lt_kpo_kio_report.action_report_lt_kpo_kio').report_action(self)
