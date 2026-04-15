# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

from .nsoft_client import NSoftClient, NSoftAPIError, extract_document_id

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    nsoft_receipt_id = fields.Char(string='nSoft Receipt ID', readonly=True,
                                   copy=False, index=True)
    nsoft_error = fields.Char(string='nSoft Klaida', readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Odoo hook — push every created order to NSoft
    # ------------------------------------------------------------------
    @api.model
    def _process_order(self, order, draft):
        order_id = super()._process_order(order, draft)
        try:
            pos_order = self.browse(order_id)
            if pos_order and pos_order.config_id.nsoft_enabled:
                pos_order._send_to_nsoft()
        except Exception as exc:  # noqa: BLE001
            _logger.error("nSoft: klaida siunčiant užsakymą %s: %s", order_id, exc)
            try:
                self.browse(order_id).write({'nsoft_error': str(exc)[:250]})
            except Exception:  # noqa: BLE001
                pass
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
            try:
                data = client.returns(payload)
            except NSoftAPIError as exc:
                self.write({'nsoft_error': str(exc)[:250]})
                raise
        else:
            payload = {'sales': sales_lines, 'payments': payments}
            if references:
                payload['references'] = references
            try:
                data = client.receipt(payload)
            except NSoftAPIError as exc:
                self.write({'nsoft_error': str(exc)[:250]})
                raise

        receipt_id = extract_document_id(data) or str(self.id)
        self.write({'nsoft_receipt_id': receipt_id, 'nsoft_error': False})
        _logger.info("nSoft: %s -> id=%s", self.name, receipt_id)
        return receipt_id
