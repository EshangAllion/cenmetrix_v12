from odoo import fields, api, models


class InheritResPartner(models.Model):
    _inherit = 'res.partner'

    latitude = fields.Char(string="Latitude")
    longitude = fields.Char(string="Longitude")