# -*- coding: utf-8 -*-
{
    'name': 'nSoft Odoo.19 POS Fiskaline kasa',
    'version': '19.0.1.212.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Kasos aparato darbo programa, valdanti nSoft virtualia fiskalizacija (i.EKA)',
    'description': """
nSoft Odoo.19 POS Fiskaline kasa
================================

Taikomoji kasos aparato funkciju valdymo programa, skirta UAB nSoft
gaminamam kasos aparatui "Kasos aparatas nSoft bendrosios paskirties
su virtualia fiskalizacija". Programa veikia Odoo 19 POS aplinkoje ir
atlieka visas fiskalines operacijas per nVirtualFiscal (i.EKA) REST API:
pardavimo kvitai, grazinimai, X/Z ataskaitos, inkasavimas/ismokejimas,
PVM lentele, sinchronizacija su VMI.
""",
    'author': 'Remigijus Kubilius, UAB TUTAS',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/pos_session_views.xml',
    ],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_nsoft_fiscal/static/src/js/payment_screen.js',
            'pos_nsoft_fiscal/static/src/xml/OrderReceipt.xml',
            'pos_nsoft_fiscal/static/src/xml/ProductScreen.xml',
        ],
    },
    'license': 'LGPL-3',
}
