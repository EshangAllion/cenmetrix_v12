from odoo import fields, models, api
from datetime import datetime


class InheritAccountInvoiceAgeAnalysis(models.Model):
    _inherit = 'account.move'

    invoice_age = fields.Integer(string="Invoice Age", compute='get_invoice_age')

    def get_invoice_age(self):
        """Calculating invoice age by days"""
        for line in self:
            if line.invoice_date:
                if line.invoice_date <= datetime.today().date():
                    #  subtracting invoice_date from current date
                    line.invoice_age = (datetime.today().date() - line.invoice_date).days
                else:
                    line.invoice_age = 0
            else:
                line.invoice_age = 0


