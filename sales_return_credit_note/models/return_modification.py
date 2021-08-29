from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import ValidationError, UserError


class InheritStockReturnPickup(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        # TODO sle: the unreserve of the next moves could be less brutal
        for return_move in self.product_return_moves.mapped('move_id'):
            return_move.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._do_unreserve()

        # create new picking for returned products
        picking_type_id = self.picking_id.picking_type_id.return_picking_type_id.id or self.picking_id.picking_type_id.id
        new_picking = self.picking_id.copy({
            'move_lines': [],
            'picking_type_id': picking_type_id,
            'state': 'draft',
            'is_return': True,
            'origin': _("Return of %s") % self.picking_id.name,
            'location_id': self.picking_id.location_dest_id.id,
            'location_dest_id': self.location_id.id})
        new_picking.message_post_with_view('mail.message_origin_link',
                                           values={'self': new_picking, 'origin': self.picking_id},
                                           subtype_id=self.env.ref('mail.mt_note').id)
        returned_lines = 0
        for return_line in self.product_return_moves:
            if not return_line.move_id:
                raise UserError(_("You have manually created product lines, please delete them to proceed."))
            # TODO sle: float_is_zero?
            if return_line.quantity:
                returned_lines += 1
                vals = self._prepare_move_default_values(return_line, new_picking)
                r = return_line.move_id.copy(vals)
                vals = {}

                # +--------------------------------------------------------------------------------------------------------+
                # |       picking_pick     <--Move Orig--    picking_pack     --Move Dest-->   picking_ship
                # |              | returned_move_ids              ↑                                  | returned_move_ids
                # |              ↓                                | return_line.move_id              ↓
                # |       return pick(Add as dest)          return toLink                    return ship(Add as orig)
                # +--------------------------------------------------------------------------------------------------------+
                move_orig_to_link = return_line.move_id.move_dest_ids.mapped('returned_move_ids')
                # link to original move
                move_orig_to_link |= return_line.move_id
                # link to siblings of original move, if any
                move_orig_to_link |= return_line.move_id \
                    .mapped('move_dest_ids').filtered(lambda m: m.state not in ('cancel')) \
                    .mapped('move_orig_ids').filtered(lambda m: m.state not in ('cancel'))
                move_dest_to_link = return_line.move_id.move_orig_ids.mapped('returned_move_ids')
                # link to children of originally returned moves, if any. Note that the use of
                # 'return_line.move_id.move_orig_ids.returned_move_ids.move_orig_ids.move_dest_ids'
                # instead of 'return_line.move_id.move_orig_ids.move_dest_ids' prevents linking a
                # return directly to the destination moves of its parents. However, the return of
                # the return will be linked to the destination moves.
                move_dest_to_link |= return_line.move_id.move_orig_ids.mapped('returned_move_ids') \
                    .mapped('move_orig_ids').filtered(lambda m: m.state not in ('cancel')) \
                    .mapped('move_dest_ids').filtered(lambda m: m.state not in ('cancel'))
                vals['move_orig_ids'] = [(4, m.id) for m in move_orig_to_link]
                vals['move_dest_ids'] = [(4, m.id) for m in move_dest_to_link]
                r.write(vals)
        if not returned_lines:
            raise UserError(_("Please specify at least one non-zero quantity."))

        new_picking.action_confirm()
        new_picking.action_assign()
        return new_picking.id, picking_type_id


class ReturnModification(models.Model):
    _inherit = 'stock.picking'

    is_return = fields.Boolean("returned")

    def button_validate(self):
        self.ensure_one()
        if not self.move_lines and not self.move_line_ids:
            raise UserError(_('Please add some items to move.'))

        # Clean-up the context key at validation to avoid forcing the creation of immediate
        # transfers.
        ctx = dict(self.env.context)
        ctx.pop('default_immediate_transfer', None)
        self = self.with_context(ctx)

        # add user as a follower
        self.message_subscribe([self.env.user.partner_id.id])

        # If no lots when needed, raise error
        picking_type = self.picking_type_id
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        no_quantities_done = all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in self.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
        no_reserved_quantities = all(float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in self.move_line_ids)
        if no_reserved_quantities and no_quantities_done:
            raise UserError(_('You cannot validate a transfer if no quantites are reserved nor done. To force the transfer, switch in edit more and encode the done quantities.'))

        if picking_type.use_create_lots or picking_type.use_existing_lots:
            lines_to_check = self.move_line_ids
            if not no_quantities_done:
                lines_to_check = lines_to_check.filtered(
                    lambda line: float_compare(line.qty_done, 0,
                                               precision_rounding=line.product_uom_id.rounding)
                )

            for line in lines_to_check:
                product = line.product_id
                if product and product.tracking != 'none':
                    if not line.lot_name and not line.lot_id:
                        raise UserError(_('You need to supply a Lot/Serial number for product %s.') % product.display_name)

        # Propose to use the sms mechanism the first time a delivery
        # picking is validated. Whatever the user's decision (use it or not),
        # the method button_validate is called again (except if it's cancel),
        # so the checks are made twice in that case, but the flow is not broken
        sms_confirmation = self._check_sms_confirmation_popup()
        if sms_confirmation:
            return sms_confirmation

        if no_quantities_done:
            view = self.env.ref('stock.view_immediate_transfer')
            wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})
            return {
                'name': _('Immediate Transfer?'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'stock.immediate.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        if self._get_overprocessed_stock_moves() and not self._context.get('skip_overprocessed_check'):
            view = self.env.ref('stock.view_overprocessed_transfer')
            wiz = self.env['stock.overprocessed.transfer'].create({'picking_id': self.id})
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'stock.overprocessed.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        # Check backorder should check for other barcodes
        if self._check_backorder():
            return self.action_generate_backorder_wizard()
        self.action_done()
        if (self.is_return or self.picking_type_id.is_invoice_return) and self.picking_type_id.code == 'incoming':
            journal = self.env['account.journal'].sudo().search([('type', '=', 'sale'), ('company_id', '=', self.picking_type_id.company_id.id)], limit=1)
            invoice = {
                'partner_id': self.partner_id.id,
                'type': 'out_refund',
                'invoice_origin': self.name,
                'journal_id': journal.id,
                'ref': self.origin,
                'company_id': self.picking_type_id.company_id.id,
                'stock_picking': self.picking_type_id.id,
                'currency_id': self.company_id.currency_id,
                'invoice_line_ids': []
            }
            # creates a credit note with GRN values

            for line in self.move_ids_without_package: # loops product return lines
                invoice['invoice_line_ids'].append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.quantity_done,
                    'name': line.product_id.name,
                    'price_unit': line.product_id.list_price,
                    'account_id': journal.default_debit_account_id.id
                }))

            credit_note = self.env['account.move'].create(invoice)
            return {
                'name': _('Credit Note'),
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': credit_note.id,
                'type': 'ir.actions.act_window',
            }
        return


class ReturnModifications(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        pick_to_backorder = self.env['stock.picking']
        pick_to_do = self.env['stock.picking']
        for picking in self.pick_ids:
            # If still in draft => confirm and assign
            if picking.state == 'draft':
                picking.action_confirm()
                if picking.state != 'assigned':
                    picking.action_assign()
                    if picking.state != 'assigned':
                        raise UserError(_(
                            "Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
            for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty
            if picking._check_backorder():
                pick_to_backorder |= picking
                continue
            pick_to_do |= picking
        # Process every picking that do not require a backorder, then return a single backorder wizard for every other ones.
        if pick_to_do:
            pick_to_do.action_done()
            if pick_to_do.is_return and pick_to_do.picking_type_code == 'incoming':
                journal = self.env['account.journal'].sudo().search([('type', '=', 'sale')], limit=1)
                invoice = {
                    'partner_id': pick_to_do.partner_id.id,
                    'type': 'out_refund',
                    'invoice_origin': pick_to_do.name,
                    'journal_id': journal.id,
                    'ref': pick_to_do.origin,
                    'stock_picking': pick_to_do.id,
                    'invoice_line_ids': []
                }
                # creates a credit note with GRN values

                for line in pick_to_do.move_ids_without_package:  # loops product return lines
                    invoice['invoice_line_ids'].append((0, 0, {
                        'product_id': line.product_id.id,
                        'quantity': line.quantity_done,
                        'name': line.product_id.name,
                        'price_unit': line.product_id.list_price,
                        'account_id': journal.default_debit_account_id.id
                    }))
                credit_note = self.env['account.move'].create(invoice)
                return {
                    'name': _('Credit Note'),
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'res_id': credit_note.id,
                    'type': 'ir.actions.act_window',
                }
        if pick_to_backorder:
            return pick_to_backorder.action_generate_backorder_wizard()
        return False


class AccountInherit(models.Model):
    _inherit = 'account.move'

    stock_picking = fields.Many2one('stock.picking')


class InheritStockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_invoice_return = fields.Boolean("Sales Return")



