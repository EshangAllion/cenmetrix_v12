from odoo import fields, api, models


class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    user_id = fields.Many2one(
        'res.users', string='Salesperson', index=True, tracking=2, default=lambda self: self.env.user,
        domain=lambda self: [('groups_id', 'in', [self.env.ref('sales_team.group_sale_salesman').id, self.env.ref('base.group_portal').id, self.env.ref('base.group_public').id])])
    visit_id = fields.Many2one('customer.visits', string="Visit")


class InheritSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    mrp = fields.Float(string="MRP", strore=True)
    is_free_issue = fields.Boolean(string="Free Issue")

    @api.model
    def create(self, vals):
        # Inheriting create function
        return_obj = super(InheritSaleOrderLine, self).create(vals)
        if return_obj.product_id:
            return_obj.mrp = return_obj.product_id.mrp
        return return_obj


class InheritCrmTeam(models.Model):
    _inherit = 'crm.team'

    member_ids = fields.One2many(
        'res.users', 'sale_team_id', string='Channel Members', check_company=True,
        domain=lambda self: [('groups_id', 'in', [self.env.ref('sales_team.group_sale_salesman').id, self.env.ref('base.group_portal').id, self.env.ref('base.group_public').id])],
        help="Add members to automatically assign their documents to this sales team. You can only be member of one team.")