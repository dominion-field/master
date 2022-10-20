from odoo import models, fields,_
from odoo.exceptions import ValidationError
from datetime import  date
import logging
_logger = logging.getLogger(__name__)


class ImPreCertification(models.Model):
    _name = 'im.production'
    _description = 'I+M production report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char('Description')
    work_order_id = fields.Many2one('im.work.order')
    contract_id = fields.Many2one('customer.contracts', related='work_order_id.contract_id')
    customer_id = fields.Many2one('res.partner',related='work_order_id.contract_id.customer_id')
    contrata_id = fields.Many2one('hr.contrata', related='work_order_id.contrata_id')
    amount_activities = fields.Monetary('Cost activities')
    amount_products = fields.Monetary('Cost products')    
    amount_total = fields.Monetary('Cost total')
    amount_customer = fields.Monetary('Customer cost total', tracking=True)
    currency_id = fields.Many2one('res.currency',string='Currency', default=lambda self: self.env.ref('base.main_company').currency_id)
    liquidation_date = fields.Date('Liquidation date', related='work_order_id.liquidation_date')
    report_date = fields.Date('Report date',readonly=True)
    certification_date = fields.Date('Certification date',readonly=True)
    state = fields.Selection([('noreport','No reported'),('report','Reported'),('certificate','Certificate'),('cancel','Cancel')], default='noreport',string='State', tracking=True)
    active = fields.Boolean('Active', default=True)
    reason = fields.Text('Reason')
    observation = fields.Text('Observación')
    
    def test(self):
        self.write({
            'reason':self.reason,
            'state': 'cancel',
            'active': False
        })

        self.work_order_id.write({
            'rollback_reason': self.reason,
        })
    

    def report_certification(self):
        if self.state == 'report' or self.state == 'cancel' or self.state == 'certificate':
            return
        self.write({
            'state': 'report',
            'report_date': date.today(),
            'amount_customer': self.amount_total
        })

    def action_report_production(self):
        active_ids = self.env.context.get('active_ids', [])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Report production'),
            'res_model': 'im.report.production.date',
            'view_type': 'form',
            'context': {'default_active_ids': active_ids},
            'view_mode': 'form',
            'target': 'new',
        }

    def action_certificate(self):
        active_ids = self.env.context.get('active_ids', [])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Certificate production'),
            'res_model': 'im.certification',
            'view_type': 'form',
            'context': {'default_active_ids': active_ids},
            'view_mode': 'form',
            'target': 'new',
        }

    def certify(self):
        for i in self:
            if i.state == 'certificate' or i.state == 'noreport' or i.state == 'cancel':
                return
            i.write({
            'state': 'report',
            'certificate_date': date.today(),
            'amount_customer': self.amount_customer
        })


    def get_activity_price(self,activity, ammount):
        return self.env['activities'].search([('id', '=', activity)])._get_price(fields.Date.today(),ammount)
        '''activity_contract = self.env['activities'].search([('activity_id', '=', activity), \
                                                                       ('contract_id', '=', contract)])
        if activity_contract.certification_type == 'score':
            return activity_contract.point_baremo
        else:
            return activity_contract.cost'''
    
    def get_product_price(self,product, contract):
        product_contract = self.env['product.price.list.contract'].search([('product_tmpl_id','=',product.product_tmpl_id.id),('contract_id','=',contract.id)],limit=1)
        if not product_contract:
            res = product.standard_price
        else: 
            res = product_contract.cost
        return res


class ReportProductionDate(models.TransientModel):
    _name = 'im.report.production.date'
    _description = 'Production report date'
    date = fields.Date('Report date', required=True)

    message = fields.Char('Message', compute="_get_message")
    
    def report_production(self):
        selected_ids = self.env.context.get('active_ids', []) #Obtiene los IDs de las filas selecionadas
        if len(selected_ids) == 0:
            raise ValidationError(_('You did not select any row to report production'))

        selected_records = self.env['im.production'].browse(selected_ids) # Obtiene los objetos de los IDs 
        for i in selected_records:
            if i.state == 'report' or i.state == 'cancel' or i.state == 'certificate':
                return
            i.write({
                'report_date': self.date,
                'state': 'report',
                'amount_customer': i.amount_total
            })

        
    def _get_message(self):
        selected_ids = self.env.context.get('active_ids', [])
        self.message = 'Usted ha seleccionado ' + str(len(selected_ids)) + ' filas para reportar la producción'


class ImCertification(models.TransientModel):
    _name = 'im.certification'
    _description = 'im.certification'
    date = fields.Date('Certification date', required=True)
    message = fields.Char('Message', compute="_get_message")
    
    def certify_production(self):
        selected_ids = self.env.context.get('active_ids', []) #Obtiene los IDs de las filas selecionadas
        if len(selected_ids) == 0:
            raise ValidationError(_('You did not select any row to report production'))

        selected_records = self.env['im.production'].browse(selected_ids) # Obtiene los objetos de los IDs 
        for i in selected_records:
            if i.state == 'noreport' or i.state == 'cancel' or i.state == 'certificate':
                return
            i.write({
                'certification_date': self.date,
                'state': 'certificate',
            })
        
        
    def _get_message(self):
        selected_ids = self.env.context.get('active_ids', [])
        self.message = 'Usted ha seleccionado ' + str(len(selected_ids)) + ' filas para reportar la producción'

class ProductPriceListContract(models.Model):
    _name = 'product.price.list.contract'
    _description = 'Product price list contract'
    name = fields.Many2one('customer.contracts')
    contract_id = fields.Many2one('customer.contracts')
    cost = fields.Monetary('Cost', currency_field='currency_company')
    currency_company = fields.Many2one('res.currency',
                                        default=lambda self: self.env.ref('base.main_company').currency_id)
    product_tmpl_id = fields.Many2one('product.template')


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    price_list_certification_ids = fields.One2many('product.price.list.contract','product_tmpl_id',string='Certification price list')


class OtReportProduction(models.Model):
    _name = 'ot.report.production'
    _description = 'OtReportProduction'
    date_report = fields.Date(string='Date report')
    contract_id = fields.Many2one('customer.contracts', string="Contract_id")
    date_start = fields.Date(string='Date start')
    date_end = fields.Date(string='Date end')
    amount_activities = fields.Float('Cost activities')
    amount_products = fields.Float('Cost products')    
    amount_total = fields.Float('Cost total')
    amount_customer = fields.Float('Customer cost total', compute='_compute_amount_total')
    workorders_ids = fields.One2many('ot.report.production.line','production_id')

    def action_get_workorders(self):
        workorders = []
        
        production_activity_cost = 0
        production_product_cost = 0

        for i in self.env['im.work.order'].search(
            ['|',('date_up','>=',self.date_start),('date_up','<=',self.date_end),
            ('state','=','liq'), 
            ('id', 'not in', self.workorders_ids.mapped('workorder_id.id')),
            ('contract_id','=',self.contract_id.id)]):
            activity_cost = 0
            product_cost = 0
            for activities in i.activity_wo_ids:
                activity_cost += activities.activity_id._get_price(i.date_up, activities.activity_qty)
            for product in i.liq_product_ids:
                product_cost += product.product_id.standard_price * product.product_qty
            workorders.append({
                'workorder_id': i.id,
                'amount_activities': activity_cost,
                'amount_products': product_cost,
                'amount_total': activity_cost + product_cost,
                'amount_customer': 0,
                'production_id': self.id,
                'employee_id': i.employee_id.id,

            })
            production_activity_cost += activity_cost
            production_product_cost += product_cost
        self.env['ot.report.production.line'].create(workorders)
        self.write({
            'amount_activities': production_activity_cost,
            'amount_products': production_product_cost,
            'amount_total': production_activity_cost + production_product_cost,
        })
    
    def _compute_amount_total(self):
        for i in self:
            i.amount_customer = sum(i.workorders_ids.mapped('amount_customer'))

        
class otReportProductionLine(models.Model):
    _name = 'ot.report.production.line'
    _description = 'OT Report production lines'
    workorder_id = fields.Many2one('im.work.order', required=True)
    amount_activities = fields.Float('Cost activities')
    amount_products = fields.Float('Cost products')    
    amount_total = fields.Float('Cost total')
    amount_customer = fields.Float('Customer cost total')
    production_id = fields.Many2one('ot.report.production')
    employee_id = fields.Many2one('hr.employee')
    service_id = fields.Many2one('im.service', related='workorder_id.service_id', store=True)
    work_type_id = fields.Many2one('im.work.order.type', related='workorder_id.work_type_id',store=True)
    contrata_id = fields.Many2one('hr.contrata', related='workorder_id.contrata_id',store=True)
    contract_id = fields.Many2one('customer.contracts', related='workorder_id.contract_id',store=True)

    