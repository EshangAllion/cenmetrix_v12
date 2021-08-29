from odoo import fields, api, models
from odoo.exceptions import UserError


class InheritSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def create(self, vals):
        """Inheriting the core function, create to validate to stop adding two or more taxes to the product"""
        # Validation
        if vals.get('tax_id'):
            if len(vals.get('tax_id')[0][2]) > 1:
                raise UserError('A product can only have one tax')
        return super(InheritSaleOrderLine, self).create(vals)

    def write(self, vals):
        """Inheriting the core function, write to validate to stop adding two or more taxes to the product"""
        # Validation
        if vals.get('tax_id'):
            if len(vals.get('tax_id')[0][2]) > 1:
                raise UserError('A product can only have one tax')
        return super(InheritSaleOrderLine, self).write(vals)


class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('order_line')
    def onchange_order_line(self):
        """Validating to avoid having both non and vat items together in a bill"""
        non_vat = False
        vat = False
        for line in self.order_line:
            if line.product_id:
                if line.product_id.vat_product == 'vat':
                    vat = True
                elif line.product_id.vat_product == 'nonvat':
                    non_vat = True
        if non_vat and vat:
            raise UserError("You can not have both VAT and NON-VAT Items in the same invoice.")