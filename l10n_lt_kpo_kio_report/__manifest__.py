{
    'name': 'Lietuvos KPO ir KIO spausdinimas',
    'version': '18.0.1.2.0',
    'category': 'Accounting/Localizations',
    'summary': 'Spausdinti lietuviškus Kasos Pajamų Orderius (KPO) ir Kasos Išlaidų Orderius (KIO)',
    'description': """
    Šis modulis prideda galimybę spausdinti Kasos pajamų orderį (KPO) ir Kasos išlaidų orderį (KIO) 
    tiesiai iš Žurnalo įrašų (account.move). 
    Automatiškai sugeneruoja sumą žodžiais bei užpildo "Pagrindas" lauką iš operacijos eilučių.
    Prideda tiesioginį spausdinimo mygtuką į sąskaitos formą.
    """,
    'author': 'Remigijus Kubilius',
    'website': 'https://www.remonasa.lt',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
        'report/account_move_kpo_kio_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
