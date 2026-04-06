{
    'name': 'Lietuvos KPO ir KIO orderiai (Kasos žurnalui + POS)',
    'version': '19.0.33.0.0',
    'author': 'Remigijus Kubilius',
    'category': 'Accounting/Localizations',
    'summary': 'KPO/KIO spausdinimas iš banko sudengimų ir POS užsakymų',
    'depends': ['account', 'sign', 'point_of_sale'],
    'data': [
        'report/kpo_kio_reports.xml',
        'views/res_config_settings_views.xml',
        'views/pos_order_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
