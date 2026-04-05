{
    'name': 'Lietuvos KPO ir KIO orderiai (Suderinimo langui + POS)',
    'version': '19.0.26.0.0',
    'author': 'Remigijus Kubilius',
    'category': 'Accounting/Localizations',
    'summary': 'KPO/KIO spausdinimas su automatiniais parašais ir POS integracija',
    'depends': ['account', 'sign', 'point_of_sale'],
    'data': [
        'report/kpo_kio_report.xml',
        'report/kpo_kio_template.xml',
        'report/pos_kpo_report.xml',
        'views/res_config_settings_views.xml',
        'views/pos_order_views.xml', # Naujas failas mygtukui
    ],
    'installable': True,
    'license': 'LGPL-3',
}
