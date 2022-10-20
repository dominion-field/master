# -*- coding: utf-8 -*-
{
    'name': "Workorders dominion",

    'summary': """
        Manage dominion's work orders 
        """,

    'description': """
        
    """,

    'author': "David Lizarraga - Dominion",
    'website': "http://www.dominion-global.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'hr_employees_dominion',
                'stock', 
                'bandeja_dominion',
                'account',
                'customer_contracts',
                ],
    # always loaded
    'data': [
        'data/im_data.xml',
        'security/im_security.xml',
        'security/ir.model.access.csv',
        'views/im_configuration.xml',
        'views/work_order_views.xml',
        'views/res_config_settings_view.xml',
        'views/hr_employee.xml',
        'views/im_contract.xml',
        'views/im_activities.xml',
        'views/im_certification.xml',
        'views/hr_contrata.xml',
        'views/assets_backend.xml',
        'views/res_users.xml',
        #'views/work_order_location.xml',
        'wizard/work_order_import.xml',
        'wizard/work_order_by_date.xml',
        'wizard/report_production_wizard.xml',
        'wizard/new_fields_work_order_wizard.xml',
    ],
    'qweb': [
        'static/src/xml/template.xml',
    ],
}