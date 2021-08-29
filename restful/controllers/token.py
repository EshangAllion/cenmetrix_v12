# Part of odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
from datetime import datetime, timedelta
import werkzeug.wrappers

from odoo import http
from ..common import extract_arguments, invalid_response, valid_response
from odoo.http import request
from passlib.context import CryptContext
from calendar import monthrange
from collections import Counter

_logger = logging.getLogger(__name__)

expires_in = "restful.access_token_expires_in"


class AccessToken(http.Controller):
    """."""

    def __init__(self):

        self._token = request.env["api.access_token"]
        self._expires_in = request.env.ref(expires_in).sudo().value

    def get_product_ids(self, partner_id, user_obj):
        """Calculating frequency of bought items"""
        sale_order_ids = request.env['sale.order'].sudo().search([('partner_id', '=', partner_id)], order="id desc", limit=user_obj.frequency)
        product_ids_raw = [line.product_id.id for line in request.env['sale.order.line'].sudo().search([('order_id', '=', sale_order_ids.ids)])]
        product_ids_sorted = [item for items, c in Counter(product_ids_raw).most_common() for item in [items] * c]
        product_ids = list(dict.fromkeys(product_ids_sorted))
        return product_ids[:user_obj.no_of_products]

    @http.route("/api/auth/token", methods=["POST"], type="http", auth="none", csrf=False)
    def token(self, **post):
        """The token URL to be used for getting the access_token:

        Args:
            **post must contain login and password.
        Returns:

            returns https response code 404 if failed error message in the body in json format
            and status code 202 if successful with the access_token.
        Example:
           import requests

           headers = {'content-type': 'text/plain', 'charset':'utf-8'}

           data = {
               'login': 'admin',
               'password': 'admin',
               'db': 'galago.ng'
            }
           base_url = 'http://odoo.ng'
           eq = requests.post(
               '{}/api/auth/token'.format(base_url), data=data, headers=headers)
           content = json.loads(req.content.decode('utf-8'))
           headers.update(access-token=content.get('access_token'))
        """
        _token = request.env["api.access_token"]
        params = ["db", "login", "password"]
        params = {key: post.get(key) for key in params if post.get(key)}
        db, username, password = (
            params.get("db"),
            post.get("login"),
            post.get("password"),
        )
        _credentials_includes_in_body = all([db, username, password])
        if not _credentials_includes_in_body:
            # The request post body is empty the credetials maybe passed via the headers.
            headers = request.httprequest.headers
            db = headers.get("db")
            username = headers.get("login")
            password = headers.get("password")
            _credentials_includes_in_headers = all([db, username, password])
            if not _credentials_includes_in_headers:
                # Empty 'db' or 'username' or 'password:
                return invalid_response(
                    "missing error",
                    "either of the following are missing [db, username,password]",
                    403,
                )
        # Login in odoo database:
        try:
            request.session.authenticate(db, username, password)
        except Exception as e:
            # Invalid database:
            info = "The database name is not valid {}".format((e))
            error = "invalid_database"
            _logger.error(info)
            return invalid_response("wrong database name", error, 403)

        uid = request.session.uid
        # odoo login failed:
        if not uid:
            info = "authentication failed"
            error = "authentication failed"
            _logger.error(info)
            return invalid_response(401, error, info)

        # Generate tokens
        access_token = _token.find_one_or_create_token(user_id=uid, create=True)
        # Successful response:
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "uid": uid,
                    "user_context": request.session.get_context() if uid else {},
                    "company_id": request.env.user.company_id.id if uid else None,
                    "access_token": access_token,
                    "expires_in": self._expires_in,
                }
            ),
        )

    @http.route("/api/login", methods=["POST"], type="http", auth="public", csrf=False)
    def login(self, **post):
        """."""
        _token = request.env["api.access_token"]
        access_token = request.httprequest.headers.get("access_token")
        access_token = _token.search([("token", "=", access_token)])
        # checks access token
        if not access_token:
            info = "No access token was provided in request!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(error, info, 401)

        elif access_token:
            username = request.params['username']
            password = request.params['password']
            # checks required fields
            if not username or not password:
                info = "User Not Found !!"
                error = "error"
                _logger.error(info)
                return invalid_response(error, info, 400)
            # check if user exist
            user = request.env['res.users'].sudo().search_read(([('login', '=', username), ('password', '=', CryptContext(['pbkdf2_sha512']).encrypt(password))]))
            if not user:
                info = "Login Failed"
                error = "error"
                _logger.error(info)
                return invalid_response(error, info, 401)
            # return if user exist
            data = {
                "user": user,
                "mobile_messages": request.env['mobile.messages'].sudo().search_read([]),
            }
            return valid_response(data)

    @http.route("/api/dashboard", methods=["POST"], type="http", auth="public", csrf=False)
    def dashboard(self, **post):
        """Dashboard API"""
        _token = request.env["api.access_token"]
        access_token = request.httprequest.headers.get("access_token")
        access_token = _token.search([("token", "=", access_token)])
        today_date = datetime.now().date()
        month_start_date = str(today_date.replace(day=1)) + " 00:00:00"
        month_end_date = str(today_date.replace(day=monthrange(today_date.year, today_date.month)[1])) + " 23:59:59"
        sales_rep_id = request.params.get('sales_rep_id')
        month = today_date.strftime('%B')
        year = str(today_date.year)
        today_date = str(today_date)
        # checks access token
        if not access_token:
            info = "Access token not found!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(error, info, 401)
        # checks required fields
        if not sales_rep_id:
            info = "Required parameters not found"
            error = "required_parameters_not_found"
            _logger.error(info)
            return invalid_response(error, info, 400)
        sales_rep_id = int(request.params.get('sales_rep_id'))
        # return values
        monthly_sales = sum(monthly_sale.amount_total for monthly_sale in request.env['sale.order'].sudo().search([('user_id', '=', sales_rep_id), ('date_order', '>=', month_start_date), ('date_order', '<=', month_end_date), ('company_id', '=', 4)]))
        today_sales = sum(today_sale.amount_total for today_sale in request.env['sale.order'].sudo().search([('user_id', '=', sales_rep_id), ('company_id', '=', 4), ('date_order', '>=', today_date + " 00:00:00"), ('date_order', '<=', today_date + " 23:59:59")]))
        today_sales_count = request.env['sale.order'].sudo().search_count([('user_id', '=', sales_rep_id), ('company_id', '=', 4), ('date_order', '>=', today_date + " 00:00:00"), ('date_order', '<=', today_date + " 23:59:59")])
        scheduled_visits_count = request.env['customer.visits'].sudo().search_count([('visit_id.user_id', '=', sales_rep_id), ('visit_id.date', '=', today_date)])
        monthly_sales_count = request.env['sale.order'].sudo().search_count([('user_id', '=', sales_rep_id), ('date_order', '>=', month_start_date), ('date_order', '<=', month_end_date)])
        scheduled_visits = request.env['customer.visits'].sudo().search_read([('visit_id.user_id', '=', sales_rep_id), ('visit_id.date', '=', today_date)], order='sequence')
        monthly_allocation = request.env['monthly.visits.allocation'].sudo().search([('month', '=', str(month).lower()), ('year', '=', year), ('user_id', '=', sales_rep_id)])
        today_allocation = request.env['daily.visits.allocation'].sudo().search([('date', '=', today_date)])
        completed_visits_count = request.env['customer.visits'].sudo().search_count([('visit_id.user_id', '=', sales_rep_id), ('visit_id.date', '=', today_date), ('is_visited', '=', True)])
        data = {
            "monthly_target": request.env['res.users'].sudo().search([('id', '=', sales_rep_id), ('company_id', '=', 4)], limit=1).monthly_target,
            "products": request.env['product.product'].sudo().search_read([('company_id', '=', 4)], fields=['name', 'default_code', 'display_name']),
            "monthly_sales_total": monthly_sales,
            "today_sales_total": today_sales,
            "today_sales_count": today_sales_count,
            "scheduled_visits_count": scheduled_visits_count,
            "monthly_sales_count": monthly_sales_count,
            "visits_completed_count": completed_visits_count,
            "scheduled_visits": scheduled_visits,
            "today_allocation_id": today_allocation.id,
            "monthly_allocation_id": monthly_allocation.id
        }
        return valid_response(data)

    @http.route("/api/frequently_bought_list", methods=["POST"], type="http", auth="public", csrf=False)
    def frequently_bought_list(self, **post):
        """Frequently bought products"""
        _token = request.env["api.access_token"]
        access_token = request.httprequest.headers.get("access_token")
        access_token = _token.search([("token", "=", access_token)])
        partner_id = request.params.get('customer_id')
        user_id = request.params.get('sales_rep_id')
        # checks access token
        if not access_token:
            info = "Access token not found!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(error, info, 401)
            # checks required fields
        if not partner_id or not user_id:
            info = "Required parameters not found"
            error = "required_parameters_not_found"
            _logger.error(info)
            return invalid_response(error, info, 400)
        partner_id = int(request.params.get('customer_id'))
        user_id = int(request.params.get('sales_rep_id'))
        user_obj = request.env['res.users'].sudo().browse(user_id)
        products_ids = self.get_product_ids(partner_id, user_obj)
        data = {
            "products": request.env['product.product'].sudo().search_read([('id', 'in', products_ids), ('company_id', '=', 4)]),
        }
        return valid_response(data)

    @http.route("/api/place_order", methods=["POST"], type="http", auth="public", csrf=False)
    def place_order(self, **post):
        """Placing sale Order"""
        _token = request.env["api.access_token"]
        access_token = request.httprequest.headers.get("access_token")
        access_token = _token.search([("token", "=", access_token)])
        partner_id = request.params.get('customer_id')
        user_id = request.params.get('sales_rep_id')
        visit_id = request.params.get('visit_id')
        allocation_id = request.params.get('allocation_id')
        daily_visit_id = request.params.get('daily_allocation_id')
        order_line = request.params.get('order_line')
        if not access_token:
            info = "Access token not found!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(error, info, 401)
        if not partner_id or not user_id or not order_line:
            info = "Required parameters not found"
            error = "required_parameters_not_found"
            _logger.error(info)
            return invalid_response(error, info, 400)
        partner_id = int(request.params.get('customer_id'))
        user_id = int(request.params.get('sales_rep_id'))
        try:
            # creating sale order
            if not allocation_id:
                allocation = request.env['monthly.visits.allocation'].sudo().create({
                    "month": (datetime.now().date().strftime('%B')).lower(),
                    "year": str(datetime.now().year),
                    "user_id": user_id
                })
                allocation_id = allocation.id
            if not daily_visit_id:
                daily_visit = request.env['daily.visits.allocation'].sudo().create({
                    "allocation_id": allocation_id,
                    "user_id": user_id,
                    "date": datetime.now().date()
                })
                daily_visit_id = daily_visit.id
            if not visit_id:
                visit = request.env['customer.visits'].sudo().create({
                    "visit_id": daily_visit_id,
                    "sequence": 999,
                    "partner_id": partner_id,
                    "is_visited": True
                })
                visit_id = visit.id

            sale_order = request.env['sale.order'].sudo().create({
                'partner_id': partner_id,
                'date_order': datetime.now() - timedelta(hours=5, minutes=30),
                'user_id': user_id,
                'visit_id': visit_id,
                'company_id': 4
            })
            for line in json.loads(order_line):
                line['order_id'] = sale_order.id
                request.env['sale.order.line'].sudo().create(line)
            request.env['customer.visits'].sudo().browse(visit_id).order_placed()
            data = {
                'sale_order_id': sale_order.name
            }
            return valid_response(data)
        except Exception as e:
            info = e
            _logger.error(info)
            return invalid_response("server_error", info, 500)

    @http.route("/api/order_details", methods=["POST"], type="http", auth="public", csrf=False)
    def order_details(self, **post):
        """Order Details API"""
        _token = request.env["api.access_token"]
        access_token = request.httprequest.headers.get("access_token")
        access_token = _token.search([("token", "=", access_token)])
        partner_id = request.params.get('customer_id')
        user_id = request.params.get('sales_rep_id')
        if not access_token:
            info = "Access token not found!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(error, info, 401)
        if not partner_id or not user_id:
            info = "Required parameters not found"
            error = "required_parameters_not_found"
            _logger.error(info)
            return invalid_response(error, info, 400)
        partner_id = int(request.params.get('customer_id'))
        user_id = int(request.params.get('sales_rep_id'))
        customer_obj = request.env['res.partner'].sudo().search_read([('id', '=', partner_id)])
        customer_obj[0]['order_details'] = request.env['sale.order'].sudo().search_read([('partner_id', '=', partner_id), ('user_id', '=', user_id), ('company_id', '=', 4)], limit=10, order='id desc')
        customer_obj[0]['returned_checks_total'] = sum(return_check.overdue_amount for return_check in request.env['returned.checks'].sudo().search([('overdue_amount', '>', 0), ('partner_id', '=', partner_id), ('company_id', '=', 4)]))
        customer_obj[0]['sales_done_total'] = sum(order.amount_total for order in request.env['sale.order'].sudo().search([('partner_id', '=', partner_id), ('user_id', '=', user_id), ('state', '=', 'sale'), ('company_id', '=', 4)]))

        for item in customer_obj[0]['order_details']:
            item['order_line_details'] = request.env['sale.order.line'].sudo().search_read([('order_id', '=', item['id'])])
        data = {
            'customer': customer_obj
        }
        return valid_response(data)

    @http.route("/api/today_sales", methods=["POST"], type="http", auth="public", csrf=False)
    def today_sales(self, **post):
        """Today Sales Details API"""
        _token = request.env["api.access_token"]
        access_token = request.httprequest.headers.get("access_token")
        access_token = _token.search([("token", "=", access_token)])
        user_id = request.params.get('sales_rep_id')
        today_date = datetime.now().date()
        today_date = str(today_date)
        if not access_token:
            info = "Access token not found!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(error, info, 401)
        if not user_id:
            info = "Required parameters not found"
            error = "required_parameters_not_found"
            _logger.error(info)
            return invalid_response(error, info, 400)
        user_id = int(request.params.get('sales_rep_id'))
        sale_orders = request.env['sale.order'].sudo().search_read([('user_id', '=', user_id), ('date_order', '>=', today_date + " 00:00:00"), ('date_order', '<=', today_date + " 23:59:59"), ('company_id', '=', 4)], order='id desc')
        for item in sale_orders:
            item['order_line_details'] = request.env['sale.order.line'].sudo().search_read(
                [('order_id', '=', item['id'])])
            item['customer_details'] = request.env['res.partner'].sudo().search_read(
                [('id', '=', item['partner_id'][0]), ('company_id', '=', 4)])
        data = {
            'today_sales': sale_orders
        }
        return valid_response(data)

    @http.route("/api/upload_documents", methods=["POST"], type="http", auth="public", csrf=False)
    def upload_documents(self, **post):
        """Placing sale Order"""
        _token = request.env["api.access_token"]
        access_token = request.httprequest.headers.get("access_token")
        access_token = _token.search([("token", "=", access_token)])
        partner_id = request.params.get('customer_id')
        user_id = request.params.get('sales_rep_id')
        visit_id = request.params.get('visit_id')
        allocation_id = request.params.get('allocation_id')
        daily_visit_id = request.params.get('daily_allocation_id')
        documents = request.params.get('documents')
        comments = request.params.get('comments')
        if not access_token:
            info = "Access token not found!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(error, info, 401)
        if not partner_id or not user_id or not documents:
            info = "Required parameters not found"
            error = "required_parameters_not_found"
            _logger.error(info)
            return invalid_response(error, info, 400)
        partner_id = int(request.params.get('customer_id'))
        user_id = int(request.params.get('sales_rep_id'))
        try:
            # creating sale order
            if not allocation_id:
                allocation = request.env['monthly.visits.allocation'].sudo().create({
                    "month": (datetime.now().date().strftime('%B')).lower(),
                    "year": str(datetime.now().year),
                    "user_id": user_id
                })
                allocation_id = allocation.id
            if not daily_visit_id:
                daily_visit = request.env['daily.visits.allocation'].sudo().create({
                    "allocation_id": allocation_id,
                    "user_id": user_id,
                    "date": datetime.now().date()
                })
                daily_visit_id = daily_visit.id
            if not visit_id:
                visit = request.env['customer.visits'].sudo().create({
                    "visit_id": daily_visit_id,
                    "sequence": 999,
                    "partner_id": partner_id,
                    "is_visited": True
                })
                visit_id = visit.id

            for document in json.loads(documents):
                request.env['customer.visits'].sudo().browse(int(visit_id)).add_image(document)
            if comments:
                request.env['customer.visits'].sudo().browse(int(visit_id)).add_comment(comments)
            data = {
                "status": "Success"
            }
            return valid_response(data)
        except Exception as e:
            info = e
            _logger.error(info)
            return invalid_response("server_error", info, 500)

    @http.route("/api/add_route_plan", methods=["POST"], type="http", auth="public", csrf=False)
    def add_route_plan(self, **post):
        """Placing sale Order"""
        _token = request.env["api.access_token"]
        access_token = request.httprequest.headers.get("access_token")
        access_token = _token.search([("token", "=", access_token)])
        partner_id = request.params.get('customer_id')
        user_id = request.params.get('sales_rep_id')
        date = request.params.get('date')
        order_line = request.params.get('order_line')
        if not access_token:
            info = "Access token not found!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(error, info, 401)
        if not partner_id or not user_id or not date:
            info = "Required parameters not found"
            error = "required_parameters_not_found"
            _logger.error(info)
            return invalid_response(error, info, 400)
        partner_id = int(request.params.get('customer_id'))
        user_id = int(request.params.get('sales_rep_id'))
        date = datetime.strptime(date, "%Y-%m-%d")
        try:
            # creating sale order
            allocation_id = request.env['monthly.visits.allocation'].sudo().search([('month', '=', date.strftime('%B').lower()), ('year', '=', str(date.year)), ('user_id', '=', user_id)], limit=1).id
            daily_visit_id = request.env['daily.visits.allocation'].sudo().search([('date', '=', str(date)), ('user_id', '=', user_id)], limit=1).id
            if not allocation_id:
                allocation = request.env['monthly.visits.allocation'].sudo().create({
                    "month": date.strftime('%B').lower(),
                    "year": str(date.year),
                    "user_id": user_id
                })
                allocation_id = allocation.id
            if not daily_visit_id:
                daily_visit = request.env['daily.visits.allocation'].sudo().create({
                    "allocation_id": allocation_id,
                    "user_id": user_id,
                    "date": str(date)
                })
                daily_visit_id = daily_visit.id

            visit_id = request.env['customer.visits'].sudo().search([('partner_id', '=', partner_id), ('user_id', '=', user_id), ('visit_id', '=', daily_visit_id)], limit=1).id
            if not visit_id:
                request.env['customer.visits'].sudo().create({
                    "visit_id": daily_visit_id,
                    "sequence": 999,
                    "partner_id": partner_id,
                    "is_visited": False
                })

                data = {
                    "status": "Success"
                }
            else:
                data = {
                    "status": "already_exist"
                }
            return valid_response(data)
        except Exception as e:
            info = e
            _logger.error(info)
            return invalid_response("server_error", info, 500)

    @http.route("/api/place_invoices", methods=["POST"], type="http", auth="public", csrf=False)
    def place_invoices(self, **post):
        """Placing sale Order"""
        _token = request.env["api.access_token"]
        access_token = request.httprequest.headers.get("access_token")
        access_token = _token.search([("token", "=", access_token)])
        invoices = request.params.get('invoices')
        if not access_token:
            info = "Access token not found!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(error, info, 401)
        if not invoices:
            info = "Required parameters not found"
            error = "required_parameters_not_found"
            _logger.error(info)
            return invalid_response(error, info, 400)
        try:
            invoice_success = []
            invoices = json.loads(invoices)
            is_post = json.loads(request.params.get('post'))
            for invoice in invoices:
                invoice_lines = invoice['InvoiceLineItems']
                invoice.pop('InvoiceLineItems')
                invoice['invoice_line_ids'] = []
                total = invoice['amount_total'] + invoice['discount_rate']
                discount = request.env['account.move'].get_discount_rate(total, invoice['discount_type'], invoice['discount_rate'])
                for line in invoice_lines:
                    line['discount'] = discount
                    invoice['invoice_line_ids'].append((0, 0, line))
                created_invoice = request.env['account.move'].sudo().create(invoice)
                created_invoice.date = invoice.get('date')
                created_invoice.invoice_date = invoice.get('date')
                invoice_success.append(created_invoice.ref)
                if is_post:
                    created_invoice.action_post()
            return valid_response({'success_invoices': invoice_success})
        except Exception as e:
            info = e
            _logger.error(info)
            return invalid_response("server_error", info, 500)

    @http.route("/api/place_payments", methods=["POST"], type="http", auth="public", csrf=False)
    def place_payments(self, **post):
        """Placing payment for invoice"""
        _token = request.env["api.access_token"]
        access_token = request.httprequest.headers.get("access_token")
        access_token = _token.search([("token", "=", access_token)])
        payments = request.params.get('payments')
        if not access_token:
            info = "Access token not found!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(error, info, 401)
        if not payments:
            info = "Required parameters not found"
            error = "required_parameters_not_found"
            _logger.error(info)
            return invalid_response(error, info, 400)
        try:
            payment_success = []
            payments = json.loads(payments)
            for payment in payments:
                payment_lines = payment['payment_lines']
                deposit = payment.get('deposit')
                realize = payment.get('realize')
                return_cheque = payment.get('return_cheque')
                bank_journal = payment.get('bank_journal')
                payment.pop('payment_lines')
                payment.pop('deposit')
                payment.pop('realize')
                if bank_journal:
                    payment.pop('bank_journal')
                payment.pop('return_cheque')
                payment['payment_lines'] = []
                if payment.get('receipt_no'):
                    exist_receipt = request.env['receipts.numbers'].sudo().search([('name', '=', payment.get('receipt_no'))])
                    if exist_receipt:
                        payment['receipt_no'] = exist_receipt.id
                    else:
                        receipt = request.env['receipts.numbers'].sudo().create({"name": payment.get('receipt_no')})
                        payment['receipt_no'] = receipt.id
                for line in payment_lines:
                    payment['payment_lines'].append((0, 0, line))
                created_payment = request.env['account.payment.register'].sudo().create(payment)
                bulk_payment = created_payment.sudo().create_payments_api()
                bulk_payment.bank_journal = bank_journal
                if deposit and bulk_payment.bank_journal:
                    bulk_payment.deposit_cheque()
                    if realize:
                        request.env['deposited.funds'].sudo().create({'journal_id': bulk_payment.bank_journal.id}).deposit_fund_api(bulk_payment)
                    elif return_cheque:
                        bulk_payment.sudo().return_check()
                payment_success.append(created_payment.receipt_no.name)
            return valid_response({'success_invoices': payment_success})
        except Exception as e:
            info = e
            _logger.error(info)
            return invalid_response("server_error", info, 500)

    @http.route("/api/get_payment_methods", methods=["POST"], type="http", auth="public", csrf=False)
    def get_payment_methods(self, **post):
        """get payment methods for api"""
        _token = request.env["api.access_token"]
        access_token = request.httprequest.headers.get("access_token")
        access_token = _token.search([("token", "=", access_token)])
        journal_id = request.params.get('journal_id')
        if not access_token:
            info = "Access token not found!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(error, info, 401)
        if not journal_id:
            info = "Required parameters not found"
            error = "required_parameters_not_found"
            _logger.error(info)
            return invalid_response(error, info, 400)
        try:
            journal_id = json.loads(journal_id)
            journal_obj = request.env['account.journal'].sudo().browse(journal_id)
            payment_methods = request.env['account.payment.method'].sudo().search_read([('id', 'in', journal_obj.inbound_payment_method_ids.ids)], fields=['id', 'name'])
            return valid_response({'payment_methods': payment_methods})
        except Exception as e:
            info = e
            _logger.error(info)
            return invalid_response("server_error", info, 500)

    @http.route("/api/place_sales_order", methods=["POST"], type="http", auth="public", csrf=False)
    def place_sales_order(self, **post):
        """Placing sale Order"""
        _token = request.env["api.access_token"]
        access_token = request.httprequest.headers.get("access_token")
        access_token = _token.search([("token", "=", access_token)])
        orders = request.params.get('orders')
        if not access_token:
            info = "Access token not found!"
            error = "no_access_token"
            _logger.error(info)
            return invalid_response(error, info, 401)
        if not orders:
            info = "Required parameters not found"
            error = "required_parameters_not_found"
            _logger.error(info)
            return invalid_response(error, info, 400)
        try:
            orders_success = []
            orders = json.loads(orders)
            is_post = json.loads(request.params.get('post'))
            for order in orders:
                order_lines = order['salesOrderLineItems']
                order.pop('salesOrderLineItems')
                order['order_line'] = []
                total = order['amount_total'] + order['discount_rate']
                discount = request.env['sale.order'].get_discount_rate(total, order['discount_type'],
                                                                         order['discount_rate'])
                for line in order_lines:
                    line['discount'] = discount
                    order['order_line'].append((0, 0, line))
                created_order = request.env['sale.order'].sudo().create(order)
                created_order.date = order.get('date')
                created_order.invoice_date = order.get('date')
                orders_success.append(created_order.name)
                # if is_post:
                #     created_order.action_post()
            return valid_response({'success_invoices': orders_success})
        except Exception as e:
            info = e
            _logger.error(info)
            return invalid_response("server_error", info, 500)