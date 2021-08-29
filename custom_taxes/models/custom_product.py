from odoo import models,fields,api
from odoo.exceptions import UserError


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    vat_product = fields.Selection([('vat','VAT item'),('nonvat','NON VAT item')], string='VAT Status', store='True', default='nonvat')
    taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id',
                                help="Default taxes used when selling the product.", string='VAT',
                                domain=[('type_tax_use', '=', 'sale')],
                                default=lambda self: self.env.user.company_id.account_sale_tax_id,
                                store='True')

    # the field is emptied when state change to nonvat
    @api.onchange('vat_product')
    def value_clear_validation(self):
        """
             This method consist of the modifications done to the non vat item. New field is added as vat status which contains
             values vat items and non vat items when a non vat item is selected the values in the VAT field is erased
        """
        if self.vat_product == 'nonvat':
            self.taxes_id = False
        else:
            pass

    @api.model
    def create(self, vals):
        """Inheriting the core function, create to validate to stop adding two or more taxes to the product"""
        # Validation
        if vals.get('taxes_id'):
            if len(vals.get('taxes_id')[0][2]) > 1:
                raise UserError('A product can only have one tax')
        return super(ProductTemplateInherit, self).create(vals)

    def write(self, vals):
        """Inheriting the core function, write to validate to stop adding two or more taxes to the product"""
        # Validation
        if vals.get('taxes_id'):
            if len(vals.get('taxes_id')[0][2]) > 1:
                raise UserError('A product can only have one tax')
        return super(ProductTemplateInherit, self).write(vals)


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    # the field is emptied when state change to nonvat
    @api.onchange('vat_product')
    def value_clear_validation(self):
        """
             This method consist of the modifications done to the non vat item. New field is added as vat status which contains
             values vat items and non vat items when a non vat item is selected the values in the VAT field is erased
        """
        if self.vat_product == 'nonvat':
            self.taxes_id = False
        else:
            pass

    @api.model
    def create(self, vals):
        """Inheriting the core function, create to validate to stop adding two or more taxes to the product"""
        # Validation
        if vals.get('taxes_id'):
            if len(vals.get('taxes_id')[0][2]) > 1:
                raise UserError('A product can only have one tax')
        return super(ProductProductInherit, self).create(vals)

    def write(self, vals):
        """Inheriting the core function, write to validate to stop adding two or more taxes to the product"""
        # Validation
        if vals.get('taxes_id'):
            if len(vals.get('taxes_id')[0][2]) > 1:
                raise UserError('A product can only have one tax')
        return super(ProductProductInherit, self).write(vals)