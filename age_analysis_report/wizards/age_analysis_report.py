from odoo import fields, models, api
from datetime import datetime, date, time, timedelta
import xlsxwriter
import base64
from odoo.tools import misc
import os
import math


class AgeAnalysisReport(models.TransientModel):
    _name = 'age.analysis.report'

    from_date = fields.Date(string="From Invoice Date")
    to_date = fields.Date(string="To Invoice Date")
    partner_id = fields.Many2one('res.partner', string="Customer")
    user_id = fields.Many2one('res.users', string="Sales Person")
    report_file = fields.Binary('File', readonly=True)
    report_name = fields.Text(string='File Name')
    is_printed = fields.Boolean('Printed', default=False)

    def export_attendance_xlsx(self):
        """Function which is called when the Print button is clicked, here all the search parameters are added according
        to the fields filled by user to the domain list, and also grouped according to the sales rep and sent to
        the print_xlsx_report_group_by function with the domain list and group by. Then the report is converted to the
        binary and sent to the view"""

        # appending domain according to the user
        domain = []
        date_to = None
        if self.from_date:
            domain.append(('invoice_date', '>=', self.from_date))
        if self.to_date:
            date_to = self.to_date
            domain.append(('invoice_date', '<=', date_to))
        else:
            date_to = datetime.today().date()
            domain.append(('invoice_date', '<=', date_to))
        domain.append(('type', '=', 'out_invoice'))
        domain.append(('state', '=', 'posted'))
        domain.append(('overdue_amount', '>', 0))
        # domain.append(('state', '=', 'open'))

        # passing domain and group_by value to the print_xlsx_report
        file_name = self.print_xlsx_report(domain, date_to)

        # converting the report to binary
        report_data = open(file_name, 'rb+')
        file = report_data.read()
        output = base64.encodestring(file)
        cr, uid, context, user = self.env.args
        context_dictionary = dict(context)
        context_dictionary.update({'report_file': output})
        context_dictionary.update({'file': file_name})
        self.env.args = cr, uid, misc.frozendict(context)
        # setting the values to the fields
        self.report_name = file_name
        self.report_file = context_dictionary['report_file']
        self.is_printed = True

        # creating dictionary to pass to the view
        result = {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'age.analysis.report',
            'target': 'new',
            'context': context_dictionary,
            'res_id': self.id
        }
        # os.remove(file_name) TodO
        # returning dictionary to the voew
        return result

    def get_invoice_payment(self, invoice_id):
        """Calculating Real outstanding by excluding all draft cheque payments"""
        payments = self.env['account.payment'].search(
            [('invoice_ids', 'in', invoice_id.id), ('state', '=', 'posted')])
        total_payment = 0
        if payments:
            for item in payments:
                total_payment += item.amount

        if total_payment > invoice_id.amount_total:
            return total_payment - invoice_id.amount_total
        else:
            return 0

    def get_return_check_payment(self, return_check):
        """Calculating Real outstanding by excluding all draft cheque payments"""
        total_payment = 0
        for payment in return_check.bulk_payment_ids:
            if payment.state in ['collected', 'realized']:
                total_payment += payment.lines_total_amount
        if total_payment > return_check.amount:
            return total_payment - return_check.amount
        else:
            return 0

    def print_xlsx_report(self, domain, date_to):
        """Here the report is created, report name, report data, report layout is created here."""
        # creating file_name
        file_name = 'Age Analysis Report' + '.xlsx'

        # craeting a workbook and a worksheet
        workbook = xlsxwriter.Workbook(file_name)
        worksheet = workbook.add_worksheet()
        worksheet.set_landscape()

        # Layouts and styles for the report
        border = workbook.add_format({'border': 1})
        bold = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 12})
        font_left = workbook.add_format({'align': 'left', 'font_size': 10, 'bold': True,})
        font_center = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_size': 10})
        font_center_red = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_size': 10, 'font_color': 'red'})
        font_right = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_size': 10, 'num_format': '#,##0.00'})
        font_right_red = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_size': 10, 'num_format': '#,##0.00', 'font_color': 'red'})
        font_right_without = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_size': 10})
        font_right_without_red = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_size': 10, 'font_color': 'red'})
        font_right_bold = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'font_size': 10, 'bold': True, 'num_format': '#,##0.00'})
        font_bold_center = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_size': 10, 'border': 1,
                                                'bold': True})

        # setting up the border for the report
        worksheet.set_column('A:B', 9.5)
        worksheet.set_column('B:C', 9.5)
        worksheet.set_column('C:D', 20)
        worksheet.set_column('D:F', 13)
        worksheet.set_column('F:G', 25)
        worksheet.set_column('G:K', 13)
        worksheet.set_column('K:L', 16)
        worksheet.set_column('L:N', 13)
        worksheet.set_column('O:P', 22)
        worksheet.set_row(0, 20)

        # Report main heading
        if self.from_date and date_to:
            worksheet.merge_range('A1:M1', 'AGE ANALYSIS REPORT FROM ' + str(self.from_date) + "TO" + str(date_to), bold)
        else:
            worksheet.merge_range('A1:M1', 'AGE ANALYSIS REPORT AS AT ' + str(date_to), bold)

        # initiating rows and columns
        row = 2
        col = 0

        invoices = self.env['account.move'].search(domain)

        # report headings
        worksheet.merge_range(row, col, row, col + 1, "INVOICE DATE", font_bold_center)
        worksheet.write(row, col + 2, "INVOICE NO", font_bold_center)
        worksheet.write(row, col + 3, "NO. OF DAYS", font_bold_center)
        worksheet.write(row, col + 4, "TOTAL", font_bold_center)
        worksheet.write(row, col + 5, "OUTSTANDING AMOUNT", font_bold_center)
        worksheet.write(row, col + 6, "0-30", font_bold_center)
        worksheet.write(row, col + 7, "31-60", font_bold_center)
        worksheet.write(row, col + 8, "61-90", font_bold_center)
        worksheet.write(row, col + 9, "OVER 90", font_bold_center)
        worksheet.write(row, col + 10, "OVER PAYMENT", font_bold_center)
        worksheet.write(row, col + 11, "CHEQUE IN", font_bold_center)
        worksheet.write(row, col + 12, "BALANCE", font_bold_center)

        worksheet.freeze_panes(4, 13)

        row += 2
        # grouped according to rep

        users = self.env['res.users'].search([])
        if self.user_id:
            users = self.env['res.users'].search([('id', '=', self.user_id.id)])
        for user in users:
            # Getting Invoice age according to the selection
            worksheet.merge_range(row, col, row, col + 13, str(user.name).upper(), font_left)
            row += 1
            total_30 = total_60 = total_90 = total_over_90 = total_residual = total_outstanding = total_check_in = total_over_payment = 0
            customers = self.env['res.partner'].search([('user_id', '=', user.id)])
            if self.partner_id:
                customers = self.env['res.partner'].search([('user_id', '=', user.id), ('id', '=', self.partner_id.id)])
            for customer in customers:
                if invoices.filtered(lambda record: record.user_id.id == user.id and record.partner_id.id == customer.id) or self.env['returned.checks'].search([('partner_id', '=', customer.id), ('state', '=', 'open')]):
                    worksheet.merge_range(row, col + 1, row, col + 11, str(customer.name).upper(), font_left)
                    row += 1
                    users_invoices = invoices.filtered(lambda record: record.user_id.id == user.id and record.partner_id.id == customer.id)
                    total_cust_30 = total_cust_60 = total_cust_90 = total_cust_over_90 = total_cust_residual = total_cust_outstanding = total_cust_check_in = total_cust_over_payment = 0
                    for invoice in users_invoices:
                        date_gap = date_to - invoice.invoice_date
                        worksheet.write(row, col + 1, str(invoice.invoice_date), font_center)
                        worksheet.write(row, col + 2, invoice.name, font_center)
                        worksheet.write(row, col + 3, date_gap.days, font_right_without)
                        worksheet.write(row, col + 4, invoice.amount_total, font_right)
                        worksheet.write(row, col + 5, invoice.overdue_amount, font_right)
                        total_cust_outstanding += invoice.overdue_amount
                        if 0 <= date_gap.days <= 30:
                            total_cust_30 += invoice.amount_residual
                            worksheet.write(row, col + 6, invoice.amount_residual, font_right)
                        else:
                            worksheet.write(row, col + 6, 0.0, font_right)
                        if 31 <= date_gap.days <= 60:
                            total_cust_60 += invoice.amount_residual
                            worksheet.write(row, col + 7, invoice.amount_residual, font_right)
                        else:
                            worksheet.write(row, col + 7, 0.0, font_right)
                        if 61 <= date_gap.days <= 90:
                            total_cust_90 += invoice.amount_residual
                            worksheet.write(row, col + 8, invoice.amount_residual, font_right)
                        else:
                            worksheet.write(row, col + 8, 0.0, font_right)
                        if date_gap.days >= 91:
                            total_cust_over_90 += invoice.amount_residual
                            worksheet.write(row, col + 9, invoice.amount_residual, font_right)
                        else:
                            worksheet.write(row, col + 9, 0, font_right)
                        worksheet.write(row, col + 10, self.get_invoice_payment(invoice), font_right)
                        worksheet.write(row, col + 11, invoice.overdue_amount - invoice.amount_residual, font_right)
                        worksheet.write(row, col + 12, invoice.amount_residual, font_right)
                        total_cust_check_in += invoice.overdue_amount - invoice.amount_residual
                        total_cust_residual += invoice.amount_residual
                        total_cust_over_payment += self.get_invoice_payment(invoice)
                        worksheet.write(row, col + 13, "", font_right)
                        row += 1

                    for return_check in self.env['returned.checks'].search([('partner_id', '=', customer.id), ('state', '=', 'open')]):
                        date_gap = date_to - return_check.date
                        worksheet.write(row, col + 1, str(return_check.date), font_center_red)
                        worksheet.write(row, col + 2, return_check.name, font_center_red)
                        worksheet.write(row, col + 3, date_gap.days, font_right_without_red)
                        worksheet.write(row, col + 4, return_check.amount, font_right_red)
                        worksheet.write(row, col + 5, return_check.overdue_amount, font_right_red)
                        total_cust_outstanding += return_check.overdue_amount
                        residual = return_check.amount - return_check.paid_amount
                        if 0 <= date_gap.days <= 30:
                            total_cust_30 += residual
                            worksheet.write(row, col + 6, residual, font_right_red)
                        else:
                            worksheet.write(row, col + 6, 0.0, font_right_red)
                        if 31 <= date_gap.days <= 60:
                            total_cust_60 += residual
                            worksheet.write(row, col + 7, residual, font_right_red)
                        else:
                            worksheet.write(row, col + 7, 0.0, font_right_red)
                        if 61 <= date_gap.days <= 90:
                            total_cust_90 += residual
                            worksheet.write(row, col + 8, residual, font_right_red)
                        else:
                            worksheet.write(row, col + 8, 0.0, font_right_red)
                        if date_gap.days >= 91:
                            total_cust_over_90 += residual
                            worksheet.write(row, col + 9, residual, font_right_red)
                        else:
                            worksheet.write(row, col + 9, 0, font_right_red)
                        worksheet.write(row, col + 10, self.get_return_check_payment(return_check), font_right_red)
                        worksheet.write(row, col + 11, return_check.overdue_amount - residual, font_right_red)
                        worksheet.write(row, col + 12, residual, font_right_red)
                        total_cust_check_in += return_check.overdue_amount - residual
                        total_cust_residual += residual
                        total_cust_over_payment += self.get_return_check_payment(return_check)
                        worksheet.write(row, col + 13, "", font_right_red)
                        row += 1
                    # final line of each rep's total sales
                    worksheet.write(row, col + 5, total_cust_outstanding, font_right_bold)
                    worksheet.write(row, col + 6, total_cust_30, font_right_bold)
                    worksheet.write(row, col + 7, total_cust_60, font_right_bold)
                    worksheet.write(row, col + 8, total_cust_90, font_right_bold)
                    worksheet.write(row, col + 9, total_cust_over_90, font_right_bold)
                    worksheet.write(row, col + 10, total_cust_over_payment, font_right_bold)
                    worksheet.write(row, col + 11, total_cust_check_in, font_right_bold)
                    worksheet.write(row, col + 12, total_cust_residual, font_right_bold)
                    total_outstanding += total_cust_outstanding
                    total_30 += total_cust_30
                    total_60 += total_cust_60
                    total_90 += total_cust_90
                    total_over_90 += total_cust_over_90
                    total_check_in += total_cust_check_in
                    total_residual += total_cust_residual
                    row += 2
            worksheet.write(row, col + 5, total_outstanding, font_right_bold)
            worksheet.write(row, col + 6, total_30, font_right_bold)
            worksheet.write(row, col + 7, total_60, font_right_bold)
            worksheet.write(row, col + 8, total_90, font_right_bold)
            worksheet.write(row, col + 9, total_over_90, font_right_bold)
            worksheet.write(row, col + 10, total_over_payment, font_right_bold)
            worksheet.write(row, col + 11, total_check_in, font_right_bold)
            worksheet.write(row, col + 12, total_residual, font_right_bold)
            row += 2
        # Closing the workbook
        workbook.close()
        return file_name

    def action_back(self):
        """Back Function is built here"""
        if self._context is None:
            self._context = {}
        self.is_printed = False
        # returning to the view before
        result = {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'age.analysis.report',
            'target': 'new',
        }
        return result

