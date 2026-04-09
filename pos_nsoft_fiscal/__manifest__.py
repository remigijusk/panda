# -*- coding: utf-8 -*-
{
    'name': 'nSoft Virtual Fiscalization for POS',
    'version': '19.0.1.65.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Tiesioginė nVirtualFiscal (i.EKA) integracija per REST API',
    'description': """
        v1.65.0: Atsisakyta nepatikimo ir klaidų sukeliančio JS 'patching' metodo PaymentScreen lange. Logika perkelta išskirtinai į Python backend (pos_order.py) ir XML šabloną. Atstatytas 100% Odoo stabilumas, išsaugant pilną nSoft funkcionalumą pajungtose kasose.
    """,
    'author': 'Remigijus Kubilius',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/pos_session_views.xml',
    ],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_nsoft_fiscal/static/src/xml/OrderReceipt.xml',
        ],
    },
    'license': 'LGPL-3',
}
