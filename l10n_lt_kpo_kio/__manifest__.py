{
    'name': 'Lietuvos KPO ir KIO orderiai (Suderinimo langui)',
    'version': '19.0.4.0.0',
    'author': 'Remigijus Kubilius',
    'category': 'Accounting/Localizations',
    'summary': 'KPO/KIO spausdinimas su tiksliais rekvizitais ir dinamišku kasininku',
    'description': """
        Modulis prideda klasikinės formos KPO/KIO spausdinimą.
        - Dinamiškas kasininko vardo/pavardės paėmimas.
        - Teisingas įmonės kodo atvaizdavimas.
        - Mokėtojo/Gavėjo parašų laukai.
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
