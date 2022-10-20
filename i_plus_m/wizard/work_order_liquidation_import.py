 # -*- coding: utf-8 -*-
from email.policy import default
from itertools import product
from locale import currency
from odoo import models, fields, api, _
from datetime import datetime,date
from odoo.exceptions import ValidationError
import xlrd
import xlwt
import base64
import logging
import re

_logger = logging.getLogger(__name__)
regex_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

class WorkOrderImport(models.TransientModel):
    _name = 'work.order.liquidation.import'
    _description = 'Work order import'
    excel_file = fields.Binary('Import file', attachment=True)
    file_name = fields.Char('Filename')
    msg_validation = fields.Text('', readonly="1")
    output_file = fields.Binary('', readonly=True)
    output_name = fields.Char('Output')
    count_output_file = fields.Integer('Error qty')
    contract_id = fields.Many2one('customer.contracts',string='Contract', required=True)

    def find_product(self, product_code):
        res = self.env['product.product'].search([('default_code', '=',product_code)])
        if not res:
            return False # empleado no registrado
        else:
            return res
    
    def find_serie(self, serie):
        res = self.env['stock.production.lot'].search([('name', '=',serie)])
        if not res:
            return False 
        else:
            return res
    
    def find_activity(self, activity_code):
        _logger.warning(activity_code)
        res = self.env['activities'].search([('code','=',activity_code), ('customer_contracts_id','=',self.contract_id.id)])
        _logger.warning("Len de res" + str(len(res)))
        if not res:
            return False 
        else:
            return res
    
    def validate_float(self,val):
        try:
            return float(val)
        except ValueError:
            return False
    
    def validate_int(self,val):
        try:
            return int(float(val))
        except ValueError:
            return False
    
    def _check_float(self, val=None):
        if type(val) is float:
            new_val = str(int(val))
        else:
            new_val = str(val)
        return new_val
    
    def import_work_orders(self):
        wb = xlrd.open_workbook(
            file_contents = base64.decodebytes(self.excel_file)
        )
        sheet = wb.sheet_by_index(0)
        sheet.cell_value(0, 0)
        a = 1
        product_count = 0
        activity_count = 0
        for i in range(sheet.nrows - 1):
            type = ''
            val = sheet.row_values(a)
            work_order = self.env['im.work.order'].search([('name','=',self._check_float(val[0]).strip()),('contract_id','=',self.contract_id.id)])
            if not work_order:
                raise ValidationError(_('Orden de trabajo %s de la fila %s no existe') % (self._check_float(val[0]).strip(), str(a)))
            if len(self._check_float(val[1]).strip()) > 0  and len(self._check_float(val[6]).strip()) == 0:
                type = 'product'
                product = self.find_product(self._check_float(val[1]).strip())
                if not product:
                    raise ValidationError(_('El material %s de la fila %s no existe') % (self._check_float(val[1]).strip(), str(a)))
                serie = None
                product_qty = 0
                if len(self._check_float(val[4]).strip())>0:
                    serie = self.find_serie(self._check_float(val[4]).strip())
                    if not serie:
                        raise ValidationError(_('La serie %s de la fila %s no existe') % (self._check_float(val[4]).strip(), str(a)))
                    product_qty = 1
                else:
                    product_qty = self.validate_float(val[5])
            elif len(self._check_float(val[1]).strip()) == 0  and len(self._check_float(val[6]).strip()) > 0:
                type = 'activity'
                activity = self.find_activity(self._check_float(val[6]))
                if not activity:
                    raise ValidationError(_('La actividad %s de la fila %s no existe en el contrato seleccionado') % (self._check_float(val[6]).strip(), str(a)))
                activity_qty = self.validate_float(self.validate_float(val[8]))
            
            if type == 'product':
                self.env['im.work.order.liquidation'].create({
                    'work_order_id': work_order.id,
                    'product_id': product.id,
                    'product_qty': product_qty,
                    'lot_id': serie.id if serie else False,
                })
                product_count += 1
            elif type == 'activity':
                self.env['im.work.order.activities'].create({
                    'work_order_id': work_order.id,
                    'activity_id': activity.id,
                    'activity_qty': activity_qty,
                })
                activity_count += 1
            a+=1
        self.msg_validation = (_('- Materiales importados: %s \n - Actividades importadas: %s')% (product_count,activity_count))
        self.excel_file = False