# -*- coding: utf-8 -*-
import json as _json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from .nsoft_client import (
    NSoftClient,
    NSoftAPIError,
    extract_default_format,
    extract_receipt_text,
)

_logger = logging.getLogger(__name__)


def _notification(title, message, ntype='success'):
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {'title': title, 'message': message, 'type': ntype, 'sticky': False},
    }


class PosSession(models.Model):
    _inherit = 'pos.session'

    # ------------------------------------------------------------------
    # Loader: expose nSoft fields to the POS frontend
    # ------------------------------------------------------------------
    def _loader_params_pos_order(self):
        result = super()._loader_params_pos_order()
        result['search_params']['fields'].append('nsoft_receipt_id')
        result['search_params']['fields'].append('nsoft_receipt_text')
        result['search_params']['fields'].append('nsoft_error')
        return result

    # ------------------------------------------------------------------
    # Opening: push cash-in to nSoft
    # ------------------------------------------------------------------
    def set_opening_control(self, opening_notes, opening_cash):
        """On session opening, push opening balance as a cash-in to NSoft."""
        try:
            cash_float = float(opening_cash or 0.0)
        except (TypeError, ValueError):
            cash_float = 0.0

        res = super().set_opening_control(opening_notes, cash_float)

        if cash_float > 0:
            for session in self.sudo().filtered(lambda s: s.config_id.nsoft_enabled):
                try:
                    session._send_nsoft_cash_operation('in', cash_float)
                    _logger.info("nSoft: atidarymo cash-in %.2f EUR (%s)",
                                 cash_float, session.name)
                except Exception as exc:  # noqa: BLE001
                    _logger.error("nSoft: atidarymo cash-in klaida: %s", exc)
        return res

    # ------------------------------------------------------------------
    # Closing: Z report MUST succeed before Odoo allows session close
    # ------------------------------------------------------------------
    def action_pos_session_closing_control(self, balancing_account=False,
                                           amount_to_balance=0,
                                           bank_payment_method_diffs=None):
        """Bind Z report to Odoo session close.

        Jei Z nepavyksta - sesija NEUZDARYTA, kasininkas turi sutvarkyti
        rysi ir bandyti is naujo.
        """
        for session in self.filtered(lambda s: s.config_id.nsoft_enabled):
            try:
                session._send_nsoft_z_report()
                _logger.info("nSoft: Z ataskaita uzbaigta (%s)", session.name)
            except NSoftAPIError as exc:
                _logger.error("nSoft Z ataskaita nepavyko: %s", exc)
                raise UserError(
                    f"Sesijos uzdarymas atmestas - Z ataskaita nepateikta "
                    f"i nVirtualFiscal (i.EKA):\n\n{exc}\n\n"
                    f"Patikrinkite kasos aparato rysi ir bandykite "
                    f"uzdaryti sesija dar karta."
                )
        return super().action_pos_session_closing_control(
            balancing_account=balancing_account,
            amount_to_balance=amount_to_balance,
            bank_payment_method_diffs=bank_payment_method_diffs,
        )

    # ------------------------------------------------------------------
    # Primitive dispatchers
    # ------------------------------------------------------------------
    def _nsoft_client(self):
        self.ensure_one()
        return NSoftClient.from_config(self.config_id)

    def _send_nsoft_cash_operation(self, direction, amount):
        """Call POST /cr/{id}/cash with output format request."""
        self.ensure_one()
        if not self.config_id.nsoft_enabled:
            return False
        client = self._nsoft_client()
        out = extract_default_format(self.config_id).get('output')
        return client.cash(direction, amount, output=out)

    def _send_nsoft_z_report(self):
        self.ensure_one()
        if not self.config_id.nsoft_enabled:
            return False
        client = self._nsoft_client()
        out = extract_default_format(self.config_id).get('output')
        return client.fis_day(output=out)

    def _send_nsoft_x_report(self):
        self.ensure_one()
        if not self.config_id.nsoft_enabled:
            return False
        client = self._nsoft_client()
        out = extract_default_format(self.config_id).get('output')
        return client.cur_day(output=out)

    # ------------------------------------------------------------------
    # Public RPC-callable methods (POS frontend buttons)
    # ------------------------------------------------------------------
    def do_nsoft_cash_op(self, direction, amount, reason=None):
        """Combined cash in/out: nSoft + Odoo bank statement line + receipt.

        Frontend kviecia si metoda is mygtuku 'Pinigu idejimas/isemimas (i.EKA)'.
        Tvarka:
          1. Siunciam i nSoft pirma - jei nepavyksta, NIEKO nedarom Odoo puseje
          2. Sukuriam Odoo bank statement line (kad cash drawer ir accounting
             matytu operacija)
          3. Grazinam kvito teksta frontend'ui spausdinimui
        """
        self.ensure_one()
        if direction not in ('in', 'out'):
            raise UserError("Bloga kryptis.")
        try:
            amount_f = float(amount)
        except (TypeError, ValueError):
            raise UserError("Bloga suma.")
        if amount_f <= 0:
            raise UserError("Suma turi buti teigiama.")

        # 1. Send to nSoft FIRST so a failure prevents desync with Odoo
        try:
            data = self._send_nsoft_cash_operation(direction, amount_f)
        except NSoftAPIError as exc:
            return {
                'success': False,
                'title': 'i.EKA klaida',
                'message': str(exc),
                'receipt_text': '',
            }

        # 2. Create Odoo bank statement line for accounting/cash drawer
        title = 'Pinigu idejimas' if direction == 'in' else 'Pinigu isemimas'
        try:
            sign = 1 if direction == 'in' else -1
            journal = self.cash_journal_id
            if journal:
                self.env['account.bank.statement.line'].sudo().create({
                    'pos_session_id': self.id,
                    'journal_id': journal.id,
                    'amount': sign * amount_f,
                    'date': fields.Date.context_today(self),
                    'payment_ref': (reason or title),
                })
        except Exception as exc:  # noqa: BLE001
            _logger.warning("nSoft: nepavyko sukurti Odoo statement line: %s", exc)
            # Continue - nSoft is the source of truth, accounting can be reconciled later

        # 3. Return receipt text
        text = extract_receipt_text(data) or ''
        return {
            'success': True,
            'title': title,
            'message': f"{amount_f:.2f} EUR uzregistruota.",
            'receipt_text': text,
        }

    def print_nsoft_x_report(self):
        self.ensure_one()
        if not self.config_id.nsoft_enabled:
            raise UserError("nSoft fiskalizacija neijungta.")
        try:
            data = self._send_nsoft_x_report()
        except NSoftAPIError as exc:
            return {'success': False, 'title': 'i.EKA klaida', 'message': str(exc)}
        _logger.info("nSoft X-report raw: %s", _json.dumps(data, ensure_ascii=False)[:4000])
        text = extract_receipt_text(data)
        if not text:
            text = _json.dumps(data, ensure_ascii=False, indent=2)
        return {
            'success': True,
            'title': 'X Ataskaita',
            'message': 'X ataskaita suformuota.',
            'receipt_text': text,
            'raw': data,
        }

    def print_nsoft_z_report(self):
        self.ensure_one()
        if not self.config_id.nsoft_enabled:
            raise UserError("nSoft fiskalizacija neijungta.")
        try:
            data = self._send_nsoft_z_report()
        except NSoftAPIError as exc:
            return {'success': False, 'title': 'i.EKA klaida', 'message': str(exc)}
        _logger.info("nSoft Z-report raw: %s", _json.dumps(data, ensure_ascii=False)[:4000])
        text = extract_receipt_text(data)
        if not text:
            text = _json.dumps(data, ensure_ascii=False, indent=2)
        return {
            'success': True,
            'title': 'Z Ataskaita',
            'message': 'Fiskaline diena uzdaryta.',
            'receipt_text': text,
            'raw': data,
        }

    def action_nsoft_min_day(self):
        self.ensure_one()
        client = self._nsoft_client()
        out = extract_default_format(self.config_id).get('output')
        try:
            client.min_day(output=out)
        except NSoftAPIError as exc:
            return _notification("i.EKA klaida", str(exc), 'danger')
        return _notification("Min. dienos ataskaita", "Ataskaita sekmingai suformuota.")

    def action_nsoft_sync(self):
        self.ensure_one()
        client = self._nsoft_client()
        try:
            data = client.force_sync(output=extract_default_format(self.config_id).get('output'))
        except NSoftAPIError as exc:
            return _notification("i.EKA klaida", str(exc), 'danger')
        _logger.info("nSoft sync: %s", data)
        return _notification("Sinchronizacija", "Kasos aparatas sinchronizuotas su STI.")

    def action_nsoft_info(self):
        self.ensure_one()
        client = self._nsoft_client()
        try:
            data = client.get_info()
        except NSoftAPIError as exc:
            return _notification("i.EKA klaida", str(exc), 'danger')
        content = (data or {}).get('content', {}) if isinstance(data, dict) else {}
        msg = (
            f"Fiskaline diena: {content.get('fiscalDayNo', '-')}\n"
            f"Paskutinis kvitas: {content.get('lastFiscalNo', '-')}\n"
            f"Grynieji stalciuje: {content.get('cashDrawerAmount', '-')} EUR\n"
            f"Pardavimai: {content.get('totalSalesAmount', '-')} EUR"
        )
        return _notification("Kasos bukle", msg)
