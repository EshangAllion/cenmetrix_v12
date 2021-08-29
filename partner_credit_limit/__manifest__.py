
{
    'name': 'Partner Credit Limit',
    'version': '1.01',
    'category': 'sale',
    'sequence': 1,
    'license': '',
    'author': 'Allion Technologies PVT Ltd',
    'website': 'http://www.alliontechnologies.com',
    'maintainer': 'Allion Technologies PVT Ltd',
    'summary': 'Set credit limit warning to sale order',
    'depends': [
        'sale_management', 'sale_discount_total'
    ],
    'data': [
        'security/partner_credit_limit_security.xml',
        'security/ir.model.access.csv',
        'wizard/send_approve_pending_view.xml',
        'wizard/send_approve_paymet_term_view.xml',
        'views/sale_view.xml',
        'views/partner_view.xml',
        'views/inherit_invoice_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
