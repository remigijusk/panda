# -*- coding: utf-8 -*-
"""Extra nSoft API operations exposed as transient wizards so that they
can be invoked from the Odoo back-end (and via RPC from the POS UI).
"""
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from .nsoft_client import NSoftClient, NSoftAPIError, extract_default_format

_logger = logging.getLogger(__name__)


def _config_from_context(env):
    config_id = env.context.get('default_pos_config_id') or env.context.get('active_pos_config_id')
    if config_id:
        return env['pos.config'].browse(config_id)
    active_model = env.context.get('active_model')
    if active_model == 'pos.config' and env.context.get('active_id'):
        return env['pos.config'].browse(env.context['active_id'])
    if active_model == 'pos.session' and env.context.get('active_id'):
        return env['pos.session'].browse(env.context['active_id']).config_id
    configs = env['pos.config'].search([('nsoft_enabled', '=', True)], limit=1)
    if not configs:
        raise UserError("Nerasta POS konfigūracija su įjungta nSoft fiskalizacija.")
    return configs


class NSoftOpWizard(models.TransientModel):
    _name = 'pos.nsoft.op.wizard'
    _description = 'nSoft Operation Wizard'

    pos_config_id = fields.Many2one('pos.config', string='POS', required=True,
                                    default=lambda self: _config_from_context(self.env).id)
    operation = fields.Selection([
        ('pre_order', 'Pre-order (RV)'),
        ('advance', 'Advance payment'),
        ('transfer', 'Transfer to hotel account (RV)'),
        ('non_fis_doc', 'Non-fiscal document'),
        ('cancel', 'Cancel unfinished purchase'),
    ], string='Operacija', required=True, default='non_fis_doc')

    name = fields.Char(string='Dokumento pavadinimas')
    description = fields.Char(string='Prekės / paslaugos aprašymas')
    quantity = fields.Float(string='Kiekis', default=1.0)
    unit_price = fields.Float(string='Vieneto kaina')
    line_amount = fields.Float(string='Eilutės suma')
    vat_code = fields.Char(string='VAT kodas', help="Pvz.: A, E, F, N, T, B")
    free_text = fields.Text(string='Laisvas tekstas (non-fis-doc eilutėms)')
    reference_doc = fields.Integer(string='Nuoroda į dokumentą (pvz. pre-order Nr.)')

    # ------------------------------------------------------------------
    def _build_line(self):
        amount = self.line_amount or (self.unit_price * (self.quantity or 1.0))
        line = {
            'description': (self.description or self.name or 'Operacija')[:50],
            'quantity': self.quantity or 1.0,
            'unitPrice': round(self.unit_price or amount, 4),
            'lineAmount': round(amount, 2),
        }
        if self.vat_code:
            line['vatCode'] = self.vat_code.strip()
        return line

    def _client(self):
        self.ensure_one()
        return NSoftClient.from_config(self.pos_config_id)

    def action_run(self):
        self.ensure_one()
        client = self._client()
        out = extract_default_format(self.pos_config_id)
        payload = dict(out)

        try:
            if self.operation == 'pre_order':
                payload['sales'] = [self._build_line()]
                data = client.pre_order(payload)
            elif self.operation == 'advance':
                payload['sales'] = [self._build_line()]
                payload['payments'] = [{
                    'method': (self.pos_config_id.nsoft_payment_cash or 'cash'),
                    'amount': round(self.line_amount
                                    or self.unit_price * (self.quantity or 1.0), 2),
                }]
                data = client.advance(payload)
            elif self.operation == 'transfer':
                payload['sales'] = [self._build_line()]
                if self.reference_doc:
                    payload['references'] = [int(self.reference_doc)]
                data = client.transfer(payload)
            elif self.operation == 'cancel':
                payload['sales'] = [self._build_line()]
                data = client.cancel(payload)
            elif self.operation == 'non_fis_doc':
                lines = []
                for row in (self.free_text or '').splitlines():
                    lines.append({'type': 'text', 'content': row, 'align': 'left'})
                data = client.non_fis_doc(
                    name=(self.name or 'Informacinis dokumentas'),
                    lines=lines,
                    output=payload.get('output'),
                )
            else:
                raise UserError(f"Nepalaikoma operacija: {self.operation}")
        except NSoftAPIError as exc:
            raise UserError(f"nSoft grąžino klaidą: {exc}")

        _logger.info("nSoft op %s -> %s", self.operation, str(data)[:300])
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'nSoft',
                'message': 'Operacija sėkmingai įvykdyta.',
                'type': 'success',
                'sticky': False,
            },
        }


class NSoftHistoryWizard(models.TransientModel):
    _name = 'pos.nsoft.history.wizard'
    _description = 'nSoft History / Report Wizard'

    pos_config_id = fields.Many2one('pos.config', string='POS', required=True,
                                    default=lambda self: _config_from_context(self.env).id)
    report = fields.Selection([
        ('history', 'Dokumentų istorija'),
        ('summary', 'Suvestinė ataskaita'),
        ('detail', 'Detali ataskaita'),
    ], string='Ataskaita', required=True, default='history')
    spec = fields.Selection([('date', 'Pagal datą'), ('id', 'Pagal ID')],
                            required=True, default='date')
    value_from = fields.Char(string='Nuo', required=True)
    value_to = fields.Char(string='Iki', required=True)
    result = fields.Text(string='Atsakymas', readonly=True)

    def action_run(self):
        self.ensure_one()
        client = NSoftClient.from_config(self.pos_config_id)
        out = extract_default_format(self.pos_config_id).get('output')
        try:
            if self.report == 'history':
                data = client.history(self.spec, self.value_from, self.value_to, output=out)
            elif self.report == 'summary':
                data = client.summary_report(self.spec, self.value_from, self.value_to, output=out)
            else:
                data = client.detail_report(self.spec, self.value_from, self.value_to, output=out)
        except NSoftAPIError as exc:
            raise UserError(f"nSoft klaida: {exc}")
        import json
        self.result = json.dumps(data, indent=2, ensure_ascii=False)[:8000]
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class NSoftVatTable(models.TransientModel):
    """Push the current pos.config VAT groups to nSoft as a VATTable."""
    _name = 'pos.nsoft.vat.push'
    _description = 'nSoft VAT Table push'

    pos_config_id = fields.Many2one('pos.config', required=True,
                                    default=lambda self: _config_from_context(self.env).id)

    def action_push(self):
        self.ensure_one()
        cfg = self.pos_config_id
        client = NSoftClient.from_config(cfg)
        groups = []

        def add_group(ident, rate, exempt=False):
            if ident:
                entry = {'g': ident.strip(), 'r': rate}
                if exempt:
                    entry['e'] = True
                groups.append(entry)

        add_group(cfg.nsoft_vat_group_21, 21)
        add_group(cfg.nsoft_vat_group_alcohol, 21)
        add_group(cfg.nsoft_vat_group_5, 5)
        add_group(cfg.nsoft_vat_group_9, 9)
        add_group(cfg.nsoft_vat_group_0, 0, exempt=True)
        add_group(cfg.nsoft_vat_group_deposit, 0, exempt=True)
        add_group(cfg.nsoft_vat_group_other, 0, exempt=True)

        payload = {
            'a': (cfg.nsoft_vat_group_alcohol or 'B').strip(),
            'd': (cfg.nsoft_vat_group_deposit or 'T').strip(),
            'o': (cfg.nsoft_vat_group_other or 'N').strip(),
            's': groups,
        }
        try:
            client.update_vat(payload)
        except NSoftAPIError as exc:
            raise UserError(f"PVM lentelės atnaujinimas nepavyko: {exc}")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'nSoft',
                'message': 'PVM lentelė atnaujinta.',
                'type': 'success',
                'sticky': False,
            },
        }
