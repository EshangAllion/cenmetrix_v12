from odoo import models,fields,api
from odoo.exceptions import UserError


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    vat_customer = fields.Selection([('vat','VAT Contact'),('nonvat','NON VAT Contact')], string='VAT Status', store='True', default='nonvat')