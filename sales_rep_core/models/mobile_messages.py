from odoo import fields, api, models


class MobileMessages(models.Model):
    _name = 'mobile.messages'

    name = fields.Char("Name")

