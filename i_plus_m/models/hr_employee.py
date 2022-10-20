import logging
from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    allow_liquidation = fields.Boolean('Allow liquidation')
    identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user,i_plus_m.group_im_manager", tracking=True)
    

class ResPartner(models.Model):
    _inherit = 'res.partner'
    allow_liquidation = fields.Boolean('Allow liquidation', default=False)


class HrContrata(models.Model):
    _inherit = 'hr.contrata'
    supervisor_contrata_ids = fields.Many2many('hr.employee',string='Supervisor contrata')


