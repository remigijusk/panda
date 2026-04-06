{
    'name': 'Lietuvos KPO POS Orderis (Galutinis variantas)',
    'version': '19.0.28.0.0',
    'author': 'Remigijus Kubilius',
    'category': 'Point of Sale/Localizations',
    'summary': 'Standartinės formos KPO spausdinimas su automatiniais parašais tiesiai iš POS užsakymo lango',
    'description': """
        Modulis prideda klasikinės formos KPO spausdinimą iš Pardavimo taško.
        - Mygtukas atsira POS užsakymo lange (Header).
        - Mygtukas matomas tik jei apmokėta per KPO ir jei įjungtas nustatymas.
        - Pilnas A4 PDF šablonas su orderiu (viršuje) ir kvitu (apačioje).
        - Pilni rekvizitai, serijos, numeriai ir pagrindai abiejose dalyse.
        - AUTOMATINIS KASININKO PARAŠAS: Paima vartotojo skaitmeninį parašą iš Odoo profilio.
    """,
    'depends': ['account', 'sign', 'point_of_sale'],
    'data': [
        'report/kpo_report.xml',
        'report/kpo_report_template.xml',
        'views/res_config_settings_views.xml',
        'views/pos_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
