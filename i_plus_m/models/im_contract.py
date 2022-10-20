from email.policy import default
from lib2to3.pgen2.token import RARROW
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ImContract(models.Model):
    _inherit = 'customer.contracts'
    _description = 'I+M Contracts'
    
    work_order_fields_ids = fields.One2many('contract.work.order.import', 'contract_id', string="Work order fields")
    generate_ot_sequence_number = fields.Boolean('Generate OT sequence number', default=False)
    sequence_id = fields.Many2one('ir.sequence', string="OT sequence")
    ot_allows_team = fields.Boolean('OT allows team', default=False)
    ot_consume_materials = fields.Boolean('OT consume materials', default=True)
    ot_aditionals = fields.Boolean('OT aditionals', default=False)

    def action_work_order_view(self):
        self.env.user.sudo().write({
            'contract_to_work': self.id,
        })
        action = self.env['ir.actions.act_window']._for_xml_id('i_plus_m.im_work_order_action')
        action['domain'] = str([('contract_id', '=', self.id)])
        action['context'] = {
                            'default_contract_id': self.id,
                            "search_default_pending": 1,
                            }
        return action

    @api.model
    def create(self, vals):
        res = super(ImContract,self).create(vals)
        self.env['contract.work.order.import'].create({
            'contract_id': res.id,
            'field_id': self.env['ir.model.fields'].with_context(lang='es_PE').\
                search([('model', '=', 'im.work.order'), ('name', '=', 'name')]).id,
            'allow_import': True
        })
        
        self.env['contract.work.order.import'].create({
            'contract_id': res.id,
            'field_id': self.env['ir.model.fields'].\
                search([('model', '=', 'im.work.order'), ('name', '=', 'region_id')]).id,
            'allow_import': True
        })

        self.env['contract.work.order.import'].create({
            'contract_id': res.id,
            'field_id': self.env['ir.model.fields'].\
                search([('model', '=', 'im.work.order'), ('name', '=', 'service_id')]).id,
            'allow_import': True
        })

        self.env['contract.work.order.import'].create({
            'contract_id': res.id,
            'field_id': self.env['ir.model.fields'].\
                search([('model', '=', 'im.work.order'), ('name', '=', 'work_type_id')]).id,
            'allow_import': True
        })

        self.env['contract.work.order.import'].create({
            'contract_id': res.id,
            'field_id': self.env['ir.model.fields'].search([('model', '=', 'im.work.order'), ('name', '=', 'address')]).id,
            'allow_import': True
        })

        return res

    def work_order_new_field(self):
        action = self.env['ir.actions.act_window']._for_xml_id('i_plus_m.work_order_new_field_action')
        action['domain'] = []
        action['context'] = "{}"
        return action
    
    def action_show_ots_by_contract(self):
        raise ValidationError('Prueba')
        
            
class contractWorkOrderImport(models.Model):
    _name = 'contract.work.order.import'
    _description = 'contract.work.order.import'
    sequence = fields.Integer()
    contract_id = fields.Many2one('customer.contracts', string="Contract")
    field_id = fields.Many2one('ir.model.fields', string='Field', required=True, ondelete='cascade')
    allow_import = fields.Boolean('Import', default=True)

class ResUsers(models.Model):
    _inherit = 'res.users'
    contract_to_work = fields.Many2one('customer.contracts', string='Contract to work')
    allow_liquidation = fields.Boolean('Allow liquidation')


FIELD_TYPES = [(key, key) for key in sorted(fields.Field.by_type)]
class IrModelFields(models.TransientModel):
    _name = 'im.new.field'
    _description = 'New field for work orders'
    name = fields.Char(string='Field Name', default='x_', required=True, index=True)
    field_description = fields.Char(string='Field Label', default='', required=True, translate=True)
    ttype = fields.Selection(selection=FIELD_TYPES, string='Field Type', required=True)
    relation = fields.Char(string='Related Model',
                           help="For relationship fields, the technical name of the target model")
    contract_id = fields.Many2one('customer.contracts', 'Contract', required=True, readonly=True, default=lambda self: self.env.user.contract_to_work)
    

    def create_new_im_field(self):
        model_id = self.env['ir.model'].search([('model', '=', 'im.work.order')]).id
        model = self.env['ir.model'].search([('model', '=', 'im.work.order')]).model
        state = 'manual'

        self.env['ir.model.fields'].create({
            'name': self.name,
            'field_description': self.field_description,
            'model_id': model_id,
            'model': model,
            'ttype': self.ttype,
            'relation': self.relation,
            'state': state,
        })

        head_view = '<?xml version="1.0"?> \
                    <xpath expr="//group[@name=\'group_information\']" position="inside"> \
                    <group>'
        foot_view = '</group>\
                    </xpath>'
        content_view = ''
        for i in self.env['ir.model.fields'].search([('model','=','im.work.order'),('state','=','manual')]):
            content_view += '<field name="' + i.name + '" attrs="{\'invisible\':[(\'contract_id\',\'=\',\''+str(self.contract_id.id)+'\')]'+'}"/>'
        
        self.env['ir.ui.view'].browse(self.env.ref('i_plus_m.inherit_work_order_customize_fields_form').id).write({
            'arch_base': head_view + content_view + foot_view
            }
        )
        