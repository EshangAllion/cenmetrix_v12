from odoo import models, fields, api


class InheritInvoice(models.Model):
    _inherit = 'account.move'

    collection_date = fields.Date("Collecting Date", track_visibility='onchange')


