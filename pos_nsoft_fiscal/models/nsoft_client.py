# -*- coding: utf-8 -*-
"""Shared HTTP client for nSoft nVirtualFiscal REST API.

Covers all endpoints described in the nVirtualFiscal Service API
reference (v1.17). The client is intentionally stateless — callers
pass the pos.config record (or a dict with api_url / pos_id / token)
and the client builds, signs and dispatches the request.
"""
import logging
import requests

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15


class NSoftAPIError(Exception):
    """Raised when the NSoft service returns a non-2xx response."""

    def __init__(self, status, message, payload=None):
        super().__init__(f"nSoft {status}: {message}")
        self.status = status
        self.message = message
        self.payload = payload


class NSoftClient(object):
    """Thin wrapper around the nVirtualFiscal REST endpoints."""

    def __init__(self, api_url, pos_id, token, timeout=DEFAULT_TIMEOUT):
        if not api_url or not token:
            raise UserError("nSoft: trūksta API URL arba Token.")
        self.api_url = api_url.rstrip('/')
        self.pos_id = (pos_id or '').strip()
        self.token = token
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_config(cls, config, require_pos=True):
        if not config:
            raise UserError("nSoft: nerasta POS konfigūracija.")
        client = cls(
            api_url=config.nsoft_api_url,
            pos_id=config.nsoft_pos_id,
            token=config.nsoft_token,
        )
        if require_pos and not client.pos_id:
            raise UserError("nSoft: trūksta POS ID (pvz.: CR-000000530).")
        return client

    # ------------------------------------------------------------------
    # Low level request plumbing
    # ------------------------------------------------------------------
    def _headers(self, with_auth=True):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        if with_auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def _url(self, path, with_cr=True):
        path = path.lstrip('/')
        if with_cr:
            if not self.pos_id:
                raise UserError("nSoft: trūksta POS ID.")
            return f"{self.api_url}/cr/{self.pos_id}/{path}" if path else f"{self.api_url}/cr/{self.pos_id}"
        return f"{self.api_url}/{path}" if path else self.api_url

    def _parse(self, response):
        try:
            data = response.json()
        except ValueError:
            data = {'raw': response.text[:500]}

        if not response.ok:
            msg = 'Unknown error'
            if isinstance(data, dict):
                msg = data.get('message') or data.get('error') or response.text[:300]
            raise NSoftAPIError(response.status_code, msg, data)
        return data

    def request(self, method, path, *, with_cr=True, json=None, with_auth=True):
        url = self._url(path, with_cr=with_cr)
        method = method.upper()
        _logger.debug("nSoft %s %s payload=%s", method, url, (str(json)[:500] if json else ''))
        try:
            response = requests.request(
                method, url,
                headers=self._headers(with_auth=with_auth),
                json=json,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise NSoftAPIError(0, f"Ryšio klaida: {exc}")
        return self._parse(response)

    # ------------------------------------------------------------------
    # General purpose
    # ------------------------------------------------------------------
    def version(self):
        return self.request('GET', 'version', with_cr=False, with_auth=False)

    # ------------------------------------------------------------------
    # Setup & configuration
    # ------------------------------------------------------------------
    def list_cash_registers(self):
        # GET /cr  (no CR id in the URL)
        return self.request('GET', '', with_cr=False, with_auth=False)

    def create_cash_register(self, payload):
        return self.request('POST', '', with_cr=False, json=payload)

    def get_cash_register(self):
        return self.request('GET', '', with_cr=True)

    def update_cash_register(self, payload):
        return self.request('PUT', '', json=payload)

    def patch_cash_register(self, payload):
        return self.request('PATCH', '', json=payload)

    def delete_cash_register(self):
        return self.request('DELETE', '')

    def get_vat(self):
        return self.request('GET', 'vat')

    def update_vat(self, payload):
        return self.request('POST', 'vat', json=payload)

    def get_sync(self):
        return self.request('GET', 'sync')

    def force_sync(self, output=None):
        return self.request('POST', 'sync', json={'output': output} if output else {})

    # ------------------------------------------------------------------
    # Counters & journal
    # ------------------------------------------------------------------
    def get_info(self):
        return self.request('GET', 'info')

    def history(self, spec='date', date_from=None, date_to=None, output=None):
        body = {'spec': spec}
        if date_from is not None:
            body['from'] = str(date_from)
        if date_to is not None:
            body['to'] = str(date_to)
        if output:
            body['output'] = output
        return self.request('POST', 'history', json=body)

    # ------------------------------------------------------------------
    # Financial operations
    # ------------------------------------------------------------------
    def receipt(self, payload):
        return self.request('POST', 'receipt', json=payload)

    def returns(self, payload):
        return self.request('POST', 'return', json=payload)

    def advance(self, payload):
        return self.request('POST', 'advance', json=payload)

    def cash(self, direction, amount, output=None):
        if direction not in ('in', 'out'):
            raise UserError("nSoft: cash direction turi būti 'in' arba 'out'.")
        body = {'direction': direction, 'amount': round(float(amount), 2)}
        if output:
            body['output'] = output
        return self.request('POST', 'cash', json=body)

    # ------------------------------------------------------------------
    # Restaurant / Hotel specific
    # ------------------------------------------------------------------
    def pre_order(self, payload):
        return self.request('POST', 'pre-order', json=payload)

    def transfer(self, payload):
        return self.request('POST', 'transfer', json=payload)

    # ------------------------------------------------------------------
    # Non-financial operations
    # ------------------------------------------------------------------
    def non_fis_doc(self, name, lines, output=None):
        body = {'name': name, 'lines': lines or []}
        if output:
            body['output'] = output
        return self.request('POST', 'non-fis-doc', json=body)

    def cancel(self, payload):
        return self.request('POST', 'cancel', json=payload)

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    def fis_day(self, output=None):
        return self.request('POST', 'fis-day', json={'output': output} if output else {})

    def cur_day(self, output=None):
        return self.request('POST', 'cur-day', json={'output': output} if output else {})

    def min_day(self, output=None):
        return self.request('POST', 'min-day', json={'output': output} if output else {})

    def summary_report(self, spec='date', date_from=None, date_to=None, output=None):
        body = {'spec': spec}
        if date_from is not None:
            body['from'] = str(date_from)
        if date_to is not None:
            body['to'] = str(date_to)
        if output:
            body['output'] = output
        return self.request('POST', 'summary-report', json=body)

    def detail_report(self, spec='date', date_from=None, date_to=None, output=None):
        body = {'spec': spec}
        if date_from is not None:
            body['from'] = str(date_from)
        if date_to is not None:
            body['to'] = str(date_to)
        if output:
            body['output'] = output
        return self.request('POST', 'detail-report', json=body)


# ---------------------------------------------------------------------------
# Utility helpers used by callers
# ---------------------------------------------------------------------------
def extract_document_id(data):
    """Given an API response (DocumentListMessage or DetailedDocumentListMessage)
    return the first document id / number as a string, or ''."""
    if not data:
        return ''
    content = data
    if isinstance(data, dict):
        content = data.get('content', data)
    if isinstance(content, list):
        content = content[0] if content else {}
    if isinstance(content, dict):
        doc = content.get('document') or {}
        rid = (
            content.get('id')
            or content.get('receiptId')
            or content.get('receiptNumber')
            or doc.get('id')
        )
        if rid is not None:
            return str(rid)
    return ''


def extract_receipt_text(data):
    """Extract the printable report / receipt text from a NSoft response.

    NSoft returns the formatted print-ready text inside the content[0]
    document. The field name varies: 'data', 'print', 'text', 'output'.
    """
    if not data:
        return ''
    content = data.get('content', data) if isinstance(data, dict) else data
    if isinstance(content, list):
        content = content[0] if content else {}
    if not isinstance(content, dict):
        return str(content) if content else ''
    # Try common locations
    for key in ('data', 'print', 'text', 'output', 'body', 'receipt'):
        val = content.get(key)
        if isinstance(val, str) and val.strip():
            return val
    doc = content.get('document') or {}
    if isinstance(doc, dict):
        for key in ('data', 'print', 'text', 'output', 'body', 'receipt'):
            val = doc.get(key)
            if isinstance(val, str) and val.strip():
                return val
    return ''


def extract_default_format(config):
    """Build an OutputFormatRequest dict according to pos.config settings."""
    fmt = (getattr(config, 'nsoft_output_format', None) or 'native').strip()
    try:
        lw = int(getattr(config, 'nsoft_line_width', 0) or 0)
    except (TypeError, ValueError):
        lw = 0
    out = {'format': fmt}
    if lw:
        out['lineWidth'] = lw
    return {'output': out}
