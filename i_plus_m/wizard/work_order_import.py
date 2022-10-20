import tempfile
import binascii
import xlrd
import json
from odoo.exceptions import Warning, UserError
from odoo import models, fields, exceptions, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import date, datetime
import io
import logging

_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')

import re

regex_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

class WorkOrderImport(models.TransientModel):
    _name = 'work.order.import'
    _description = 'Work order import'
    file = fields.Binary('Archivo')
    file_name = fields.Char()
    msg_validation = fields.Text('', readonly="1")
    output_file = fields.Binary('Template', readonly=True)
    output_name = fields.Char('Output')
    output_error = fields.Binary('Output error')
    output_error_name = fields.Char('Output error name')
    count_output_file = fields.Integer('Error qty')
    contract_id = fields.Many2one('customer.contracts',string='Contract', required=True)

    def find_employee(self, dni):
        employee_search = self.env['hr.employee'].search([('identification_id', '=', dni)])
        if not employee_search:
            return False # empleado no registrado
        else:
            return employee_search

    def find_region(self, val):
        res = self.env['region'].search([('name', '=ilike', val)])
        if res:
            return res
        else:
            return False

    def find_service(self, val):
        res = self.env['im.service'].search([('name', '=ilike', val)])
        if res:
            return res
        else:
            return False

    def find_work_type(self, val):
        res = self.env['im.work.order.type'].search([('name', '=ilike', val)])
        if res:
            return res
        else:
            return False

    def validate_numbers(self,val):
        try:
            float(val)
            return int(float(val))
        except ValueError:
            return False

    def validate_string_numbers(self,val):
        _logger.warning(val)
        _logger.warning(isinstance(val, str))
        if self.validate_numbers(val):
            return self.validate_numbers(val)
        res = bool(re.match('[0-9a-zA-Z\s]+$', val))
        if not res:
            return False
        else:
            return val

    def validate_string(self, val):
        res = bool(re.match('[a-zA-Z\s]+$', val))
        if not res:
            return False
        else:
            return val

    def validate_email(self,val):
        if (re.fullmatch(regex_email, val)):
            return val
        else:
            return False
    #return false if Cell is empty and True if cell is no empty
    def validate_empty_cell(self,val):
        if len(val) == 0:
            return False
        else:
            return True

    def false_to_null(self,val):
        if not val:
            return ''
        else:
            return val

    def format_date(self, date):
        if not date:
            return False
        if not self.validate_numbers(date):
            return False
        dt = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + date - 2)
        return dt

    def import_work_orders(self):
        extension = ''
        if self.file:
            file_name = str(self.file_name)
            extension = file_name.split('.')[1]
        if extension not in ['xls', 'xlsx', 'XLS', 'XLSX']:
            raise exceptions.Warning(_('Cargue solo el archivo xls o xlsx.!'))
        fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.file))
        fp.seek(0)
        values = {}
        res = {}
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        new = 0
        out = []
        file = 0
        self.msg_validation = ""

        for row_no in range(sheet.nrows):
            if row_no <= 0:
                fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
            else:
                line = list(
                    map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                        sheet.row(row_no)))
                employee = None
                name = None
                region = None
                service = None
                work_type = None
                boleta_number = None
                customer_name = None
                phone = None
                address = None
                error_count = 0
                error_text = []
                values = {}

                if not self.validate_string_numbers(line[0]):
                    if self.validate_numbers(line[0]):
                        name = self.validate_numbers(line[0])
                    else:
                        error_count += 1
                        error_text.append(['Numero de contrato'])
                else:
                    name = self.validate_string_numbers(line[0])

                if not self.validate_numbers(line[1]):
                    error_count += 1
                    error_text.append(['Documento empleado'])
                else:
                    employee = self.find_employee(self.validate_numbers(line[1]))
                    if not employee:
                        error_count += 1
                        error_text.append(['Empleado no registrado'])
                    elif employee.type_worker != 'directo':
                        error_count += 1
                        error_text.append(['No es un trabajador directo'])

                if not self.find_region(line[2]):
                    error_count += 1
                    error_text.append(['Región'])
                else:
                    region = self.find_region(line[2])

                if not self.find_service(line[3]):
                    error_count += 1
                    error_text.append(['Service'])
                else:
                    service = self.find_service(line[3])

                if not self.find_work_type(line[4]):
                    error_count += 1
                    error_text.append(['Work type'])
                else:
                    work_type = self.find_work_type(line[4])

                if not self.validate_string(line[5]):
                    boleta_number = False
                else:
                    boleta_number = self.validate_string(line[5])

                if not self.validate_string(line[6]):
                    customer_name = False
                else:
                    customer_name = self.validate_string(line[6])

                if not self.validate_string_numbers(line[7]):
                    phone = False
                else:
                    phone = self.validate_string(line[7])

                if not self.validate_string_numbers(line[8]):
                    error_count += 1
                    error_text.append(['Address'])
                    address = ''
                else:
                    address = self.validate_string_numbers(line[8])

                file += 1
                if error_count > 0:
                    out.append([
                        line[0],self.validate_numbers(line[1]),line[2],line[3],line[4],line[5],
                        line[6],line[7],line[8],str(error_text)
                    ])
                    self.count_output_file += 1
                else:
                    values.update({'contract_id': self.contract_id.id,
                                   'name': name,
                                   'employee_id': employee.id,
                                   'contrata_id': employee.company_employee_id.id,
                                   'region_id': region.id,
                                   'service_id': service.id,
                                   'work_type_id': work_type.id,
                                   'boleta_number': boleta_number,
                                   'customer_name': customer_name,
                                   'phone': phone,
                                   'address': address,
                                   })
                    
                    work_order = self.env['im.work.order'].create(values)
                    if work_order:
                        new += 1

        if len(out) >0:
            workbook_out = xlwt.Workbook()
            style2 = xlwt.easyxf('font:bold True,height 200,')
            style3 = xlwt.easyxf('align:vert center')
            sheet = workbook_out.add_sheet('Errores', cell_overwrite_ok=True)
            sheet.write(0, 0, 'Nro contrato', style2)
            sheet.write(0, 1, 'Técnico', style2)
            sheet.write(0, 2, 'Región', style2)
            sheet.write(0, 3, 'Service', style2)
            sheet.write(0, 4, 'Tipo de orden', style2)
            sheet.write(0, 5, 'Boleta', style2)
            sheet.write(0, 6, 'Cliente', style2)
            sheet.write(0, 7, 'Telefono', style2)
            sheet.write(0, 8, 'Dirección', style2)
            n = 1;
            for i in out:
                sheet.write(n, 0, i[0], style3)
                sheet.write(n, 1, i[1], style3)
                sheet.write(n, 2, i[2], style3)
                sheet.write(n, 3, i[3], style3)
                sheet.write(n, 4, i[4], style3)
                sheet.write(n, 5, i[5], style3)
                sheet.write(n, 6, i[6], style3)
                sheet.write(n, 7, i[7], style3)
                sheet.write(n, 8, i[8], style3)
                sheet.write(n, 9, i[9], style3)
                n += 1;

            filename = ('////opt/odoo/custom-addons/i_plus_m/Importar errores.xls')
            workbook_out.save(filename)
            fp = open(filename, "rb")
            file_data = fp.read()
            self.output_file = base64.encodebytes(file_data)
            self.output_name = 'error.xls'
            fp.close()

        self.msg_validation = self.msg_validation + '* Se han creado ' + str(new) + ' nuevas ordenes de trabajo \n'
        self.file = False

    def download_template(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_import_work_order_template',
            'target': 'new',
        }
    
    @api.onchange('contract_id')
    def onchange_contract_id(self):
        self.output_file = False

    def customize_import(self):
        workbook_out = xlwt.Workbook()
        style1 = xlwt.easyxf('font:bold True,height 200,')
        sheet = workbook_out.add_sheet('test', cell_overwrite_ok=True)
        cols = self.env['contract.work.order.import'].search([('contract_id','=',self.contract_id.id)])
        i = 0
        for col in cols:
            sheet.write(0, i, _(col.field_id.field_description), style1)
            i += 1
        filename = ('////opt/odoo/custom-addons/i_plus_m/Custom import.xls')
        workbook_out.save(filename)
        fp = open(filename, "rb")
        file_data = fp.read()
        self.output_file = base64.encodebytes(file_data)
        self.output_name = 'plantilla ' + self.contract_id.name +'.xls'
        fp.close()

    def import_customize_file(self):
        cols = self.env['contract.work.order.import'].search([('contract_id','=',self.contract_id.id)])
        extension = ''
        if self.file:
            file_name = str(self.file_name)
            extension = file_name.split('.')[1]
        if extension not in ['xls', 'xlsx', 'XLS', 'XLSX']:
            raise exceptions.Warning(_('Cargue solo el archivo xls o xlsx.!'))
        fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.file))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        count_work_order = 0
        count_update_work_order = 0
        error_count = 0
        error_list = []
        for row_no in range(sheet.nrows):
            list_values = {}
            error_count = 0
            if row_no <= 0:
                fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
            else:
                line = list(
                    map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                        sheet.row(row_no)))
                i = 0
                list_values['contract_id'] = self.contract_id.id
                errors_line = []
                
                for col in cols:
                    val = None
                    if col.field_id.ttype == 'many2one' and col.allow_import:
                        val = self.env[col.field_id.relation].search([('code','=',line[i])]).id
                    elif col.allow_import:
                        if col.field_id.ttype == 'date':
                            val = self.format_date(line[i])
                        elif col.field_id.ttype == 'char':
                            if col.field_id.name == 'name':
                                val = line[i]
                            else:
                                val = self.validate_string_numbers(line[i])
                        elif col.field_id.ttype == 'integer':
                            val = self.validate_numbers(line[i])
                    i+=1 
                    if col.field_id.required and val:
                        list_values[col.field_id.name] = val
                    elif not col.field_id.required:
                        list_values[col.field_id.name] = val
                    elif col.field_id.required and not val:
                        errors_line.append(_(col.field_id.field_description))
                        error_count+=1

                if error_count > 0:
                    line.append(str(errors_line))
                    error_list.append(line)
                else:
                    _logger.warning(str(list_values))    
                    wo = self.env['im.work.order'].search([('name',"=",list_values['name']),('contract_id',"=",self.contract_id.id),('state','=','pending')])
                    if wo:
                        wo.write(list_values)
                        count_update_work_order+=1
                    else:
                        work_order = self.env['im.work.order'].create(list_values)
                        if work_order:
                            count_work_order+=1
        
        _logger.warning(str(error_list))  
        if len(error_list) > 0:  
            workbook_out = xlwt.Workbook()
            style2 = xlwt.easyxf('font:bold True,height 200,')
            style3 = xlwt.easyxf('align:vert center')
            style4 = xlwt.easyxf('align:vert center', num_format_str='dd/mm/yyyy')
            sheet = workbook_out.add_sheet('Errores', cell_overwrite_ok=True)
            i = 0
            for col in cols:
                sheet.write(0, i, _(col.field_id.field_description), style2)
                i+=1
            n = 1
            for errors in error_list:
                i = 0
                _logger.warning(str(errors))
                for error in errors:
                    sheet.write(n, i, error, style3)
                    i+=1
                n+=1
            filename = ('//opt/odoo/custom-addons/i_plus_m/import_errors.xls')
            workbook_out.save(filename)
            fp = open(filename, "rb")
            file_data = fp.read()
            self.output_error = base64.encodebytes(file_data)
            self.output_error_name = 'error.xls'
            fp.close()
        self.msg_validation = '* Se han creado ' + str(count_work_order) + ' nuevas ordenes de trabajo y se actualizaron '+ str(count_update_work_order) +' Ordenes de trabajo\n'
        self.output_file = False
        self.file = False
        self.file_name = False