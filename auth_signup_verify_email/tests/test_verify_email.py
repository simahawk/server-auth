# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _
from odoo.tests.common import HttpCase
from odoo.tools.misc import mute_logger
from lxml.html import document_fromstring
import mock


class SignupVerifyEmailCase(HttpCase):

    post_install = True
    at_install = False

    def setUp(self):
        super(SignupVerifyEmailCase, self).setUp()
        # do it here, otherwise is not going to have any effect :(
        self.opener.cookies['frontend_lang'] = 'fr_FR'

        lang = self.env['res.lang'].with_context(active_test=0).search([
            ('code', '=', 'fr_FR'), ('active', '=', False)], limit=1)
        if lang:
            lang.active = True

        self.msg = {
            "badmail": _("That does not seem to be an email address."),
            "failure": _(
                "Something went wrong, please try again later or contact us."),
            "success": _("Check your email to activate your account!"),
        }
        self.patch(
            type(self.env["ir.config_parameter"]),
            'get_param',
            self._fake_get_param)

        self.patch(
            type(self.env["ir.http"]),
            '_get_language_codes',
            self._fake_get_language_codes
        )

    @classmethod
    def _fake_get_language_codes(cls):
        return [('en_US', 'English'), ('fr_FR', 'French')]

    def patch(self, obj, key, val):
        """Overidden to keep old method."""
        old = getattr(obj, key)
        setattr(obj, key, val)
        setattr(obj, 'old_' + key, old)
        self.addCleanup(setattr, obj, key, old)

    def _fake_get_param(self, key, default=False):
        if key == 'auth_signup.allow_uninvited':
            return 'True'
        return self.env["ir.config_parameter"].old_get_param(
            key, default=default)

    @property
    def user_data(self):
        return {
            "csrf_token": self.csrf_token(),
            "name": "Somebody",
        }

    def html_doc(self, url="/web/signup", data=None, timeout=10):
        """Get an HTML LXML document."""
        resp = self.url_open(url, data=data, timeout=timeout)
        return document_fromstring(resp.content)

    def csrf_token(self):
        """Get a valid CSRF token."""
        doc = self.html_doc()
        return doc.xpath("//input[@name='csrf_token']")[0].get("value")

    def search_text(self, doc, text):
        """Search for any element containing the text."""
        return doc.xpath("//*[contains(text(), '%s')]" % text)

    def test_bad_email(self):
        """Test rejection of bad emails."""
        data = self.user_data.copy()
        data["login"] = "bad email"
        doc = self.html_doc(data=data)
        self.assertTrue(self.search_text(doc, self.msg["badmail"]))

    @mute_logger('signup_verify_email.controller')
    def test_good_email(self):
        """Test acceptance of good emails.

        This test could lead to success if your SMTP settings are correct, or
        to failure otherwise. Any case is expected, since tests usually run
        under unconfigured demo instances.
        """
        data = self.user_data.copy()
        data["login"] = "good@example.com"
        doc = self.html_doc(data=data)
        self.assertTrue(
            self.search_text(doc, self.msg["failure"]) or
            self.search_text(doc, self.msg["success"]))

    @mute_logger('signup_verify_email.controller')
    def test_user_lang_preserved(self):
        """In multilang websites the language must be preserved on the user."""
        data = self.user_data.copy()
        data["login"] = "keeplang@example.com"
        to_patch_signup = \
            'odoo.addons.auth_signup.models.res_users.ResUsers.signup'
        with mock.patch(to_patch_signup) as patched:
            self.html_doc(url='/fr_FR/web/signup', data=data)
            patched.assert_called()
            self.assertEqual(patched.call_args[0][0]['lang'], 'fr_FR')
