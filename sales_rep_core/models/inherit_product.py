from odoo import fields, api, models


class InheritProductTemplate(models.Model):
    _inherit = 'product.template'

    mrp = fields.Float(string="MRP", default=1.0, digits='Product Price', track_visibility='always')
    list_price = fields.Float('Sales Price', default=1.0, digits='Product Price', help="Price at which the product is sold to customers.", track_visibility='always')

    is_promotion_product = fields.Boolean(string="Promotion Product")
    eligible_qty = fields.Float('Eligible Quantity')
    free_issue_qty = fields.Float('Free Issue Quantity')

    _sql_constraints = [
        ('default_code_unique', 'unique(default_code)', "A record exist with the same reference")]


class InheritProductProduct(models.Model):
    _inherit = 'product.product'

    _sql_constraints = [
        ('default_code_unique', 'unique(default_code)', "A record exist with the same reference")]