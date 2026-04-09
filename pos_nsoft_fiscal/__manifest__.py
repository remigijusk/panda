# -*- coding: utf-8 -*-
{
    'name': 'nSoft Virtual Fiscalization for POS',
    'version': '19.0.1.67.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Tiesioginė nVirtualFiscal (i.EKA) integracija per REST API',
    'description': """
        v1.67.0: Pakeista "Testuoti ryšį" mygtuko logika. Užuot siuntus 0.00 EUR pinigų įnešimą (kurį nSoft atmeta su 400 Bad Request klaida), dabar ryšys testuojamas iškviečiant X ataskaitą (/cur-day).
    """,
    'author': 'Remigijus Kubilius',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/pos_session_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
