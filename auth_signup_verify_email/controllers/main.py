# Copyright 2015 Antiun Ingeniería, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from odoo import _, http
from odoo.addons.auth_signup.controllers.main import AuthSignupHome

request = http.request
_logger = logging.getLogger('signup_verify_email.controller')

try:
    from validate_email import validate_email
except ImportError:
    _logger.debug("Cannot import `validate_email`.")


class SignupVerifyEmail(AuthSignupHome):

    @http.route()
    def web_auth_signup(self, *args, **kw):
        if (request.params.get("login") and
                not request.params.get("password")):
            return self.passwordless_signup(request.params)
        else:
            return super(SignupVerifyEmail, self).web_auth_signup(*args, **kw)

    @property
    def msg_invalid_email_error(self):
        return _("That does not seem to be an email address.")

    @property
    def msg_something_wrong_error(self):
        return _("Something went wrong, please try again later or contact us.")

    @property
    def msg_check_inbox_info(self):
        return _("Check your email to activate your account!")

    def passwordless_signup(self, values):
        qcontext = self.get_auth_signup_qcontext()

        # Check good format of e-mail
        if not validate_email(values.get("login", "")):
            qcontext["error"] = self.msg_invalid_email_error
            return request.render("auth_signup.signup", qcontext)
        elif not values.get("email"):
            values["email"] = values.get("login")

        # Remove password
        values["password"] = ""
        sudo_users = (request.env["res.users"]
                      .with_context(create_user=True).sudo())

        try:
            with request.cr.savepoint():
                sudo_users.signup(values, qcontext.get("token"))
                sudo_users.reset_password(values.get("login"))
        except Exception as error:
            # Duplicate key or wrong SMTP settings, probably
            _logger.exception(error)

            # Agnostic message for security
            qcontext["error"] = self.msg_something_wrong_error
            return request.render("auth_signup.signup", qcontext)

        qcontext["message"] = self.msg_check_inbox_info
        return request.render("auth_signup.reset_password", qcontext)
