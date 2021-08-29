from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    collect_date = fields.Integer(related='payment_term_id.collecting_date')
    collection_date = fields.Date("Collecting Date", track_visibility='onchange')

    def action_confirm(self):
        """creates a collection date by adding collecting date from payment terms with confirmation date"""
        if self.partner_id:
            if self.date_order:
                self.collection_date = self.date_order.date() + timedelta(days=self.collect_date)
        return super(InheritSaleOrder, self).action_confirm()

    def _prepare_invoice(self):
        return_obj = super(InheritSaleOrder, self)._prepare_invoice()
        if return_obj:
            return_obj['collection_date'] = self.collection_date
        return return_obj