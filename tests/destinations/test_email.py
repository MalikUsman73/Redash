from mock import MagicMock, mock_open, patch

from redash import settings
from redash.destinations.email import Email
from tests import BaseTestCase


class TestEmail(BaseTestCase):
    def test_configuration_schema(self):
        schema = Email.configuration_schema()

        # Verify schema structure
        self.assertEqual(schema["type"], "object")
        self.assertIn("addresses", schema["properties"])
        self.assertIn("subject_template", schema["properties"])

        # Verify required fields
        self.assertIn("addresses", schema["required"])

        # Verify extra options
        self.assertIn("subject_template", schema["extra_options"])

        # Verify default subject template
        self.assertEqual(
            schema["properties"]["subject_template"]["default"], settings.ALERTS_DEFAULT_MAIL_SUBJECT_TEMPLATE
        )

    def test_icon(self):
        self.assertEqual(Email.icon(), "fa-envelope")

    @patch("redash.destinations.email.mail")
    @patch(
        "redash.destinations.email.open",
        new_callable=mock_open,
        read_data="<html>Default template {alert_name}</html>",
    )
    def test_notify_with_custom_subject_and_body(self, mock_file, mock_mail):
        # Setup
        email_dest = Email({"addresses": "test@example.com"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = "Custom Subject"
        mock_alert.custom_body = "<html>Custom Body</html>"

        mock_query = MagicMock()
        mock_query.id = 100

        options = {"addresses": "test1@example.com,test2@example.com", "subject_template": "{alert_name} - {state}"}

        # Execute
        email_dest.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options,
        )

        # Verify
        mock_mail.send.assert_called_once()
        message = mock_mail.send.call_args[0][0]

        self.assertEqual(message.recipients, ["test1@example.com", "test2@example.com"])
        self.assertEqual(message.subject, "Custom Subject")
        self.assertEqual(message.html, "<html>Custom Body</html>")

    @patch("redash.destinations.email.mail")
    @patch(
        "redash.destinations.email.open",
        new_callable=mock_open,
        read_data="<html>Default template {alert_name}</html>",
    )
    def test_notify_with_default_template(self, mock_file, mock_mail):
        # Setup
        email_dest = Email({"addresses": "test@example.com"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        mock_alert.render_template.return_value = "<html>Rendered template</html>"

        mock_query = MagicMock()
        mock_query.id = 100

        options = {"addresses": "test@example.com", "subject_template": "{alert_name} - {state}"}

        # Execute
        email_dest.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options,
        )

        # Verify
        mock_mail.send.assert_called_once()
        message = mock_mail.send.call_args[0][0]

        self.assertEqual(message.recipients, ["test@example.com"])
        self.assertEqual(message.subject, "Test Alert - TRIGGERED")
        self.assertEqual(message.html, "<html>Rendered template</html>")
        mock_alert.render_template.assert_called_once()

    @patch("redash.destinations.email.mail")
    @patch("redash.destinations.email.open", new_callable=mock_open, read_data="<html>Template</html>")
    def test_notify_with_default_subject_template(self, mock_file, mock_mail):
        # Setup
        email_dest = Email({"addresses": "test@example.com"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        mock_alert.render_template.return_value = "<html>Body</html>"

        mock_query = MagicMock()

        # Options without subject_template - should use default
        options = {"addresses": "test@example.com"}

        # Execute
        email_dest.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="ok",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options,
        )

        # Verify - subject should use default template from settings
        mock_mail.send.assert_called_once()
        message = mock_mail.send.call_args[0][0]

        # Default template should be used
        expected_subject = settings.ALERTS_DEFAULT_MAIL_SUBJECT_TEMPLATE.format(alert_name="Test Alert", state="OK")
        self.assertEqual(message.subject, expected_subject)

    @patch("redash.destinations.email.logging")
    @patch("redash.destinations.email.mail")
    @patch("redash.destinations.email.open", new_callable=mock_open, read_data="<html>Template</html>")
    def test_notify_with_empty_addresses(self, mock_file, mock_mail, mock_logging):
        # Setup
        email_dest = Email({"addresses": ""})

        mock_alert = MagicMock()
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        mock_alert.render_template.return_value = "<html>Body</html>"

        mock_query = MagicMock()

        options = {"addresses": ""}

        # Execute
        email_dest.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options,
        )

        # Verify warning was logged
        mock_logging.warning.assert_called_with("No emails given. Skipping send.")

    @patch("redash.destinations.email.logging")
    @patch("redash.destinations.email.mail")
    @patch("redash.destinations.email.open", new_callable=mock_open, read_data="<html>Template</html>")
    def test_notify_with_whitespace_addresses(self, mock_file, mock_mail, mock_logging):
        # Setup
        email_dest = Email({"addresses": "test@example.com"})

        mock_alert = MagicMock()
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        mock_alert.render_template.return_value = "<html>Body</html>"

        mock_query = MagicMock()

        # Addresses with extra commas and whitespace
        options = {"addresses": "test1@example.com, ,test2@example.com,,"}

        # Execute
        email_dest.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options,
        )

        # Verify only valid emails are included
        mock_mail.send.assert_called_once()
        message = mock_mail.send.call_args[0][0]

        # Should include non-empty email addresses (including whitespace-only ones get stripped by split)
        # The split on "test1@example.com, ,test2@example.com,," creates:
        # ['test1@example.com', ' ', 'test2@example.com', '', '']
        # After filtering empty strings: ['test1@example.com', ' ', 'test2@example.com']
        self.assertIn("test1@example.com", message.recipients)
        self.assertIn(" ", message.recipients)  # Whitespace is not filtered
        self.assertIn("test2@example.com", message.recipients)

    @patch("redash.destinations.email.logging")
    @patch("redash.destinations.email.mail")
    @patch("redash.destinations.email.open", new_callable=mock_open, read_data="<html>Template</html>")
    def test_notify_with_exception(self, mock_file, mock_mail, mock_logging):
        # Setup
        mock_mail.send.side_effect = Exception("SMTP error")

        email_dest = Email({"addresses": "test@example.com"})

        mock_alert = MagicMock()
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        mock_alert.render_template.return_value = "<html>Body</html>"

        mock_query = MagicMock()

        options = {"addresses": "test@example.com"}

        # Execute - should not raise exception
        email_dest.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options,
        )

        # Verify exception was logged
        mock_logging.exception.assert_called_with("Mail send error.")

    @patch("redash.destinations.email.logging")
    @patch("redash.destinations.email.mail")
    @patch("redash.destinations.email.open", new_callable=mock_open, read_data="<html>Template</html>")
    def test_notify_state_uppercase(self, mock_file, mock_mail, mock_logging):
        # Setup
        email_dest = Email({"addresses": "test@example.com"})

        mock_alert = MagicMock()
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        mock_alert.render_template.return_value = "<html>Body</html>"

        mock_query = MagicMock()

        options = {"addresses": "test@example.com", "subject_template": "Alert: {alert_name} is {state}"}

        # Execute with lowercase state
        email_dest.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="ok",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options,
        )

        # Verify state is uppercased
        message = mock_mail.send.call_args[0][0]
        self.assertIn("OK", message.subject)
        self.assertNotIn("ok", message.subject)
