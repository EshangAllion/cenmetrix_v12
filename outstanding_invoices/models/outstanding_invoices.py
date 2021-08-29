from odoo import models, api, fields, _
import json
from odoo.exceptions import UserError


class OutstandingInvoices(models.Model):
    _name = 'outstanding.invoices'
    _order = "partner_id"

    partner_id = fields.Many2one('res.partner', "Customer")
    invoice_id = fields.Many2one('account.move', "Invoice")
    user_id = fields.Many2one('res.users', "Sales Person")
    invoice_amount = fields.Float("Invoice Amount")
    invoice_residual = fields.Float("Invoice Residual")
    invoice_outstanding = fields.Float("Invoice Outstanding")
    invoice_date = fields.Date("Invoice Date")
    invoice_due_date = fields.Date("Invoice Due Date")
    invoice_collection_date = fields.Date("Invoice Collection Date")
    company_id = fields.Many2one('res.company', "Company")
    invoice_payments_widget = fields.Text("Payment Widget")
    invoice_payment_state = fields.Selection(selection=[('not_paid', 'Not Paid'), ('in_payment', 'In Payment'),
                                                        ('paid', 'Paid')],
                                            string='Payment')

    def run_scheduler(self):
        invoices = self.env['account.move'].search([('company_id.id', '=', '3'), ('state', 'in', ['posted']), ('type', '=', 'out_invoice'), ('overdue_amount', '>', 0)])
        for invoice in invoices:
            self.create({
                'partner_id': invoice.partner_id.id,
                'invoice_id': invoice.id,
                'user_id': invoice.user_id.id,
                'invoice_amount': invoice.amount_total,
                'invoice_residual': invoice.amount_residual,
                'invoice_outstanding': invoice.overdue_amount,
                'invoice_date': invoice.invoice_date,
                'invoice_due_date': invoice.invoice_date_due,
                'invoice_collection_date': invoice.collection_date,
                'company_id': invoice.company_id.id,
                'invoice_payments_widget': invoice.invoice_payments_widget,
                'invoice_payment_state': invoice.invoice_payment_state
            })


    def delete_records(self):
        tempory_invoices = self.search([('company_id.id', '=', '3'),('invoice_outstanding', '<=', 0)])
        if tempory_invoices:
            tempory_invoices.unlink()

class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_overdue_amount(self):
        """Calculating Real outstanding by excluding all draft cheque payments"""
        for invoice in self:
            amount = 0
            if invoice.type == 'out_invoice':
                payments_obj = self.env['account.payment'].search(
                    [('partner_id', '=', invoice.partner_id.id), ('state', '=', 'posted'),
                     ('bulk_payment_id.state', 'in', ['cheque_on_hand', 'deposited']),
                     ('payment_type_name', '=', 'Cheque')])
                payments = payments_obj.filtered(lambda x: invoice.id in x.reconciled_invoice_ids.ids)
                amount = invoice.amount_residual
                if payments:
                    total = sum(item.amount for item in payments)
                    amount += total
                else:
                    amount = invoice.amount_residual
            else:
                amount = 0
            check_exist = self.env['outstanding.invoices'].sudo().search([('invoice_id', '=', invoice.id)])
            vals = {
                'partner_id': invoice.partner_id.id,
                'invoice_id': invoice.id,
                'user_id': invoice.user_id.id,
                'invoice_amount': invoice.amount_total,
                'invoice_residual': invoice.amount_residual,
                'invoice_outstanding': amount,
                'invoice_date': invoice.invoice_date,
                'invoice_due_date': invoice.invoice_date_due,
                'invoice_collection_date': invoice.collection_date,
                'company_id': invoice.company_id.id,
                'invoice_payments_widget': invoice.invoice_payments_widget,
                'invoice_payment_state': invoice.invoice_payment_state
            }
            if check_exist:
                check_exist.write(vals)
            else:
                if invoice.state == 'posted' and invoice.type == 'out_invoice' and amount > 0:
                    check_exist.create(vals)
            invoice.overdue_amount = amount

    def button_draft(self):
        AccountMoveLine = self.env['account.move.line']
        excluded_move_ids = []

        if self._context.get('suspense_moves_mode'):
            excluded_move_ids = AccountMoveLine.search(AccountMoveLine._get_suspense_moves_domain() + [('move_id', 'in', self.ids)]).mapped('move_id').ids

        for move in self:
            if move in move.line_ids.mapped('full_reconcile_id.exchange_move_id'):
                raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id:
                raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
            if move.restrict_mode_hash_table and move.state == 'posted' and move.id not in excluded_move_ids:
                raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'draft'})


class InheritAccountBulkPayment(models.Model):
    _inherit = 'account.bulk.payment'

    @api.model
    def create(self, vals):
        return_obj = super(InheritAccountBulkPayment, self).create(vals)
        for line in return_obj.bulk_payment_lines:
            invoice_sync = self.env['account.move'].browse(line.invoice_id.id)
            line.invoice_id._compute_amount()
            line.invoice_id._compute_overdue_amount()
        return return_obj

    def write(self, vals):
        return_obj = super(InheritAccountBulkPayment, self).write(vals)
        for line in self.bulk_payment_lines:
            invoice_sync = self.env['account.move'].browse(line.invoice_id.id)
            line.invoice_id._compute_amount()
            line.invoice_id._compute_overdue_amount()
        return return_obj


class InheritAccountBulkPaymentLine(models.Model):
    _inherit = 'account.bulk.payment.line'

    @api.model
    def create(self, vals):
        return_obj = super(InheritAccountBulkPaymentLine, self).create(vals)
        invoice_sync = self.env['account.move'].browse(return_obj.invoice_id.id)
        return_obj.invoice_id._compute_amount()
        return_obj.invoice_id._compute_overdue_amount()
        return return_obj

    def write(self, vals):
        return_obj = super(InheritAccountBulkPaymentLine, self).write(vals)
        invoice_sync = self.env['account.move'].browse(self.invoice_id.id)
        self.invoice_id._compute_amount()
        self.invoice_id._compute_overdue_amount()
        return return_obj


class InheritAccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.depends('move_line_ids.matched_debit_ids', 'move_line_ids.matched_credit_ids')
    def _compute_reconciled_invoice_ids(self):
        """Inheriting core feature to calculate reconciled invoice"""
        for record in self:
            reconciled_moves = record.move_line_ids.mapped('matched_debit_ids.debit_move_id.move_id') \
                               + record.move_line_ids.mapped('matched_credit_ids.credit_move_id.move_id')
            record.reconciled_invoice_ids = reconciled_moves.filtered(lambda move: move.is_invoice())
            record.has_invoices = bool(record.reconciled_invoice_ids)
            record.reconciled_invoices_count = len(record.reconciled_invoice_ids)
            for invoice in record.reconciled_invoice_ids:
                invoice_sync = self.env['account.move'].browse(invoice.id)
                invoice._compute_amount()
                invoice._compute_overdue_amount()
            if record.reconciled_invoice_ids:
                for line in record.bulk_payment_id.bulk_payment_lines.filtered(
                        lambda x: x.invoice_id.id in record.reconciled_invoice_ids.ids):
                    amount = self.get_payment_of_invoice(
                        json.loads(line.invoice_id.invoice_payments_widget).get('content'), record)
                    line.write({
                        "amount": amount
                    })

    def write(self, vals):
        for invoice in self.reconciled_invoice_ids:
            invoice._compute_amount()
            invoice._compute_overdue_amount()
        return super(InheritAccountPayment, self).write(vals)

    def action_draft(self):
        ids = []
        for invoice in self.reconciled_invoice_ids:
            ids.append(invoice.id)
        moves = self.mapped('move_line_ids.move_id')
        moves.filtered(lambda move: move.state == 'posted').button_draft()
        moves.with_context(force_delete=True).unlink()
        self.write({'state': 'draft', 'invoice_ids': False})
        invoices = self.env['account.move'].browse(ids)
        invoices._compute_amount()
        invoices._compute_overdue_amount()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        return_obj = super(AccountMoveLine, self).reconcile(writeoff_acc_id=writeoff_acc_id, writeoff_journal_id=writeoff_journal_id)
        for line in self.filtered(lambda x:x.move_id.type == 'out_invoice'):
            line.move_id._compute_amount()
            line.move_id._compute_overdue_amount()
        return return_obj

    def remove_move_reconcile(self):
        """ Undo a reconciliation """
        ids = []
        records = (self.mapped('matched_debit_ids') + self.mapped('matched_credit_ids'))
        for record in records:
            if record.credit_move_id.move_id.type == 'out_invoice':
                ids.append(record.credit_move_id.move_id.id)
            if record.debit_move_id.move_id.type == 'out_invoice':
                ids.append(record.debit_move_id.move_id.id)
        (self.mapped('matched_debit_ids') + self.mapped('matched_credit_ids')).unlink()
        invoices = self.env['account.move'].browse(ids)
        invoices._compute_amount()
        invoices._compute_overdue_amount()



