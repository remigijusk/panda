# -*- coding: utf-8 -*-
import json as _json
import logging

from odoo import api, models
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
    # Cash In / Out: Odoo POS standard hook -> also call nSoft + return text
    # ------------------------------------------------------------------
    def try_cash_in_out(self, _type, amount, reason, extras):
        """Override Odoo POS cash drawer in/out so that:

        1. The standard Odoo bank statement line is created (super()).
        2. The same operation is registered on nSoft (POST /cr/{id}/cash).
        3. The nSoft-returned printable receipt text is appended to the
           result so the POS frontend can print it via pos.printer.

        If nSoft fails, the operation is REJECTED (UserError) so that the
        Odoo cash drawer stays in sync with the fiscal cash drawer.
        """
        result = super().try_cash_in_out(_type, amount, reason, extras)
        if not self.config_id.nsoft_enabled:
            return result
        try:
            direction = 'in' if _type == 'in' else 'out'
            data = self._send_nsoft_cash_operation(direction, abs(float(amount)))
        except NSoftAPIError as exc:
            _logger.error("nSoft cash-%s nepavyko: %s", _type, exc)
            raise UserError(
                f"Inkasavimo operacija atmesta - nVirtualFiscal (i.EKA) "
                f"klaida:\n\n{exc}"
            )
        text = extract_receipt_text(data) or ''
        if isinstance(result, dict):
            result['nsoft_receipt_text'] = text
            result['nsoft_title'] = 'Pinigu idejimas' if direction == 'in' else 'Pinigu isemimas'
        else:
            # Odoo may return a list (statement line ids) - wrap into dict
            result = {
                'odoo_result': result,
                'nsoft_receipt_text': text,
                'nsoft_title': 'Pinigu idejimas' if direction == 'in' else 'Pinigu isemimas',
            }
        return result

    # ------------------------------------------------------------------
    # Closing: Z report MUST succeed before Odoo allows session close
    # ------------------------------------------------------------------
    def action_pos_session_closing_control(self, balancing_account=False,
                                           amount_to_balance=0,
                                           bank_payment_method_diffs=None):
        """Bind Z report to Odoo session close.

        Pagal VMI / nSoft reikalavima sesijos uzdarymas neturi vykti be
        galiojancios Z ataskaitos. Jei Z nepavyksta - sesija NEUZDARYTA,
        kasininkas turi sutvarkyti ir bandyti is naujo.

        Z atspausdinimas vyksta kliento puseje (POS frontend) - cia tik
        suformuojama ir saugojama ataskaita. Faktinis spausdinimas ivyksta
        kai vartotojas kviecia close_session_from_ui.
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

    def action_nsoft_cash_in(self, amount):
        self.ensure_one()
        if not amount or float(amount) <= 0:
            raise UserError("Iveskite teigiama suma.")
        self._send_nsoft_cash_operation('in', float(amount))
        return _notification("Cash-in", f"{float(amount):.2f} EUR uzregistruota.")

    def action_nsoft_cash_out(self, amount):
        self.ensure_one()
        if not amount or float(amount) <= 0:
            raise UserError("Iveskite teigiama suma.")
        self._send_nsoft_cash_operation('out', float(amount))
        return _notification("Cash-out", f"{float(amount):.2f} EUR uzregistruota.")

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
