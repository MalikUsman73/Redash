from mock import Mock, patch
from tests import BaseTestCase
from redash import settings
from flask import request

class TestSAMLAuth(BaseTestCase):
    def setUp(self):
        super(TestSAMLAuth, self).setUp()
        self.old_saml_enabled = self.factory.org.get_setting("auth_saml_enabled")
        self.factory.org.set_setting("auth_saml_enabled", True)
        self.factory.org.set_setting("auth_saml_type", "static")
        self.factory.org.set_setting("auth_saml_entity_id", "redash")
        self.factory.org.set_setting("auth_saml_sso_url", "http://idp.example.com")
        self.factory.org.set_setting("auth_saml_x509_cert", "cert")
        self.factory.org.set_setting("auth_saml_metadata_url", "http://idp.example.com/metadata")

    def tearDown(self):
        self.factory.org.set_setting("auth_saml_enabled", self.old_saml_enabled)
        super(TestSAMLAuth, self).tearDown()

    @patch("redash.authentication.saml_auth.Saml2Client")
    @patch("redash.authentication.saml_auth.Saml2Config")
    def test_get_saml_client(self, mock_saml_config, mock_saml_client):
        from redash.authentication.saml_auth import get_saml_client
        
        with self.app.test_request_context("/"):
             client = get_saml_client(self.factory.org)
             self.assertIsNotNone(client)
             mock_saml_client.assert_called()

    @patch("redash.authentication.saml_auth.get_saml_client")
    def test_sp_initiated(self, mock_get_client):
        mock_client_instance = Mock()
        mock_get_client.return_value = mock_client_instance
        mock_client_instance.prepare_for_authenticate.return_value = (None, {"headers": [("Location", "http://idp.example.com/sso")]})
        
        from redash.authentication.saml_auth import sp_initiated
        
        with self.app.test_request_context("/saml/login"):
            request.view_args = {"org_slug": "default"}
            rv = sp_initiated(org_slug="default")
            self.assertEqual(rv.status_code, 302)
            self.assertEqual(rv.location, "http://idp.example.com/sso")

    @patch("redash.authentication.saml_auth.get_saml_client")
    @patch("redash.authentication.saml_auth.create_and_login_user")
    def test_idp_initiated_success(self, mock_create_user, mock_get_client):
        mock_client_instance = Mock()
        mock_get_client.return_value = mock_client_instance
        
        mock_authn_response = Mock()
        mock_client_instance.parse_authn_request_response.return_value = mock_authn_response
        
        mock_authn_response.get_subject.return_value = Mock(text="saml@example.com")
        mock_authn_response.ava = {"FirstName": ["SAML"], "LastName": ["User"]}
        
        mock_create_user.return_value = Mock() 
        
        from redash.authentication.saml_auth import idp_initiated
        
        with self.app.test_request_context("/saml/callback", method="POST", data={"SAMLResponse": "dummy"}):
            request.view_args = {"org_slug": "default"}
            rv = idp_initiated(org_slug="default")
            self.assertEqual(rv.status_code, 302)
            self.assertTrue(rv.location.endswith("/default/") or rv.location == "/default/")
            
            mock_create_user.assert_called()
            args, _ = mock_create_user.call_args
            self.assertEqual(args[2], "saml@example.com")
            self.assertEqual(args[1], "SAML User")

    @patch("redash.authentication.saml_auth.get_saml_client")
    def test_idp_initiated_fail(self, mock_get_client):
        mock_client_instance = Mock()
        mock_get_client.return_value = mock_client_instance
        
        mock_client_instance.parse_authn_request_response.side_effect = Exception("Parse error")
        
        from redash.authentication.saml_auth import idp_initiated
        
        with self.app.test_request_context("/saml/callback", method="POST", data={"SAMLResponse": "bad"}):
            request.view_args = {"org_slug": "default"}
            rv = idp_initiated(org_slug="default")
            self.assertEqual(rv.status_code, 302)
            self.assertIn("/login", rv.location)

    def test_sp_initiated_disabled(self):
        self.factory.org.set_setting("auth_saml_enabled", False)
        from redash.authentication.saml_auth import sp_initiated
        with self.app.test_request_context("/saml/login"):
             request.view_args = {"org_slug": "default"}
             rv = sp_initiated(org_slug="default")
             self.assertEqual(rv.status_code, 302)
             self.assertIn("/default/", rv.location)
