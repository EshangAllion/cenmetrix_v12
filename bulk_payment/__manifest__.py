# -*- coding: utf-8 -*-
{
    'name': 'Bulk Payment',
    'version': '1.1',
    'category': 'Accounting',
    'sequence': 0,
    'summary': 'User able to execute multiple payments at one time',
    'description': """""",
    'website': 'http://www.alliontechnologies.com/',
    'depends': ['account', 'account_check_printing'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/account_payment_register_view.xml',
        'views/account_payment_view.xml',
        'data/sequence_data.xml',
        'data/account_payment_data.xml',
        'report_templates/paperformats.xml',
        'report_templates/cheque_ac_payee_only_without_20.xml',
        'report_templates/cheque_ac_payee_only_with_20.xml',
        'report_templates/cheque_cash_with_20.xml',
        'report_templates/cheque_cash_without_20.xml',
        # 'report_templates/payment_voucher.xml',
        'report_templates/payment_voucher_paperformat.xml',
        'report_templates/payment_voucher_report.xml',
        'report_templates/payment_receipt.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
