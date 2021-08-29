{
    'name': 'Pidilite Core',
    'version': '1.01',
    'category': 'sale',
    'sequence': 1,
    'license': '',
    'author': 'Allion Technologies PVT Ltd',
    'website': 'http://www.alliontechnologies.com',
    'maintainer': 'Allion Technologies PVT Ltd',
    'summary': 'Set credit limit warning to sale order',
    'depends': [
        'account_payment', 'account', 'custom_invoice', 'sale_discount_total'
    ],
    'data': [
        'data/payment_method.xml',
        'views/inherit_sale_order.xml',
        'views/inherit_invoice.xml',
        'reports/invoice_pdf.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
