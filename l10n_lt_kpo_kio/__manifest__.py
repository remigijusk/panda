{
    'name': 'Lietuvos KPO ir KIO orderiai',
    'version': '19.0.2.0.0',
    'author': 'Remigijus Kubilius',
    'category': 'Accounting/Localizations',
    'summary': 'Tradiciniai KPO ir KIO orderiai iš Žurnalo įrašų (account.move) su kvitu',
    'description': """
        Modulis prideda klasikinės formos KPO ir KIO spausdinimą su kvito šaknele.
        Veikia tiesiogiai iš Žurnalo įrašų (account.move) ir kasos suderinimo lango.
        Integruotas tikslus lietuviškas sumos vertimas į žodžius.
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
