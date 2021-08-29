{
    'name': 'Sales return modification',
    'version': '1.0',
    'category': 'Accounting',
    'sequence': 1,
    'author': "Allion Technologies PVT Ltd",
    'website': 'http://www.alliontechnologies.com/',
    'summary': 'new sales return with credit note',
    'description': """Sales return modification""",
    'depends': ['base', 'stock', 'account'],
    'data': [
        'views/stock_picking_inherit_view.xml',
        'views/operation_types_inherit.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
