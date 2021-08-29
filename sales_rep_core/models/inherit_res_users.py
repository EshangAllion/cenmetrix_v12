from odoo import fields, api, models


class InheritResUsers(models.Model):
    _inherit = 'res.users'

    monthly_target = fields.Float(string="Monthly Target")
    frequency = fields.Integer("Frequency", default=10)
    no_of_products = fields.Integer("Number of Products", default=5)