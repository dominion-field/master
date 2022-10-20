odoo.define('i_plus_m.JsToCallWizard', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var Context = require('web.Context');
    var JsTocallWizard = ListController.include({
      renderButtons: function($node){
        this._super.apply(this, arguments);
        if (this.$buttons) {
          this.$buttons.on('click', '.o_button_to_call_wizard', this.action_to_call_wizard.bind(this));
          //this.$buttons.on('click', '.call_wizard_asigned_employee', this.call_wizard_asigned_employee.bind(this));
          this.$buttons.appendTo($node);
        }

      },
      action_to_call_wizard: function(event) {
        event.preventDefault();
        this.do_action({
            name: "Open a wizard",
            type: 'ir.actions.act_window',
            res_model: 'im.work.order.by.dates',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
         });
      },

      /*call_wizard_asigned_employee: function(event){
        event.preventDefault();
        console.log(this.getSelectedIds())
        this.do_action({
          name: "Open a wizard",
          type: 'ir.actions.act_window',
          res_model: 'im.report.production.date',
          view_mode: 'form',
          view_type: 'form',
          views: [[false, 'form']],
          target: 'new',
          context: {
            active_ids: this.getSelectedIds(),
          }
       });
      },*/
    });
});