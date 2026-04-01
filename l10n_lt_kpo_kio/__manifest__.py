{
    'name': 'Lietuvos KPO ir KIO orderiai',
    'version': '19.0.1.3.0',
    'author': 'Remigijus Kubilius',
    'category': 'Accounting/Localizations',
    'summary': 'Pritaikyta Lietuvos rinkai: Kasos pajamų ir išlaidų orderių spausdinimas PDF formatu',
    'description': """
        Modulis prideda KPO ir KIO spausdinimo funkcionalumą prie mokėjimų (account.payment).
        - Suma žodžiu
        - Privalomi rekvizitai (pagrindas, gavėjas/mokėtojas)
        - PDF generavimas
    """,
    'depends': ['account'],
    'data': [
        'report/kpo_kio_report.xml',
        'report/kpo_kio_template.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
