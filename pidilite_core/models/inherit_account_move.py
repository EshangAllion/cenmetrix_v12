from odoo import fields, models, api
import datetime


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    print_status = fields.Selection([('original', 'Original'), ('reprint', 'Reprint')], string="Print Status")
    print_count = fields.Integer(string="Print Count", default=0)
    print_date = fields.Date(string="Print Date")

    def download_new_invoice(self):
        return_obj = self.env.ref('pidilite_core.new_invoice_report_action').report_action(self)
        if self.print_count == 0:
            self.write({
                'print_count': self.print_count + 1,
                'print_status': 'original'
            })
        else:
            self.write({
                'print_count': self.print_count + 1,
                'print_status': 'reprint'
            })
        self.write({
            'print_date': datetime.datetime.now().date()
        })
        return return_obj