from odoo import api, models, fields, _
from datetime import datetime, date


class SaleOrder(models.Model):
    _inherit = "sale.order"

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('pending', 'Pending Approval'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3,
        default='draft')

    def check_limit(self):
        """Check the credit limit of the customer and if the amount of the current
            sale order is greater than the credit limit it goes through a approval stage """
        invoice_sum = sum(invoice.amount_residual_signed for invoice in self.env['account.move'].search([('state', '=', 'posted'), ('partner_id', '=', self.partner_id.id), ('invoice_date_due', '<', datetime.today().date()), ('invoice_payment_state', '!=', 'paid'), ('type', '=', 'out_invoice')]))
        if not self.partner_id.over_credit:
            if self.partner_id.credit_limit < invoice_sum:
                exceed_amount = invoice_sum - self.partner_id.credit_limit
                msg = 'This customer has exceeded the given the credit limit.\nThe exceeded credit limit is ' + str(round(exceed_amount, 2))
                return {
                    'status': False,
                    'msg': msg
                }
            else:
                if self.partner_id.credit_limit < (round(invoice_sum, 2) + self.amount_total):
                    exceed_amount = (invoice_sum + self.amount_total) - self.partner_id.credit_limit
                    msg = 'This customer will exceeded the given credit limit due to the current sales order' \
                          '.\nThe exceeding credit limit will be ' + str(
                        round(exceed_amount, 2))
                    return {
                        'status': False,
                        'msg': msg
                    }
                else:
                    return {
                        'status': True
                    }
        return {
            'status': True
        }


    def action_confirm(self):
        """Return the relevant wizards according to the functions. (check_limit and check_payment_terms)"""
        val = self.check_limit()  # getting the check limit function to "val" variable
        if val['status'] == False:  # check return is false in check limit
            return {
                'type': 'ir.actions.act_window',
                'name': 'CREDIT LIMIT EXCEEDED',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'send.approve.pending',
                'view_id': self.env.ref('partner_credit_limit.send_approve_pending').id,
                'target': 'new',
                'context': {'default_error_msg': 'You can not confirm Sale '
                                                 'Order. \n' + val['msg']},  # making a dictionary to pass as context
            }

        else:
            value = self.check_payment_terms()  # getting the check_payment_terms function to "val" variable
            if value['status'] == False:  # check return is false in check payment terms and pop up wizard

                return {
                    'type': 'ir.actions.act_window',
                    'name': 'PAYMENT TERM EXCEEDED!',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'send.approve.payment.terms',
                    'view_id': self.env.ref('partner_credit_limit.send_approve_payment_terms').id,
                    'target': 'new',
                    'context': {'default_error_msg': 'You can not confirm this sale '
                                                     'order. \n' + 'The due date of the invoice ' + value['invoice'] + ' exceeded'}, # making a dictionary to pass as context
                }
            if value['status'] == True:
                return super(SaleOrder, self).action_confirm()  # getting the super class of the sale order action confirm to "res" variable

    def check_payment_terms(self):
        """Check the Payment term of the customer and whether
            the due date of previous invoices have exceeded
             it goes through a approval stage"""

        invoices = self.env['account.move'].search([('state', '=', 'posted'), ('partner_id', '=', self.partner_id.id), ('invoice_date_due', '<', datetime.today().date()), ('invoice_payment_state', '!=', 'paid'), ('type', '=', 'out_invoice')])
        #  getting customer's open state invoices on before today
        if invoices:
            return {
                'status': False,
                'msg': "",
                'invoice': invoices[0].name
            }

        return {
            'status': True
        }

    @api.constrains('amount_total')
    def check_amount(self):
        """Call check limit function for sale orders"""
        for order in self:
            order.check_limit()

    def approve_credit_limit(self):
        """This function will confirm the sales order through the approve button"""
        res = super(SaleOrder, self).action_confirm()  # getting the super class of the sale order action confirm to "res" variable
        for order in self:
            if order.sale_order_template_id and order.sale_order_template_id.mail_template_id:
                self.sale_order_template_id.mail_template_id.send_mail(order.id)
        return res