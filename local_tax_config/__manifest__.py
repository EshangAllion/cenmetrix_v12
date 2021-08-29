{
	'name': 'Local Tax Configuration',
	'version': '0.1',
	'summary': 'Local Tax Configuration',
	'author': 'Centrics Business Solutions',
	'maintainer': 'Centrics Business Solutions',
	'company': 'Centrics Business Solutions',
	'website': 'http://www.centrics.cloud/',
	'depends': ['sale', 'account'],
	'data': [
        'views/inherit_tax_view.xml',
        'views/inherit_customer_view.xml',
	],
	'images': [],
	'license': 'AGPL-3',
	'installable': True,
	'application': True,
	'auto_install': False,
}
