from odoo import fields, api, models


class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    user_id = fields.Many2one(
        'res.users', string='Salesperson', index=True, tracking=2, default=lambda self: self.env.user,
        domain=lambda self: [('groups_id', 'in', [self.env.ref('sales_team.group_sale_salesman').id, self.env.ref('base.group_portal').id, self.env.ref('base.group_public').id])])
    visit_id = fields.Many2one('customer.visits', string="Visit")