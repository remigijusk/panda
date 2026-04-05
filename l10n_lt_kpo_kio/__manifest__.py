{
    'name': 'Lietuvos KPO ir KIO orderiai (Suderinimo langui + POS)',
    'version': '19.0.14.0.0',
    'author': 'Remigijus Kubilius',
    'category': 'Accounting/Localizations',
    'summary': 'KPO/KIO spausdinimas iš banko suderinimo ir automatiškai iš POS',
    'depends': ['account', 'sign', 'point_of_sale'],
    'data': [
        'report/kpo_kio_report.xml',
        'report/kpo_kio_template.xml',
        'report/pos_kpo_report.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_lt_kpo_kio/static/src/js/pos_kpo_button.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
