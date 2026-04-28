# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError

from .nsoft_client import NSoftClient, NSoftAPIError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_nsoft_enabled = fields.Boolean(related='pos_config_id.nsoft_enabled', readonly=False)
    pos_nsoft_api_url = fields.Char(related='pos_config_id.nsoft_api_url', readonly=False)
    pos_nsoft_pos_id = fields.Char(related='pos_config_id.nsoft_pos_id', readonly=False)
    pos_nsoft_token = fields.Char(related='pos_config_id.nsoft_token', readonly=False)

    pos_nsoft_mod = fields.Selection(related='pos_config_id.nsoft_mod', readonly=False)
    pos_nsoft_cashier = fields.Char(related='pos_config_id.nsoft_cashier', readonly=False)
    pos_nsoft_round_cash = fields.Boolean(related='pos_config_id.nsoft_round_cash', readonly=False)
    pos_nsoft_retain_cash = fields.Boolean(related='pos_config_id.nsoft_retain_cash', readonly=False)
    pos_nsoft_output_format = fields.Selection(related='pos_config_id.nsoft_output_format', readonly=False)
    pos_nsoft_line_width = fields.Integer(related='pos_config_id.nsoft_line_width', readonly=False)

    pos_nsoft_payment_cash = fields.Char(related='pos_config_id.nsoft_payment_cash', readonly=False)
    pos_nsoft_payment_card = fields.Char(related='pos_config_id.nsoft_payment_card', readonly=False)
    pos_nsoft_payment_other_card = fields.Char(related='pos_config_id.nsoft_payment_other_card', readonly=False)
    pos_nsoft_payment_voucher = fields.Char(related='pos_config_id.nsoft_payment_voucher', readonly=False)
    pos_nsoft_payment_transfer = fields.Char(related='pos_config_id.nsoft_payment_transfer', readonly=False)
    pos_nsoft_payment_other = fields.Char(related='pos_config_id.nsoft_payment_other', readonly=False)

    pos_nsoft_vat_group_21 = fields.Char(related='pos_config_id.nsoft_vat_group_21', readonly=False)
    pos_nsoft_vat_group_9 = fields.Char(related='pos_config_id.nsoft_vat_group_9', readonly=False)
    pos_nsoft_vat_group_5 = fields.Char(related='pos_config_id.nsoft_vat_group_5', readonly=False)
    pos_nsoft_vat_group_0 = fields.Char(related='pos_config_id.nsoft_vat_group_0', readonly=False)
    pos_nsoft_vat_group_alcohol = fields.Char(related='pos_config_id.nsoft_vat_group_alcohol', readonly=False)
    pos_nsoft_vat_group_deposit = fields.Char(related='pos_config_id.nsoft_vat_group_deposit', readonly=False)
    pos_nsoft_vat_group_other = fields.Char(related='pos_config_id.nsoft_vat_group_other', readonly=False)

    def _require_connection(self):
        self.ensure_one()
        if not self.pos_nsoft_enabled:
            raise UserError("Pirmiausia ijunkite nSoft fiskalizacija.")
        if not self.pos_nsoft_api_url or not self.pos_nsoft_token:
            raise UserError("Uzpildykite API URL ir Token laukus.")
        return NSoftClient.from_config(self.pos_config_id, require_pos=False)

    def _notify(self, title, message, ntype='success'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': title, 'message': message, 'type': ntype, 'sticky': False},
        }

    def action_test_nsoft_connection(self):
        client = self._require_connection()
        try:
            data = client.version()
        except NSoftAPIError as exc:
            raise UserError(f"Nepavyko pasiekti nSoft: {exc}")
        version = (data or {}).get('version', '?')
        mod = (data or {}).get('mod', '?')
        return self._notify("Rysys veikia!",
                            f"nVirtualFiscal v{version} (mod {mod}).")

    def action_nsoft_get_version(self):
        return self.action_test_nsoft_connection()

    def action_nsoft_get_info(self):
        client = self._require_connection()
        if not self.pos_nsoft_pos_id:
            raise UserError("Truksta POS ID.")
        try:
            data = client.get_info()
        except NSoftAPIError as exc:
            raise UserError(f"Klaida: {exc}")
        content = (data or {}).get('content', {}) if isinstance(data, dict) else {}
        msg = (
            f"Fiskaline diena Nr.: {content.get('fiscalDayNo', '-')}\n"
            f"Paskutinis kvitas: {content.get('lastFiscalNo', '-')}\n"
            f"Grynieji stalciuje: {content.get('cashDrawerAmount', '-')} EUR\n"
            f"Dienos pardavimai: {content.get('daySalesAmount', '-')} EUR"
        )
        return self._notify("Kasos bukle", msg)

    def action_nsoft_push_vat(self):
        self.ensure_one()
        wizard = self.env['pos.nsoft.vat.push'].create({'pos_config_id': self.pos_config_id.id})
        return wizard.action_push()

    def action_nsoft_force_sync(self):
        client = self._require_connection()
        try:
            client.force_sync()
        except NSoftAPIError as exc:
            raise UserError(f"Sinchronizacijos klaida: {exc}")
        return self._notify("Sinchronizacija", "Duomenys sinchronizuoti su STI.")

    def action_nsoft_patch_settings(self):
        """Push cashier / rounding settings to the CR via PATCH /cr/{id}."""
        client = self._require_connection()
        payload = {
            'cashier': self.pos_nsoft_cashier or '',
            'roundCash': bool(self.pos_nsoft_round_cash),
            'retainCash': bool(self.pos_nsoft_retain_cash),
        }
        try:
            client.patch_cash_register(payload)
        except NSoftAPIError as exc:
            raise UserError(f"Nepavyko atnaujinti kasos nustatymu: {exc}")
        return self._notify("Kasos aparatas", "Nustatymai issiusti i i.EKA.")

    def action_nsoft_list_registers(self):
        client = self._require_connection()
        try:
            data = client.list_cash_registers()
        except NSoftAPIError as exc:
            raise UserError(f"Klaida: {exc}")
        content = (data or {}).get('content') if isinstance(data, dict) else data
        return self._notify("Aktyvios kasos", ', '.join(content or []) or '(nera)')
