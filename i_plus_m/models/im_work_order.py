# -*- coding: utf-8 -*-
from ast import Lambda
from email.policy import default
from importlib.metadata import requires
from locale import currency
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)
UNIT = dp.get_precision("Location")


class ImWorkOrder(models.Model):
    _name = 'im.work.order'
    _description = 'Im Work Order'
    _inherit = ['mail.thread']
    name = fields.Char('Work order number', required=True)
    contract_id = fields.Many2one('customer.contracts', string='Contract', required=True,
                                  default=lambda self: self.env.user.contract_to_work)
    region_id = fields.Many2one('region', string='Region', required=True)
    area_id = fields.Many2one('im.area', string='Area')
    service_id = fields.Many2one('im.service', string='Service', required=True)
    work_type_id = fields.Many2one('im.work.order.type', string='Work type', required=True)
    fase = fields.Selection([('mono', 'Monofásico'), ('tri', 'Trifásico')], string="Fase")  #
    substation_ids = fields.Many2many('im.substation', string='Substations')  #
    description_ot = fields.Char('Description OT')
    suministro = fields.Char('Supply')
    post = fields.Char('Post')
    date_up = fields.Date('Date up', readonly=True)
    liquidation_date = fields.Date('Liquidation date', readonly=True)
    pre_liquidation_date = fields.Date('Preliquidation date', readonly=True)
    boleta_number = fields.Char('Boleta number')
    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  domain=[('user_id', '!=', False), ('state', '=', 'up')], tracking=True)
    employee_matricula_id = fields.Many2one('hr.employee.matricula', string='matricula')
    employee_type_worker = fields.Selection(related="employee_id.type_worker")
    employee_dni = fields.Char('DNI')
    asigned_user = fields.Many2one('res.users', string='Asigned user')
    employee_allow_liquidation = fields.Boolean('Allow liquidation', related='employee_id.allow_liquidation')
    employee_location_id = fields.Many2one('stock.location', related='employee_id.location_id')
    contrata_location_id = fields.Many2one('stock.location', related='contrata_id.location_id')
    customer_contract_id = fields.Many2one('res.partner', string='Company', related='contract_id.customer_id',
                                           store=True)
    contrata_id = fields.Many2one('hr.contrata', string='Contrata')
    customer_name = fields.Char(string='Customer')
    phone = fields.Char('Phone')
    address = fields.Char('Address', required=True)
    notes = fields.Text('Notes')
    liq_product_ids = fields.One2many('im.work.order.liquidation', 'work_order_id')
    down_product_ids = fields.One2many('im.work.order.down.line', 'work_order_id')
    state = fields.Selection([('draft', 'Draft'),
                              ('pending', 'Pending'),
                              ('preliq', 'Pre-liquidado'),
                              ('liq', 'liquidado'),
                              ('canceled', 'Canceled')], 'State', default='draft')
    picking_id = fields.Many2one('stock.picking', string='Liquidation picking')
    down_picking_id = fields.Many2one('stock.picking', string='Liquidation down picking')
    return_picking_id = fields.Many2one('stock.picking', string='Returned picking')
    activity_wo_ids = fields.One2many('ot.workorder.activities', 'work_order_id', string='Activities')
    rollback_reason = fields.Char('Rollback reason')
    coordinates = fields.Char('Coordinates', compute='_get_iframe_coordinates')
    liquidation_latitude = fields.Float("Liquidation Latitude", digits=UNIT, readonly=True)
    liquidation_longitude = fields.Float("Liquidation Longitude", digits=UNIT, readonly=True)
    blank = fields.Boolean('Blank', default=True)
    documents_count = fields.Integer('Document count', compute='_compute_documents_count')

    # campos de configuracion del contrato
    generate_ot_sequence_number = fields.Boolean(related='contract_id.generate_ot_sequence_number')
    ot_allows_team = fields.Boolean(related='contract_id.ot_allows_team')
    ot_consume_materials = fields.Boolean(related='contract_id.ot_consume_materials')
    ot_aditionals = fields.Boolean(related='contract_id.ot_aditionals')
    # fin de campos de connfiguracion del contrato.

    # aditionals
    aditionals_ids = fields.One2many('ot.workorder.aditionals', 'workorder_id', string="Aditionals")

    _sql_constraints = [('unique_workorder', 'unique(contract_id, name)',
                         'El numero de Orden de trabajo ya existe en el contrato seleccionado')]

    @api.onchange('employee_id')
    def _get_contrata(self):
        if self.employee_id:
            self.contrata_id = self.employee_id.company_employee_id.id
            self.asigned_user = self.employee_id.user_id.id
            self.employee_dni = self.employee_id.identification_id
        else:
            self.contrata_id = False
            self.asigned_user = False
            self.employee_dni = False

    def _get_iframe_coordinates(self):
        for i in self:
            iframe = False
            if i.liquidation_latitude != 0 or i.liquidation_longitude != 0:
                lng_box1 = i.liquidation_longitude - (i.liquidation_longitude * 0.0001)
                lat_box1 = i.liquidation_latitude - (i.liquidation_latitude * 0.0001)
                lng_box2 = i.liquidation_longitude + (i.liquidation_longitude * 0.0001)
                lat_box2 = i.liquidation_latitude + (i.liquidation_latitude * 0.0001)
                iframe = 'https://www.openstreetmap.org/export/embed.html?bbox=' + str(lng_box1).strip() + '%2C' + str(
                    lat_box1).strip() + '%2C' + str(lng_box2).strip() + '%2C' + str(
                    lat_box2).strip() + '&layer=mapnik&marker=' + str(i.liquidation_latitude).strip() + '%2C' + str(
                    i.liquidation_longitude).strip()
            i.coordinates = iframe

    @api.model
    def create(self, vals):
        vals['state'] = 'pending'
        vals['date_up'] = date.today()
        if vals.get('employee_dni'):
            vals['employee_id'] = self.env['hr.employee'].search([('identification_id', '=', vals['employee_dni'])]).id
        if vals.get('employee_matricula_id'):
            vals['employee_id'] = self.env['hr.employee.matricula'].search(
                [('id', '=', vals['employee_matricula_id'])]).employee_id.id
        if vals.get('employee_id'):
            vals['asigned_user'] = self.env['hr.employee'].search([('id', '=', vals['employee_id'])]).user_id.id
            vals['employee_dni'] = self.env['hr.employee'].search([('id', '=', vals['employee_id'])]).identification_id
        if not vals.get('contrata_id') and vals.get('employee_id'):
            vals['contrata_id'] = self.env['hr.employee'].search(
                [('id', '=', vals['employee_id'])]).company_employee_id.id
        res = super(ImWorkOrder, self).create(vals)
        return res

    def write(self, values):
        if values.get('employee_dni'):
            _logger.warning(values.get('employee_dni'))
            employee = self.env['hr.employee'].search([('identification_id', '=', values.get('employee_dni'))])
            values['employee_id'] = employee.id
            values['asigned_user'] = employee.user_id.id
            values['contrata_id'] = employee.company_employee_id.id
        if values.get('employee_matricula_id'):
            employee = self.env['hr.employee.matricula'].search(
                [('id', '=', values.get('employee_matricula_id'))]).employee_id
            values['employee_id'] = employee.id
            values['asigned_user'] = employee.user_id.id
            values['contrata_id'] = employee.company_employee_id.id
            values['employee_dni'] = employee.identification_id
        res = super(ImWorkOrder, self).write(values)
        return res

    def preliquidar(self):
        # variables para la creacion de picking
        res_id = None
        lista = []
        move_line_lista = []
        down_move_line_lista = []
        location_dest = None
        picking_type = None
        location_src = None

        down_res_id = None
        down_lista = []
        down_location_dest = None
        down_picking_type = None
        down_location_src = None

        if not self.employee_id.location_id and not self.contrata_id.location_id:
            raise ValidationError('No existe una ubicacion de stock del empleado o contrata')

        # Inicio de PICKING de materiales
        if len(self.liq_product_ids) > 0:
            location_dest = int(self.env['ir.config_parameter'].sudo().get_param(
                'i_plus_m.liquidation_location_id'))
            if self.employee_type_worker == 'directo':
                picking_type = self.employee_id.sudo().picking_type_id
                location_src = self.employee_location_id.id
            elif self.employee_type_worker == 'indirecto':
                picking_type = self.contrata_id.sudo().picking_type_id
                location_src = self.contrata_location_id.id
            _logger.warning('Picking type')
            _logger.warning(self.employee_id.sudo().picking_type_id.id)
            for i in self.liq_product_ids:
                lot = False
                lot_name = False
                if i.lot_id:
                    lot = i.lot_id.id
                    lot_name = i.lot_id.name
                move_line_lista.append((0, 0, {
                    'company_id': self.env.company.id,
                    'date': str(date.today()) + ' 00:00:00',
                    'location_dest_id': location_dest,
                    'location_id': location_src,
                    'product_uom_id': i.product_uom_id.id,
                    'product_uom_qty': i.product_qty,
                    'qty_done': i.product_qty,
                    'lot_id': lot,
                    'lot_name': lot_name,
                    'product_id': i.product_id.id,
                }))
                lista.append({
                    'company_id': self.env.company.id,
                    'name': self.name,
                    'date': str(date.today()) + ' 00:00:00',
                    'procure_method': 'make_to_stock',
                    'location_dest_id': location_dest,
                    'location_id': location_src,
                    'product_id': i.product_id.id,
                    'product_uom': i.product_uom_id.id,
                })

            if len(lista) > 0:
                res_id = self.env['stock.picking'].sudo().create({
                    'partner_id': self.employee_id.sudo().user_partner_id.id,
                    'location_dest_id': location_dest,
                    'location_id': location_src,
                    'move_type': 'direct',
                    'picking_type_id': picking_type.id,
                    'user_id': self.env.user.id,
                    'date': str(date.today()) + ' 00:00:00',
                    'immediate_transfer': False,
                    'move_ids_without_package': lista,
                    'move_line_ids_without_package': move_line_lista,
                })

                res_id.sudo().action_confirm()
                self.write({
                    'picking_id': res_id.id,
                    'state': 'preliq',
                    'pre_liquidation_date': date.today(),
                })
        # fin de PICKIN de materiales

        # Inicio de PICKING para baja
        # TODO: establecer sub ubicacion para baja de productos
        if len(self.down_product_ids) > 0:
            down_location_dest = self.employee_id.location_id.id if self.employee_type_worker == 'directo' else self.contrata_id.location_id.id
            if self.employee_type_worker == 'directo':
                down_picking_type = self.employee_id.sudo().picking_type_id
                down_location_src = int(self.env['ir.config_parameter'].sudo().get_param(
                    'i_plus_m.liquidation_location_id'))
            elif self.employee_type_worker == 'indirecto':
                down_picking_type = self.contrata_id.sudo().picking_type_id
                down_location_src = int(self.env['ir.config_parameter'].sudo().get_param(
                    'i_plus_m.liquidation_location_id'))
            for i in self.down_product_ids:
                lot = False
                lot_name = False
                if i.lot_id:
                    lot = i.lot_id.id
                    lot_name = i.lot_id.name
                down_move_line_lista.append((0, 0, {
                    'company_id': self.env.company.id,
                    'date': str(date.today()) + ' 00:00:00',
                    'location_dest_id': down_location_dest,
                    'location_id': down_location_src,
                    'product_uom_id': i.product_uom_id.id,
                    'product_uom_qty': i.product_qty,
                    'qty_done': i.product_qty,
                    'lot_id': lot,
                    'lot_name': lot_name,
                    'product_id': i.product_id.id,
                }))
                down_lista.append({
                    'company_id': self.env.company.id,
                    'name': self.name + ' ' + i.product_id.name,
                    'date': str(date.today()) + ' 00:00:00',
                    'procure_method': 'make_to_stock',
                    'location_dest_id': down_location_dest,
                    'location_id': down_location_src,
                    'product_id': i.product_id.id,
                    'product_uom': i.product_uom_id.id,
                })
            if len(down_lista) > 0:
                down_res_id = self.env['stock.picking'].sudo().create({
                    'partner_id': self.employee_id.sudo().user_partner_id.id,
                    'location_dest_id': down_location_dest,
                    'location_id': down_location_src,
                    'move_type': 'direct',
                    'picking_type_id': down_picking_type.id,
                    'user_id': self.env.user.id,
                    'date': str(date.today()) + ' 00:00:00',
                    'immediate_transfer': False,
                    'move_ids_without_package': down_lista,
                    'move_line_ids_without_package': down_move_line_lista,
                })
                down_res_id.sudo().action_confirm()
                self.write({
                    'down_picking_id': down_res_id.id,
                    'state': 'preliq',
                    'pre_liquidation_date': date.today(),
                })
        # FIN de PICKING para baja

    def action_rollback_liquidation(self):
        # Inicio de validaciones
        if self.state != 'liq':
            raise ValidationError(_('Work order state must be Liquidado to rollback'))
        # if not self.sudo().picking_id:
        #    raise ValidationError(_('Debe existir un moviento de almacen para realizar rollback'))
        # fin de validaciones
        lista = []
        move_line = []
        certificate = self.env['im.production'].search([('work_order_id', '=', self.id), ('state', '=', 'certificate')])
        if len(certificate) > 0:
            raise ValidationError(_('No se puede desverificar de una orden de trabajo certificada.'))
        reportado = self.env['im.production'].search([('work_order_id', '=', self.id), ('state', '=', 'report')])
        if len(reportado) > 0:
            raise ValidationError(
                _('No se puede desverificar de una orden de trabajo con reporte de producción. Primero debe eliminar el reporte de producción'))
        no_certificados = self.env['im.production'].search(
            [('work_order_id', '=', self.id), ('state', '=', 'noreport')])

        for report in no_certificados:
            report.sudo().unlink()

        if self.sudo().picking_id:
            for i in self.sudo().picking_id.move_line_ids:
                move_line.append((0, 0, {
                    'company_id': self.env.company.id,
                    'date': str(date.today()) + ' 00:00:00',
                    'location_dest_id': i.location_id.id,
                    'location_id': i.location_dest_id.id,
                    'product_uom_id': i.product_uom_id.id,
                    'product_uom_qty': i.qty_done,
                    'qty_done': i.qty_done,
                    'lot_id': i.lot_id.id if i.lot_id else False,
                    'lot_name': i.lot_id.name if i.lot_id else False,
                    'product_id': i.product_id.id,
                }))
            for i in self.sudo().picking_id.move_ids_without_package:
                lista.append({
                    'company_id': self.env.company.id,
                    'name': i.name,
                    'date': i.date,
                    'procure_method': 'make_to_stock',
                    'location_dest_id': i.location_id.id,
                    'location_id': i.location_dest_id.id,
                    'product_id': i.product_id.id,
                    'product_uom': i.product_uom.id,
                    # 'product_uom_qty': i.product_uom_qty,
                    # 'quantity_done': i.quantity_done,
                    'to_refund': False,
                    'origin_returned_move_id': i.id,
                })

            res_id = self.env['stock.picking'].sudo().create({
                'partner_id': self.employee_id.sudo().user_partner_id.id,
                'location_dest_id': self.sudo().picking_id.location_id.id,
                'location_id': self.sudo().picking_id.location_dest_id.id,
                'move_type': 'direct',
                'picking_type_id': self.sudo().employee_id.picking_type_id.id,
                'user_id': self.env.user.id,
                'date': self.sudo().picking_id.date,
                'immediate_transfer': False,
                'move_ids_without_package': lista,
                'move_line_ids_without_package': move_line,
                'origin': _('Return from %s', self.sudo().picking_id.name),
            })

            res_id.sudo().button_validate()

        if self.sudo().down_picking_id:
            lista = []
            move_line = []
            res_id = None
            for i in self.sudo().down_picking_id.move_line_ids:
                move_line.append((0, 0, {
                    'company_id': self.env.company.id,
                    'date': str(date.today()) + ' 00:00:00',
                    'location_dest_id': i.location_id.id,
                    'location_id': i.location_dest_id.id,
                    'product_uom_id': i.product_uom_id.id,
                    'product_uom_qty': 0,
                    'qty_done': i.qty_done,
                    'lot_id': i.lot_id.id if i.lot_id else False,
                    'lot_name': i.lot_id.name if i.lot_id else False,
                    'product_id': i.product_id.id,
                }))

            for i in self.sudo().down_picking_id.move_ids_without_package:
                lista.append({
                    'company_id': self.env.company.id,
                    'name': i.name,
                    'date': i.date,
                    'procure_method': 'make_to_stock',
                    'location_dest_id': i.location_id.id,
                    'location_id': i.location_dest_id.id,
                    'product_id': i.product_id.id,
                    'product_uom': i.product_uom.id,
                    'to_refund': False,
                    'origin_returned_move_id': i.id,
                })
            res_id = self.env['stock.picking'].sudo().create({
                'partner_id': self.employee_id.sudo().user_partner_id.id,
                'location_dest_id': self.sudo().down_picking_id.location_id.id,
                'location_id': self.sudo().down_picking_id.location_dest_id.id,
                'move_type': 'direct',
                'picking_type_id': self.sudo().employee_id.picking_type_id.id,
                'user_id': self.env.user.id,
                'date': self.sudo().down_picking_id.date,
                'immediate_transfer': True,
                # 'move_ids_without_package': lista,
                'move_line_ids_without_package': move_line,
                'origin': _('Return from %s', self.sudo().down_picking_id.name),
            })

            res_id.sudo().button_validate()
        self.write({
            'state': 'pending',
            'picking_id': False,
            'down_picking_id': False,
        })
        _body = '<div><h3>Rollback realizado</h3></div>'
        if self.rollback_reason:
            _body += _body + '<p>' + self.rollback_reason + '</p>'

        self.message_post(body=_body)

    def liquidar(self):
        for i in self.liq_product_ids:
            if i.quant - i.product_qty < 0:
                raise ValidationError('Hay productos sin el stock suficiente para cerrar la OT')
        if self.state != 'liq' or self.state != 'preliq':
            self.preliquidar()
        # if self.asigned_user.allow_liquidation:
        if self.env.user.has_group('i_plus_m.group_im_technical') and self.env.user == self.asigned_user:
            if not self.asigned_user.allow_liquidation:
                return
        if self.sudo().picking_id:
            self.sudo().picking_id.button_validate()
        if self.sudo().down_picking_id:
            self.sudo().down_picking_id.button_validate()

        self.write({
            'state': 'liq',
            'liquidation_date': date.today(),
        })
        self.report_production()

    def action_liquidation(self):
        for i in self:
            if len(i.liq_product_ids) == 0 and len(i.down_product_ids) == 0 and len(i.activity_wo_ids) == 0:
                raise ValidationError('No hay productos o actividades para liquidar')

            if i.state == 'pending' or i.state == 'preliq' and \
                    self.env.user.has_group('i_plus_m.group_im_manager') or \
                    self.env.user.has_group('i_plus_m.group_im_user'):
                _body = "<div><h3>Orden de trabajo liquidada</h3></div>"
                i.message_post(body=_body)
                i.liquidar()
                continue

            elif i.state == 'pending' or i.state == 'preliq' and self.env.user.has_group('i_plus_m.group_im_technical'):
                if i.employee_id.sudo().user_id.allow_liquidation:
                    _body = "<div><h3>Orden de trabajo liquidada</h3></div>"
                    i.message_post(body=_body)
                    i.liquidar()
                    continue
                else:
                    _body = "<div><h3>Orden de trabajo pre-liquidada</h3></div>"
                    i.message_post(body=_body)
                    i.preliquidar()
                    continue
            elif i.state == 'pending' or i.state == 'preliq' and \
                    self.env.user.has_group('i_plus_m.group_im_supervisor_contrata'):
                _body = "<div><h3>Orden de trabajo liquidada</h3></div>"
                i.message_post(body=_body)
                i.liquidar()
                continue

            # raise ValidationError('Ha ocurrido un error o usted no tiene los permisos para realizar esta acción')

    def report_production(self):
        activities_cost = 0
        for activity in self.activity_wo_ids:
            activities_cost += self.env['im.production'].get_activity_price(activity.activity_id.id,
                                                                            activity.activity_qty)
        product_cost = 0
        for product in self.liq_product_ids:
            product_cost += self.env['im.production'].get_product_price(product.product_id,
                                                                        self.contract_id) * product.product_qty

        self.env['im.production'].create({
            'name': self.name,
            'work_order_id': self.id,
            'amount_activities': activities_cost,
            'amount_products': product_cost,
            'amount_total': activities_cost + product_cost,
        })

    def action_view_production(self):
        certificate = self.env['im.production'].search([('work_order_id', '=', self.id), ('state', '=', 'certificate')])
        if len(certificate) > 0:
            raise ValidationError(_('No se puede eliminar de una orden de trabajo certificada.'))

        action = self.env['ir.actions.act_window']._for_xml_id('i_plus_m.im_production_action2')
        action['context'] = {
            'default_work_order_id': self.id,
        }
        action['res_id'] = self.env['im.production'].search([('work_order_id', '=', self.id)]).id
        return action

    def cancel(self):
        self.write({
            'state': 'canceled'
        })

    def _compute_documents_count(self):
        self.documents_count = len(self.env['ir.attachment'].search([
            ('res_model', '=', 'im.work.order'),
            ('res_id', '=', self.id)
        ]))

    def attachment_tree_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        action['domain'] = str([('res_model', '=', 'im.work.order'), ('res_id', 'in', self.ids)])
        action['context'] = "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        return action


class ImWorkOrderLine(models.Model):
    _name = 'im.work.order.liquidation'
    _description = 'Work order liquidation'

    @api.onchange('product_id')
    def _get_domain_product(self):
        for i in self:
            if i.employee_location_id:
                return {
                    'domain': {'product_id': [('id', 'in', i.employee_location_id.quant_ids.mapped('product_id.id'))]}}
            elif i.contrata_location_id:
                return {
                    'domain': {'product_id': [('id', 'in', i.contrata_location_id.quant_ids.mapped('product_id.id'))]}}
            else:
                return {'domain': {'product_id': [('id', '=', 0)]}}

    name = fields.Char('Description')
    work_order_id = fields.Many2one('im.work.order')
    product_id = fields.Many2one('product.product', 'Product', required=True, domain=_get_domain_product)
    product_tracking = fields.Selection(related='product_id.product_tmpl_id.tracking')
    product_uom_id = fields.Many2one('uom.uom', related="product_id.uom_id", string='UoM')
    quant = fields.Float('Qty available', compute='get_quant_by_employee_or_contrata')
    product_qty = fields.Float('Product qty', required=True)
    move_id = fields.Many2one('stock.move')
    lots_in_location = fields.Many2many('stock.production.lot', string='Lots by location')
    lot_id = fields.Many2one('stock.production.lot', string='Serie', domain="[('id', 'in' , lots_in_location)]")
    employee_location_id = fields.Many2one('stock.location', related='work_order_id.employee_location_id')
    contrata_location_id = fields.Many2one('stock.location', related='work_order_id.contrata_location_id')

    @api.onchange('product_id')
    def _lots_by_location(self):
        for i in self:
            i.name = i.product_id.name
            lots = None
            if i.product_id:
                if i.product_id.tracking == 'none':
                    i.lots_in_location = False
                    return
                lots = self.env['stock.quant'].search([('product_id', '=', i.product_id.id),
                                                       ('location_id', '=', i.work_order_id.employee_location_id.id)])
                i.lots_in_location = False
                for lot in lots:
                    i.lots_in_location = [(4, lot.lot_id.id)]
            elif not i.product_id:
                lots = self.env['stock.quant'].search(
                    [('location_id', '=', i.work_order_id.employee_location_id.id), ('lot_id', '!=', False)])
                i.lots_in_location = False
                for lot in lots:
                    i.lots_in_location = [(4, lot.lot_id.id)]
            if i.product_tracking == 'serial':
                i.product_qty = 1

    @api.onchange('product_id', 'lot_id')
    def get_quant_by_employee_or_contrata(self):
        for i in self:
            if self.lot_id:
                self.product_id = self.lot_id.product_id
            if not i.work_order_id.employee_id:
                i.quant = 0
                return
            if i.work_order_id.employee_type_worker == 'directo':
                if i.work_order_id.employee_id.location_id:
                    location = i.work_order_id.employee_id.location_id
                    i.quant = i.product_id.with_context(
                        {
                            'location': location.id,
                            'lot_id': i.lot_id.id if i.lot_id else False
                        }).qty_available
                else:
                    i.quant = 0
            elif i.work_order_id.employee_type_worker == 'indirecto':
                if i.work_order_id.contrata_id.location_id:
                    location = i.work_order_id.contrata_id.location_id
                    i.quant = i.product_id.with_context(
                        {
                            'location': location.id,
                            'lot_id': i.lot_id.id if i.lot_id else False
                        }).qty_available
                else:
                    i.quant = 0


class ImWorkOrderDownLine(models.Model):
    _name = 'im.work.order.down.line'
    _description = 'Work order liquidation'

    @api.onchange('lot_id')
    def _get_domain_lot(self):
        location_dest = int(self.env['ir.config_parameter'].sudo().get_param(
            'i_plus_m.liquidation_location_id'))
        customer_location = self.env['stock.location'].search([('id', '=', location_dest)])
        return {'domain': {'lot_id': [('id', 'in', customer_location.quant_ids.mapped('lot_id.id'))]}}

    @api.onchange('product_id')
    def _get_domain_product(self):
        location_dest = int(self.env['ir.config_parameter'].sudo().get_param(
            'i_plus_m.liquidation_location_id'))
        customer_location = self.env['stock.location'].search([('id', '=', location_dest)])
        return {'domain': {'product_id': [('id', 'in', customer_location.quant_ids.mapped('product_id.id'))]}}

    work_order_id = fields.Many2one('im.work.order')
    product_id = fields.Many2one('product.product', string="Product", required=True)
    product_tracking = fields.Selection(related='product_id.product_tmpl_id.tracking')
    product_uom_id = fields.Many2one('uom.uom', related="product_id.uom_id", string='UoM')
    product_qty = fields.Float('Product qty', required=True)
    lot_id = fields.Many2one('stock.production.lot', string='Serie')

    @api.onchange('lot_id')
    def set_lot(self):
        self.product_id = self.lot_id.product_id.id
        if not self.lot_id:
            self.product_qty = 0
        elif self.lot_id:
            self.product_qty = 1


class ImWorkOrderActivities(models.Model):
    _name = 'ot.workorder.activities'
    _description = 'I+M Work order activities'
    activity_id = fields.Many2one('activities', string='Activity', required=True, domain="[]")
    work_order_id = fields.Many2one('im.work.order', string='Work order', required=True)
    activity_qty = fields.Integer('Units', required=True, default=1)
    certification_type = fields.Char('Certification type', readonly=True)

    @api.onchange('activity_id')
    def _get_domain_activity(self):
        for i in self:
            if i.work_order_id._origin:
                return {'domain': {
                    'activity_id': [('id', 'in', i.work_order_id._origin.contract_id.activities_ids.mapped('id'))]}}
            else:
                return {'domain': {'activity_id': [('id', '=', 0)]}}


class OtAditionals(models.Model):
    _name = 'ot.workorder.aditionals'
    _description = 'Workorder aditionals'
    name = fields.Char('Description', required=True)
    quantity = fields.Float('Quantity', default=1, required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id, required=True)
    amount = fields.Monetary('Amount', required=True)
    workorder_id = fields.Many2one('im.work.order', string="Workorder")


class WorkOrderByDates(models.TransientModel):
    _name = 'im.work.order.by.dates'
    _description = 'Work orders by dates'
    date_start = fields.Date('Date start', required=True)
    date_end = fields.Date('Date end', required=True)
    date_to_filter = fields.Selection([('liq', 'Liquidation date'), ('up', 'Date up')], default='liq', required=True)

    def get_work_orders(self):
        action = self.env['ir.actions.act_window']._for_xml_id('i_plus_m.im_work_order_action')
        if self.date_to_filter == 'liq':
            action['domain'] = str([('liquidation_date', '>=', self.date_start.strftime("%Y-%m-%d")),
                                    ('liquidation_date', '<=', self.date_end.strftime("%Y-%m-%d"))])
        else:
            action['domain'] = str([('date_up', '>=', self.date_start.strftime("%Y-%m-%d")),
                                    ('date_up', '<=', self.date_end.strftime("%Y-%m-%d"))])
        return action
