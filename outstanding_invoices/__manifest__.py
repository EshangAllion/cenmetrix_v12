{
    'name': 'Outstanding Invoices Temporary Table',
    'version': '1.0',
    'category': 'Sales',
    'sequence': 0,
    'author': 'Allion Technologies PVT Ltd',
    'website': 'http://www.alliontechnologies.com/',
    'summary': 'Outstanding Invoices Temporary Table',
    'description': """Outstanding Invoices Temporary Table""",
    'depends': ['account', 'invoice_outstanding', 'bulk_payment'],
    'data': [
        'security/ir.model.access.csv',
        'data/schedule_action.xml',
        'views/temporary_table.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
