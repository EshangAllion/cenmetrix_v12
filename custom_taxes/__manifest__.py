{
	'name': 'Customization of Taxes and VAT',
	'sequence': 1,
	'version': '1.0',
	'summary': 'Customization of Taxes and VAT',
	'author': 'Allion Technologies PVT Ltd',
	'website': 'http://www.alliontechnologies.com/',
	'description': """Customization of Taxes and VAT""",
	'depends': ['base', 'product', 'sale', 'account', 'purchase'],
	'data': [
		'views/custom_product_view.xml',
		'views/custom_res_partner_view.xml',
		# 'reports/invoice_paper_format.xml',
		# 'reports/custom_invoice_reports.xml',
	],
	'installable': True,
	'application': True,
	'auto_install': False,
}
