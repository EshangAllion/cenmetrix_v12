from odoo import fields, models, api


class MonthlyVisitAllocation(models.Model):
    _name = 'monthly.visits.allocation'

    name = fields.Char('Name', copy=False, default='New')
    month = fields.Selection([('january', 'January'),
                              ('february', 'February'),
                              ('march', 'March'),
                              ('april', 'April'),
                              ('may', 'May'),
                              ('june', 'June'),
                              ('july', 'July'),
                              ('august', 'August'),
                              ('september', 'September'),
                              ('october', 'October'),
                              ('november', 'November'),
                              ('december', 'December')], string="Month", copy=False)
    year = fields.Selection([('2020', '2020'),
                             ('2021', '2021'),
                             ('2022', '2022'),
                             ('2023', '2023'),
                             ('2024', '2024'),
                             ('2025', '2025')])
    user_id = fields.Many2one('res.users', 'Sales Person')
    daily_visits_allocation_ids = fields.One2many('daily.visits.allocation', 'allocation_id')

    _sql_constraints = [
        ('user_id_month_year_unique', 'unique(month,year,user_id)', "A record exist with same month, year and sales person")]

    @api.model
    def create(self, values):
        """Overiding the create function to change name"""
        return_obj = super(MonthlyVisitAllocation, self).create(values)
        return_obj.name = "%s's Monthly Allocation for %s" % (return_obj.user_id.name, str(return_obj.month).title())
        return return_obj


class DailyVisitAllocation(models.Model):
    _name = 'daily.visits.allocation'

    name = fields.Char('Name', copy=False, default='New')
    allocation_id = fields.Many2one('monthly.visits.allocation')
    user_id = fields.Many2one('res.users', 'Sales Person')
    date = fields.Date('Date', copy=False)
    customer_visits_ids = fields.One2many('customer.visits', 'visit_id')
    state_ids = fields.Many2many('res.country.state', string="Cities")

    _sql_constraints = [
        ('user_id_date_unique', 'unique(name,date)', "A record exist with same date and sales person")]

    @api.model
    def create(self, values):
        """Overiding the create function to change name"""
        return_obj = super(DailyVisitAllocation, self).create(values)
        return_obj.name = "%s's Allocation for %s" % (return_obj.user_id.name, str(return_obj.date))
        return return_obj

    @api.onchange('state_ids', 'user_id')
    def onchange_state_ids_user_id(self):
        """Onchange status_ids autofill visits"""
        if self.state_ids and self.allocation_id.user_id:
            customer_visits_ids = []
            partners = self.env['res.partner'].search([('state_id', 'in', self.state_ids.ids), ('user_id', '=', self.allocation_id.user_id.id)])
            for partner in partners:
                customer_visits_ids.append((0, 0, {
                    'partner_id': partner.id
                }))
            self.customer_visits_ids = [(5,)]
            self.customer_visits_ids = customer_visits_ids


class CustomerVisits(models.Model):
    _name = 'customer.visits'

    visit_id = fields.Many2one('daily.visits.allocation', ondelete='cascade')
    sequence = fields.Integer('Sequence')
    partner_id = fields.Many2one('res.partner')
    user_id = fields.Many2one('res.users', related='visit_id.user_id')
    is_visited = fields.Boolean('Visited')
    state_id = fields.Many2one('res.country.state', string="City", related="partner_id.state_id")
    state = fields.Selection([('order_placed', 'Order Placed'), ('only_visited', 'Visited Only'),
                              ('pending_visit', 'Visit Pending')], default='pending_visit')
    latitude = fields.Char(string="Latitude", related="partner_id.latitude", store=True)
    longitude = fields.Char(string="Longitude", related="partner_id.longitude", store=True)
    address = fields.Char(string="Address", related="partner_id.contact_address_complete", store=True)
    mobile = fields.Char(string="Mobile", related="partner_id.mobile", store=True)
    visit_image_ids = fields.One2many('customer.visit.image', 'visit_id', string="Visits Images", copy=True)
    comment_ids = fields.One2many('visit.comment', 'visit_id', string="Visit Comments", copy=True)

    def order_placed(self):
        """Order place function"""
        self.write({
            "is_visited": True,
            "state": 'order_placed'
        })

    def add_image(self, binary):
        self.visit_image_ids.create({
            'image': binary,
            'visit_id': self.id
        })
        self.write({
            "is_visited": True,
            "state": 'only_visited'
        })

    def add_comment(self, comment):
        self.comment_ids.create({
            'comment': comment,
            'visit_id': self.id
        })
        self.write({
            "is_visited": True,
            "state": 'only_visited'
        })


class CustomerVisitImages(models.Model):
    _name = 'customer.visit.image'

    name = fields.Char("Name")
    image = fields.Image(required=True)
    visit_id = fields.Many2one('customer.visits')


class VisitComments(models.Model):
    _name = 'visit.comment'

    comment = fields.Char("Name")
    visit_id = fields.Many2one('customer.visits')
