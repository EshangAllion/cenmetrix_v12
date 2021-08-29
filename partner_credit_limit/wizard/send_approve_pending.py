from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SendApprovePending(models.TransientModel):
    _name = 'send.approve.pending'

    error_msg = fields.Text(readonly=True)

    def state_change(self):
        """This function is used to send this SO pending approval process"""
        so_id = self.env.context.get('active_id', False)  # get the active id of the current sale order
        if so_id:
            # search and get the sale order which the id is equal to active id
            so = self.env['sale.order'].search([('id', '=', so_id)])
            if so:
                so.write({'state': 'pending'})  # update state
