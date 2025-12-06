from tests import BaseTestCase


class TestWSGI(BaseTestCase):
    def test_wsgi_app_creation(self):
        """Test that the WSGI module creates a valid Flask app."""
        # Import the wsgi module to trigger app creation
        from redash import wsgi

        # Verify the app object exists
        self.assertIsNotNone(wsgi.app)

        # Verify it's a Flask application
        self.assertTrue(hasattr(wsgi.app, 'config'))
        self.assertTrue(hasattr(wsgi.app, 'route'))

        # Verify app name
        self.assertEqual(wsgi.app.name, 'redash.app')
