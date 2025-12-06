from mock import Mock, patch
from tests import BaseTestCase
from redash import settings, models
import sys
import importlib

# Mock ldap3 - persistent across tests in this process
if 'ldap3' not in sys.modules:
    mock_ldap3 = Mock()
    mock_ldap3.Server = Mock()
    mock_ldap3.Connection = Mock()
    mock_ldap3.utils.conv.escape_filter_chars = lambda x: x
    sys.modules['ldap3'] = mock_ldap3
    sys.modules['ldap3.utils'] = Mock()
    sys.modules['ldap3.utils.conv'] = Mock()
    sys.modules['ldap3.utils.conv'].escape_filter_chars = lambda x: x

from redash.authentication import ldap_auth
from redash.authentication.ldap_auth import auth_ldap_user

class TestLDAPAuth(BaseTestCase):
    def setUp(self):
        super(TestLDAPAuth, self).setUp()
        # Force reload to ensure ldap3 mock is used and module is fresh
        importlib.reload(ldap_auth) 
        self.old_ldap_login_enabled = settings.LDAP_LOGIN_ENABLED
        self.old_ldap_host_url = settings.LDAP_HOST_URL
        self.old_ldap_bind_dn = settings.LDAP_BIND_DN
        self.old_ldap_auth_method = settings.LDAP_AUTH_METHOD
        
        settings.LDAP_LOGIN_ENABLED = True
        settings.LDAP_HOST_URL = "ldap://localhost"
        settings.LDAP_BIND_DN = "cn=admin,dc=example,dc=com"
        settings.LDAP_BIND_DN_PASSWORD = "password"
        settings.LDAP_AUTH_METHOD = "SIMPLE"
        settings.LDAP_SEARCH_DN = "dc=example,dc=com"
        settings.LDAP_SEARCH_TEMPLATE = "(cn=%(username)s)"
        settings.LDAP_DISPLAY_NAME_KEY = "displayName"
        settings.LDAP_EMAIL_KEY = "mail"
        self.old_ldap_login_enabled = settings.LDAP_LOGIN_ENABLED
        self.old_ldap_host_url = settings.LDAP_HOST_URL
        self.old_ldap_bind_dn = settings.LDAP_BIND_DN
        self.old_ldap_auth_method = settings.LDAP_AUTH_METHOD
        
        settings.LDAP_LOGIN_ENABLED = True
        settings.LDAP_HOST_URL = "ldap://localhost"
        settings.LDAP_BIND_DN = "cn=admin,dc=example,dc=com"
        settings.LDAP_BIND_DN_PASSWORD = "password"
        settings.LDAP_AUTH_METHOD = "SIMPLE"
        settings.LDAP_SEARCH_DN = "dc=example,dc=com"
        settings.LDAP_SEARCH_TEMPLATE = "(cn=%(username)s)"
        settings.LDAP_DISPLAY_NAME_KEY = "displayName"
        settings.LDAP_EMAIL_KEY = "mail"

    def tearDown(self):
        settings.LDAP_LOGIN_ENABLED = self.old_ldap_login_enabled
        settings.LDAP_HOST_URL = self.old_ldap_host_url
        settings.LDAP_BIND_DN = self.old_ldap_bind_dn
        settings.LDAP_AUTH_METHOD = self.old_ldap_auth_method
        super(TestLDAPAuth, self).tearDown()

    @patch("redash.authentication.ldap_auth.Server")
    @patch("redash.authentication.ldap_auth.Connection")
    def test_auth_ldap_user_success(self, mock_connection_cls, mock_server_cls):
        # Setup Mock Connection
        mock_conn = Mock()
        mock_connection_cls.return_value = mock_conn
        
        mock_entry = Mock()
        mock_entry.entry_dn = "cn=user,dc=example,dc=com"
        mock_entry.attributes = {"displayName": ["Test User"], "mail": ["test@example.com"]}
        # Simulate ldap3 entry access
        mock_entry.__getitem__ = Mock(side_effect=lambda k: mock_entry.attributes[k])
        
        mock_conn.entries = [mock_entry]
        mock_conn.search.return_value = True
        mock_conn.rebind.return_value = True 

        user = auth_ldap_user("user", "password")
        
        self.assertIsNotNone(user)
        self.assertEqual(user["displayName"][0], "Test User")
        self.assertEqual(user["mail"][0], "test@example.com")

    @patch("redash.authentication.ldap_auth.Server")
    @patch("redash.authentication.ldap_auth.Connection")
    def test_auth_ldap_user_search_fail(self, mock_connection_cls, mock_server_cls):
        mock_conn = Mock()
        mock_connection_cls.return_value = mock_conn
        mock_conn.entries = [] 
        
        user = auth_ldap_user("nouser", "password")
        self.assertIsNone(user)

    @patch("redash.authentication.ldap_auth.Server")
    @patch("redash.authentication.ldap_auth.Connection")
    def test_auth_ldap_user_bind_fail(self, mock_connection_cls, mock_server_cls):
        mock_conn = Mock()
        mock_connection_cls.return_value = mock_conn
        mock_entry = Mock()
        mock_entry.entry_dn = "cn=user,dc=example,dc=com"
        mock_conn.entries = [mock_entry]
        mock_conn.rebind.return_value = False 
        
        user = auth_ldap_user("user", "wrong")
        self.assertIsNone(user)

    @patch("redash.authentication.ldap_auth.create_and_login_user")
    @patch("redash.authentication.ldap_auth.auth_ldap_user")
    @patch("redash.authentication.ldap_auth.current_user")
    def test_login_success(self, mock_current_user, mock_auth_ldap_user, mock_create_and_login):
        mock_current_user.is_authenticated = False
        mock_user = {
            "displayName": ["LDAP User"],
            "mail": ["ldap@example.com"]
        }
        mock_auth_ldap_user.return_value = mock_user
        mock_create_and_login.return_value = True

        from redash.authentication.ldap_auth import login
        
        with self.app.test_request_context("/ldap/login", method="POST", data={"email": "ldap", "password": "pwd"}):
            rv = login(org_slug="default")
            # Redirect 302
            self.assertEqual(rv.status_code, 302)
            
            self.assertTrue(mock_create_and_login.called)
            args, _ = mock_create_and_login.call_args
            self.assertEqual(args[1], "LDAP User")
            self.assertEqual(args[2], "ldap@example.com")

    @patch("redash.authentication.ldap_auth.auth_ldap_user")
    @patch("redash.authentication.ldap_auth.current_user")
    def test_login_fail(self, mock_current_user, mock_auth_ldap_user):
        mock_current_user.is_authenticated = False
        mock_auth_ldap_user.return_value = None
        
        from redash.authentication.ldap_auth import login

        with self.app.test_request_context("/ldap/login", method="POST", data={"email": "ldap", "password": "wrong"}):
            rv = login(org_slug="default")
            # Render template returns string or response object? 
            # render_template returns string in test context usually unless processed?
            # Actually render_template returns str.
            # But the code might return it directly. 
            # If rv is str, we check content.
            # If response, check status.
            if hasattr(rv, 'status_code'):
                self.assertEqual(rv.status_code, 200)
            else:
                self.assertIsInstance(rv, str)
                self.assertIn("Incorrect credentials", rv)

    @patch("redash.authentication.ldap_auth.current_user")
    def test_login_disabled(self, mock_current_user):
        mock_current_user.is_authenticated = False
        settings.LDAP_LOGIN_ENABLED = False
        from redash.authentication.ldap_auth import login
        
        with self.app.test_request_context("/ldap/login"):
             rv = login(org_slug="default")
             self.assertEqual(rv.status_code, 302)

    @patch("redash.authentication.ldap_auth.current_user")
    def test_login_authenticated(self, mock_current_user):
        mock_current_user.is_authenticated = True
        from redash.authentication.ldap_auth import login
        
        with self.app.test_request_context("/ldap/login"):
             rv = login(org_slug="default")
             self.assertEqual(rv.status_code, 302)
