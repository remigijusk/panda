{
    'name': 'Lietuvos KPO ir KIO orderiai (Suderinimo langui)',
    'version': '19.0.3.0.0',
    'author': 'Remigijus Kubilius',
    'category': 'Accounting/Localizations',
    'summary': 'KPO/KIO spausdinimas tiesiai iš Banko/Kasos suderinimo eilučių (Bank Statements)',
    'description': """
        Modulis prideda klasikinės formos KPO/KIO spausdinimą.
        Pritaikyta veikti TIESIOGIAI iš "Banko sąskaitos suderinimas" lango (account.bank.statement.line).
        Pilnai atitinka LT reikalavimus, įskaitant sumos vertimą į žodžius.
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
