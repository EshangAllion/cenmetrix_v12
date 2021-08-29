from odoo import models, fields, api


class InheritPaymentTerms(models.Model):
    _inherit = 'account.payment.term'

    collecting_date = fields.Integer("Collecting Days")