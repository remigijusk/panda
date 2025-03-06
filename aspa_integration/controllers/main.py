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

        if not cmd:
            return {"success": False, "message": "Missing required parameters: cmd"}

        base_url = request.env.user.company_id.aspa_api_url + '/json/fp550/Cmdline' or 'http://127.0.0.1:8111/json/fp550/Cmdline'
        payload = {"cmd": cmd, "parameter": parameter}

        try:
            response = requests.post(base_url, json=payload, timeout=10)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.RequestException as e:
            return {"success": False, "message": str(e)}

    @http.route('/aspa/bankas0', type='json', auth='user', csrf=False)
    def aspa_bankas0(self):
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
        except ValueError:
            return {"success": False, "message": "Invalid JSON payload"}

        amount = data.get('amount')
        if not amount:
            return {"success": False, "message": "Missing amount parameter"}

        base_url = request.env.user.company_id.aspa_api_url + '/json/fp550/BankasSale0' or 'http://127.0.0.1:8111/json/fp550/BankasSale0'
        payload = {"amount": str(amount)}

        try:
            response = requests.post(base_url, json=payload, timeout=10)
            response.raise_for_status()

            try:
                response_data = response.json()
                return {"success": True, "data": response_data}
            except json.JSONDecodeError:
                return {"success": False, "message": "Invalid JSON response from BankasSale0",
                        "raw_response": response.text}

        except requests.RequestException as e:
            return {"success": False, "message": str(e)}
