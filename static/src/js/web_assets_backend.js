odoo.define('signatures.mail_settings_widget_extend', function (require) {
    'use strict';

    var rpc = require('web.rpc');
    const FormRenderer = require('web.FormRenderer');

    FormRenderer.include({
        events: {
            'change .signatures_nebiz': '_onClickSignature',
            'click .o_ChatterTopbar_buttonSendMessage': '_sendMessage',
            'click .o_ChatterTopbar_buttonLogNote': '_sendLog',
        },

        _populateSignature: function () {
            var self = this;
            if (!$('.o_ChatterTopbar_buttonSendMessage').hasClass('o-active')) {
                var checkExist = setInterval(function () {
                    var signature = $('.signatures_nebiz');
                    if (signature.length) {
                        var html_options = "<option class='sign_option' value=''>----Select your signature----</option>";
                        self._rpc({
                            model: 'nebiz.signatures',
                            method: 'get_my_signatures',
                            args: [self.state],
                        }).then(function (result) {
                            result.forEach(function (signature) {
                                html_options = html_options + "<option class='sign_option' value='" + signature['id'] + "'>" + signature['name'] + "</option>";
                            });
                            signature.html(html_options);
                        });
                        clearInterval(checkExist);
                    }
                }, 100);
            }
        },

        _sendMessage: function () {
            this._populateSignature();
        },

        _sendLog: function () {
            this._populateSignature();
        },

        _onClickSignature: function () {
            var signature = $('.signatures_nebiz');
            var active_sign = signature.val();
            rpc.query({
                model: 'nebiz.signatures',
                method: "set_active_signature",
                args: [{'sign_id': active_sign}]
            });
        },

    });

});