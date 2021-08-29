{
    'name': 'Reset Invoices to Draft',
    'version': '1.0',
    'sequence': 1,
    'author': "Allion Technologies PVT Ltd",
    'website': 'http://www.alliontechnologies.com/',
    'summary': 'Unreserve Qty',
    'description': """Reset Invoices to Draft""",
    'depends': [
        'account'
    ],
    'data': [
        'views/inherit_account_move.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}