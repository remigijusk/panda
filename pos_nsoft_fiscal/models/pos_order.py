# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from .nsoft_client import (
    NSoftClient,
    NSoftAPIError,
    extract_default_format,
    extract_document_id,
    extract_receipt_text,
)

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    nsoft_receipt_id = fields.Char(string='nSoft Receipt ID', readonly=True,
                                   copy=False, index=True)
    nsoft_receipt_text = fields.Text(
        string='nSoft Kvito tekstas', readonly=True, copy=False,
        help="Suformatuotas kvito tekstas, gautas iš nVirtualFiscal API. "
             "Šis tekstas yra vienintelis teisėtas spausdinimui — Odoo savo "
             "kvito šablono nespausdina (VMI reikalavimas).",
    )
    nsoft_error = fields.Char(string='nSoft Klaida', readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Odoo hook — push every created order to NSoft
    # ------------------------------------------------------------------
    @api.model
    def _process_order(self, order, draft):
        """Override: every order MUST be successfully fiscalized.

        Pagal VMI ir UAB „nSoft" reikalavimą, kasos aparato programa neleis
        prekybos neatspausdinus čekio. Jei nVirtualFiscal grąžina klaidą,
        užsakymas atmetamas (Odoo transakcija rollback'inama) ir kasininkui
        rodomas klaidos pranešimas — bandyti pakartotinai.
        """
        order_id = super()._process_order(order, draft)
        pos_order = self.browse(order_id)
        if not pos_order or not pos_order.config_id.nsoft_enabled:
            return order_id
        try:
            pos_order._send_to_nsoft()
        except NSoftAPIError as exc:
            _logger.error("nSoft: užsakymo %s fiskalizacija nepavyko: %s",
                          order_id, exc)
            # Reject the sale — VMI requires no sale without fiscal receipt
            raise UserError(
                f"Pardavimas atmestas: nVirtualFiscal (i.EKA) kvitas "
                f"nepateiktas.\n\n{exc}\n\n"
                f"Patikrinkite kasos aparato ryšį ir bandykite dar kartą."
            )
        except Exception as exc:  # noqa: BLE001
            _logger.exception(
                "nSoft: nelaukta klaida siunčiant užsakymą %s", order_id)
            raise UserError(
                f"Pardavimas atmestas: vidinė fiskalizacijos klaida.\n\n{exc}"
            )
        return order_id

    # ------------------------------------------------------------------
    # Mappings
    # ------------------------------------------------------------------
    _PAYMENT_KEYWORDS = (
        # (field name on pos.config, iterable of lowercase keywords in payment name)
        ('nsoft_payment_card', ('card', 'kortel', 'bank', 'banko', 'visa', 'master')),
        ('nsoft_payment_voucher', ('voucher', 'kupon', 'dovan', 'wolt', 'bolt', 'coupon')),
        ('nsoft_payment_transfer', ('transfer', 'pavedim', 'iban', 'wire')),
        ('nsoft_payment_other_card', ('loyal', 'lojal', 'gift', 'other card')),
        ('nsoft_payment_other', ('other', 'kita')),
    )

    def _get_nsoft_payment_method(self, payment):
        config = self.config_id
        name = (payment.payment_method_id.name or '').lower().strip()
        for field_name, keywords in self._PAYMENT_KEYWORDS:
            if any(k in name for k in keywords):
                return (getattr(config, field_name) or '').strip() or field_name
        return (config.nsoft_payment_cash or 'cash').strip()

    def _get_nsoft_vat_code(self, line, config):
        """Return the VAT group identifier for the sale line."""
        try:
            if not line.tax_ids:
                return (config.nsoft_vat_group_0 or 'F').strip()

            # Detect special categories via product name / category keywords
            text = ' '.join(filter(None, [
                (line.product_id.display_name or ''),
                (line.product_id.categ_id.display_name or ''),
            ])).lower()
            if any(w in text for w in ('alkohol', 'alcohol', 'vyn', 'alus', 'beer',
                                       'wine', 'spirit', 'degtin', 'vodka', 'whisk')):
                return (config.nsoft_vat_group_alcohol or 'B').strip()
            if any(w in text for w in ('tara', 'deposit', 'depozit', 'butel')):
                return (config.nsoft_vat_group_deposit or 'T').strip()

            rate = int(round(float(line.tax_ids[0].amount)))
            if rate == 21:
                return (config.nsoft_vat_group_21 or 'A').strip()
            if rate == 9:
                return (config.nsoft_vat_group_9 or 'E').strip()
            if rate == 5:
                return (config.nsoft_vat_group_5 or 'C').strip()
            if rate == 0:
                return (config.nsoft_vat_group_0 or 'F').strip()
            return (config.nsoft_vat_group_21 or 'A').strip()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("nSoft vatCode klaida: %s", exc)
            return 'A'

    # ------------------------------------------------------------------
    # Payload builders
    # ------------------------------------------------------------------
    def _build_nsoft_sales_lines(self):
        config = self.config_id
        lines = []
        for line in self.lines:
            qty = round(abs(line.qty), 3)
            line_incl = round(abs(line.price_subtotal_incl), 2)
            name = (line.full_product_name
                    or line.product_id.display_name
                    or 'Prekė')[:50]
            unit_price = round(line_incl / qty, 4) if qty else line_incl
            entry = {
                'description': name,
                'quantity': qty,
                'unitPrice': unit_price,
                'lineAmount': line_incl,
                'vatCode': self._get_nsoft_vat_code(line, config),
            }
            disc = getattr(line, 'discount', 0) or 0
            if disc:
                gross = round(unit_price * qty, 2)
                if gross > line_incl:
                    entry['lineDiscount'] = round(gross - line_incl, 2)
            lines.append(entry)

        # Correct rounding drift so that sum(lineAmount) == amount_total
        total_incl = round(abs(self.amount_total), 2)
        sum_lines = round(sum(i['lineAmount'] for i in lines), 2)
        diff = round(total_incl - sum_lines, 2)
        if abs(diff) > 0.001 and lines:
            lines[-1]['lineAmount'] = round(lines[-1]['lineAmount'] + diff, 2)
            if lines[-1]['quantity']:
                lines[-1]['unitPrice'] = round(
                    lines[-1]['lineAmount'] / lines[-1]['quantity'], 4)
        return lines

    def _build_nsoft_payments(self):
        config = self.config_id
        payments = []
        for payment in self.payment_ids:
            amount = round(abs(payment.amount), 2)
            if amount <= 0:
                continue
            payments.append({
                'method': self._get_nsoft_payment_method(payment),
                'amount': amount,
            })
        if not payments:
            payments = [{
                'method': (config.nsoft_payment_cash or 'cash').strip(),
                'amount': round(abs(self.amount_total), 2),
            }]
        return payments

    # ------------------------------------------------------------------
    # Main dispatch
    # ------------------------------------------------------------------
    def _send_to_nsoft(self):
        self.ensure_one()
        config = self.config_id
        client = NSoftClient.from_config(config)

        is_refund = self.amount_total < 0
        sales_lines = self._build_nsoft_sales_lines()
        payments = self._build_nsoft_payments()

        # Always request a printable output from nVF — the returned text
        # is the only legally-valid receipt content we are allowed to print.
        out_format = extract_default_format(config)

        # References to original orders (for refunds / split receipts)
        references = []
        if is_refund and getattr(self, 'refunded_order_id', False):
            orig = self.refunded_order_id
            if orig.nsoft_receipt_id and orig.nsoft_receipt_id.isdigit():
                references.append(int(orig.nsoft_receipt_id))

        if is_refund:
            # Map every sale line into a ReturnLine referencing the original document
            returns = []
            for line in sales_lines:
                ret = dict(line)
                if references:
                    ret['origDocNumber'] = references[0]
                returns.append(ret)
            payload = {'returns': returns, 'payments': payments}
            payload.update(out_format)
            try:
                data = client.returns(payload)
            except NSoftAPIError as exc:
                self.write({'nsoft_error': str(exc)[:250]})
                raise
        else:
            payload = {'sales': sales_lines, 'payments': payments}
            if references:
                payload['references'] = references
            payload.update(out_format)
            try:
                data = client.receipt(payload)
            except NSoftAPIError as exc:
                self.write({'nsoft_error': str(exc)[:250]})
                raise

        receipt_id = extract_document_id(data) or str(self.id)
        receipt_text = extract_receipt_text(data) or ''
        self.write({
            'nsoft_receipt_id': receipt_id,
            'nsoft_receipt_text': receipt_text,
            'nsoft_error': False,
        })
        _logger.info("nSoft: %s -> id=%s (text %d chars)",
                     self.name, receipt_id, len(receipt_text))
        return receipt_id
