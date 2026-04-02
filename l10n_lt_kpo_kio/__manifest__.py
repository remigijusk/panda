{
    'name': 'Lietuvos KPO ir KIO orderiai (Suderinimo langui)',
    'version': '19.0.5.0.0',
    'author': 'Remigijus Kubilius',
    'category': 'Accounting/Localizations',
    'summary': 'KPO/KIO spausdinimas su tiksliais rekvizitais ir pritaikytu A4 formatu',
    'description': """
        Modulis prideda klasikinės formos KPO/KIO spausdinimą.
        - Veikia tiesiogiai iš "Banko sąskaitos suderinimas" lango.
        - Dinamiškas kasininko vardo/pavardės paėmimas.
        - Teisingas įmonės kodo atvaizdavimas.
        - Mokėtojo/Gavėjo parašų laukai.
        - Priskirtas specialus A4 popieriaus formatas su sumažintomis paraštėmis (telpa į vieną lapą).
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
