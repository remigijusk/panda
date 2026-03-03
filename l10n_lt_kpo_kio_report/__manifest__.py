{
    'name': 'Lietuvos KPO ir KIO spausdinimas',
    'version': '18.0.1.4.0',
    'category': 'Accounting/Localizations',
    'summary': 'Spausdinti lietuviškus Kasos Pajamų Orderius (KPO) ir Kasos Išlaidų Orderius (KIO)',
    'description': """
    Šis modulis prideda galimybę spausdinti Kasos pajamų orderį (KPO) ir Kasos išlaidų orderį (KIO) 
    tiesiai iš Žurnalo įrašų (account.move). 
    Automatiškai sugeneruoja sumą žodžiais pagal partnerio kalbą bei užpildo "Pagrindas" lauką iš kasos eilutės etiketės.
    Prideda tiesioginį spausdinimo mygtuką į sąskaitos formą.
    """,
    'author': 'Remigijus Kubilius',
    'website': 'https://remonasa.com',
    'email': 'remonasa1975@gmail.com',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
        'report/account_move_kpo_kio_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
