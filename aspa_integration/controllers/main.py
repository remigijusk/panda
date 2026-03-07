from odoo import http
from odoo.http import request
import requests
import json


class ASPAController(http.Controller):

    @http.route('/aspa/command', type='json', auth='user', csrf=False)
    def aspa_command(self):
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
        except ValueError:
            return {"success": False, "message": "Invalid JSON payload"}

        cmd = data.get('cmd')
        parameter = data.get('parameter')
        pos_config_id = data.get('pos_config_id')

        print("Received command:", cmd)
        print('Config ID:', pos_config_id)

        pos_config = request.env['pos.config'].sudo().browse(pos_config_id) if pos_config_id else request.env.user.company_id.pos_config_id

        if not cmd:
            return {"success": False, "message": "Missing required parameters: cmd"}

        base_url = pos_config.aspa_api_url + '/json/fp550/Cmdline' or 'http://127.0.0.1:8111/json/fp550/Cmdline'
        payload = {"cmd": cmd, "parameter": parameter}

        try:
            response = requests.post(base_url, json=payload, timeout=40)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.RequestException as e:
            return {"success": False, "message": str(e)}

    @http.route('/aspa/bankassale0', type='json', auth='user', csrf=False)
    def aspa_bankas_sale0(self, amount=None, pos_config_id=None):
        if amount is None:
            return {"success": False, "message": "Missing amount"}

        if pos_config_id is None:
            pos_config_id = request.env.user.company_id.pos_config_id.id

        pos_config = request.env['pos.config'].sudo().browse(pos_config_id)

        if not pos_config or not pos_config.aspa_api_url:
            return {"success": False, "message": "Invalid pos config or missing ASPA URL"}

        url = (pos_config.aspa_api_url or 'http://127.0.0.1:8111') + '/json/fp550/BankasSale0'
        payload = {"amount": str(amount)}

        try:
            response = requests.post(url, json=payload, timeout=40)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.RequestException as e:
            return {"success": False, "message": str(e)}
