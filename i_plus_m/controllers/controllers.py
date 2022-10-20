# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import Response
import json

_logger = logging.getLogger(__name__)

class OdooAndroidSync(http.Controller):

    @http.route('/api/workorders/<user_id>', auth='user', methods=['GET'])
    def get_work_orders(self, user_id):
        try:
            employee_id = http.request.env['hr.employee'].search([('user_id', '=', int(user_id))]).id
            work_orders = http.request.env['im.work.order'].sudo() \
                .search_read([('employee_id', '=', int(employee_id))],['id', 'name', 'state'])
            return self.build_response(work_orders)
        except Exception as e:
            return self.build_response({'err': str(e)})
    
    @http.route('/api/workorder/<user_id>/<work_order_id>', auth='user', methods=['GET'])
    def get_work_order(self, user_id,work_order_id):
        try:
            employee_id = http.request.env['hr.employee'].search([('user_id', '=', int(user_id))]).id
            work_order = http.request.env['im.work.order'].sudo() \
                .search_read([('employee_id', '=', int(employee_id)),('id','=',int(work_order_id))], \
                    ['id', 'name', 'state'])
            return self.build_response(work_order)
        except Exception as e:
            return self.build_response({'err': str(e)})
    
    @http.route('/api/products/<name>', auth='user', methods=['GET'])
    def get_products(self, name):
        try:
            products = http.request.env['product.product'].sudo() \
                .search_read([('name', '=', str(name))], \
                    ['id', 'name'])
            return self.build_response(products)
        except Exception as e:
            return self.build_response({'err': str(e)})


    @http.route('/api/product/<id>', auth='user', methods=['GET'])
    def get_product(self, id):
        try:
            product = http.request.env['product.product'].sudo() \
                .search_read([('id', '=', int(id))], \
                    ['id', 'name'])
            return self.build_response(product)
        except Exception as e:
            return self.build_response({'err': str(e)})
    
    @http.route('/api/activities/<name>', auth='user', methods=['GET'])
    def get_activities(self, name):
        try:
            activities = http.request.env['im.activities'] \
                .search_read([('name', '=', str(name))], \
                    ['id', 'name'])
            return self.build_response(activities)
        except Exception as e:
            return self.build_response({'err': str(e)})

    @http.route('/api/activity/<id>', auth='user', methods=['GET'])
    def get_activities(self, id):
        try:
            activity = http.request.env['im.activities'] \
                .search_read([('id', '=', int(id))], \
                    ['id', 'name'])
            return self.build_response(activity)
        except Exception as e:
            return self.build_response({'err': str(e)})

    def build_response(self, entity):
        response = json.dumps(entity, ensure_ascii=False).encode('utf8')
        return Response(response, content_type='application/json;charset=utf-8', status=200)