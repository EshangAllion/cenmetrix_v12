{
    'name': 'Age Analysis Report',
    'version': '1.0',
    'sequence': 1,
    'author': "Allion Technologies PVT Ltd",
    'website': 'http://www.alliontechnologies.com/',
    'summary': 'Age Analysis Report',
    'description': """Age Analysis Report""",
    'depends': ['base', 'sale', 'sale_management', 'account', 'sale_stock'],
    'data': [
        'views/inherit_invoice_view.xml',
        'wizards/age_analysis_report_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}