from odoo import fields, api, models


class InheritAccountTax(models.Model):
    _inherit = 'account.tax'

    vat_type = fields.Selection([('vat', 'VAT'), ('s_vat', 'SVAT'), ('other', 'Other')], string="Local Tax Type")

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, type_tax_use, vat_type)', 'Tax names must be unique !'),
    ]


class CustomerInherit(models.Model):
    _inherit = 'res.partner'

    vat_type = fields.Selection([('non_vat', 'Non VAT'),
                                 ('s_vat', 'SVAT'),
                                 ('vat', 'VAT')], string="VAT Type", default='non_vat')
    svat_no = fields.Char('SVAT No')
    vat = fields.Char(string='Tax No',
                      help="The Tax Identification Number. Complete it if the contact is subjected to government taxes. Used in some legal statements.")


class CompanyInherit(models.Model):
    _inherit = 'res.company'

    svat_no = fields.Char(related='partner_id.svat_no', string='SVAT No', readonly=False)
    vat = fields.Char(related='partner_id.vat', string="VAT No", readonly=False)


class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    svat = fields.Float(string="SVAT Amount", compute='get_svat_value')
    vat_type = fields.Selection([('non_vat', 'Non VAT'), ('s_vat', 'SVAT'), ('vat', 'VAT')], string="VAT Type", default='non_vat', related='partner_id.vat_type')

    @api.depends('amount_untaxed')
    def get_svat_value(self):
        """get svat amount calculation"""
        for line in self:
            if line.partner_id.vat_type == 's_vat':
                svat = 0
                for item in line.order_line:
                    if_tax = item.tax_id
                    tax = if_tax[0].amount if if_tax else 0
                    svat += item.price_subtotal * ((tax) / 100)
                line.svat = svat
            else:
                line.svat = line.amount_tax

    @api.onchange('partner_id')
    def odoo_onchange_partner_id(self):
        """calling the order line function to compute"""
        self.order_line._compute_tax_id()


class InheritSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_tax_id(self):
        for line in self:
            """overding core function"""
            fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(lambda r: not line.company_id or r.company_id == line.company_id)
            if line.order_id.partner_id:
                if line.order_id.partner_id.vat_type in ['non_vat', 'vat']:
                    taxes = taxes.filtered(lambda x: x.vat_type == 'vat')
                else:
                    taxes = taxes.filtered(lambda x: x.vat_type == 's_vat')
            line.tax_id = fpos.map_tax(taxes, line.product_id, line.order_id.partner_shipping_id) if fpos else taxes


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    svat = fields.Float(string="SVAT Amount", compute='get_svat_value')
    vat_type = fields.Selection([('non_vat', 'Non VAT'), ('s_vat', 'SVAT'), ('vat', 'VAT')], string="VAT Type", default='non_vat', related='partner_id.vat_type')

    @api.depends('amount_untaxed')
    def get_svat_value(self):
        """get svat amount calculation"""
        for line in self:
            if line.partner_id.vat_type == 's_vat':
                svat = 0
                for item in line.invoice_line_ids:
                    if_tax = item.tax_ids
                    tax = if_tax[0].amount if if_tax else 0
                    svat += item.price_subtotal * ((tax)/ 100)
                line.svat = svat
            else:
                line.svat = line.amount_tax

    @api.onchange('partner_id')
    def odoo_onchange_partner_id(self):
        """calling the order line function to compute"""
        for line in self.invoice_line_ids:
            line._onchange_product_id()


class InheritAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_computed_taxes(self):
        self.ensure_one()
        """overding core function"""
        if self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            if self.product_id.taxes_id:
                tax_ids = self.product_id.taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
                if self.move_id.partner_id:
                    if self.move_id.partner_id.vat_type in ['non_vat', 'vat']:
                        tax_ids = tax_ids.filtered(lambda x: x.vat_type == 'vat')
                    else:
                        tax_ids = tax_ids.filtered(lambda x: x.vat_type == 's_vat')
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids
            else:
                tax_ids = self.env['account.tax']
            if not tax_ids and not self.exclude_from_invoice_tab:
                tax_ids = self.move_id.company_id.account_sale_tax_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            if self.product_id.supplier_taxes_id:
                tax_ids = self.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
                if self.move_id.partner_id:
                    if self.move_id.partner_id.vat_type in ['non_vat', 'vat']:
                        tax_ids = tax_ids.filtered(lambda x: x.vat_type == 'vat')
                    else:
                        tax_ids = tax_ids.filtered(lambda x: x.vat_type == 's_vat')
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids
            else:
                tax_ids = self.env['account.tax']
            if not tax_ids and not self.exclude_from_invoice_tab:
                tax_ids = self.move_id.company_id.account_purchase_tax_id
        else:
            # Miscellaneous operation.
            tax_ids = self.account_id.tax_ids

        if self.company_id and tax_ids:
            tax_ids = tax_ids.filtered(lambda tax: tax.company_id == self.company_id)

        return tax_ids