from dataclasses import field
from pyexpat import model
from select import select
import string
from odoo import models, fields

#test
class Service(models.Model):
    _name = 'im.service'
    _description = 'Services'
    sequence = fields.Integer()
    name = fields.Char('Service', required=True)
    code = fields.Char('Código',required=True)
    contract_id = fields.Many2one('customer.contracts',required=True,string="Contrato")
    area_id = fields.Many2one('im.area')
    _sql_constraints = [('unique_code', 'unique(code)', 'El código de servicio debe ser único')]
    
class OrderType(models.Model):
    _name = 'im.work.order.type'
    _description = 'work order type'
    sequence = fields.Integer()
    service_id = fields.Many2one('im.service', string="Service")
    name = fields.Char('Order type', required=True)
    code = fields.Char('Código',required=True)
    contract_id = fields.Many2one('customer.contracts',required=True,string="Contrato")
    area_id = fields.Many2one('im.area')
    _sql_constraints = [('unique_code', 'unique(code)', 'El código de tipo de orden debe ser único')]

class imArea(models.Model):
    _name = 'im.area'
    _description = 'Area OT'
    sequence = fields.Integer()
    name = fields.Char('Area', required=True)
    code = fields.Char('Code', required=True)
    contract_id = fields.Many2one('customer.contracts', string='Contrato', required=True)
    _sql_constraints = [('unique_code', 'unique(code)', 'El código de área debe ser único')]

class imSubStation(models.Model):
    _name = 'im.substation'
    _description = 'Substation'
    sequence = fields.Integer()
    name = fields.Char('Substation', required=True)
    code = fields.Char('Code', required=True)
    contract_id = fields.Many2one('customer.contracts', string='Contrato', required=True)
    _sql_constraints = [('unique_code', 'unique(code)', 'El código de subestación debe ser único')]

class OtTeam(models.Model):
    _name = 'ot.team'
    _description = 'OT Team'
    name = fields.Char('Team', required=True)
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id.id)
    goal_production = fields.Monetary('Goal production', required=True)
    contrata_id = fields.Many2one('hr.contrata', string="Contratista",required=True)
    contract_id = fields.Many2one('customer.contracts', string='Contrat', required=True)
    employee_id = fields.Many2one('hr.employee', string='Team Leader', required=True)
    employee_ids = fields.One2many('ot.team.employees', 'ot_team_id', string="Team employees")

class OtTeamEmployees(models.Model):
    _name = 'ot.team.employees'
    _description = 'ot.team.employees'
    ot_team_id = fields.Many2one('ot.team', string='Team')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    job_id = fields.Many2one('hr.job', related="employee_id.job_id")
    contrata_id = fields.Many2one('hr.contrata', string="Contratista", related='ot_team_id.contrata_id')

