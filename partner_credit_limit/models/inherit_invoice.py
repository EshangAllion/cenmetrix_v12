from odoo import api, models, fields, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = "account.move"

    date_invoice = fields.Date(string='Invoice Date',
                               readonly=True, states={'draft': [('readonly', False)]}, index=True,
                               help="Keep empty to use the current date", copy=False)

