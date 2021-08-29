from odoo import fields, models
from odoo import fields, api, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    over_credit = fields.Boolean('Allow Over Credit?', default=True)
    remaining_credit_limit = fields.Float("Remaining Credit Limit", readonly=True, invisible=True)

    @api.onchange('credit_limit')
    def credit_limit_validation(self):
        """check initial credit limit of the customer & if it credit limit is
        greater than 0 allow over credit limit become true"""
        if self.credit_limit > 0:
            self.over_credit = False
