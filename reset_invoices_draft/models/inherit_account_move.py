from odoo import fields, models, api, _


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    def reset_to_draft_bulk_invoice(self):
        invoices = self.env['account.move'].browse(self.env.context.get('active_ids'))
        for invoice in invoices:
            invoice.button_draft()


class InheritAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def reset_update_due_date(self):
        invoices = self.env['account.move.line'].browse(self.env.context.get('active_ids'))
        for invoice in invoices:
            invoice.write({
                'date_maturity': invoice.date
            })



