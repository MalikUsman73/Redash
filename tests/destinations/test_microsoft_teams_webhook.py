from mock import MagicMock, patch
from tests import BaseTestCase
from redash.destinations.microsoft_teams_webhook import MicrosoftTeamsWebhook, json_string_substitute
import json


class TestJsonStringSubstitute(BaseTestCase):
    def test_json_string_substitute_with_substitutions(self):
        # Test basic substitution
        json_str = '{"name": "{user_name}", "id": "{user_id}"}'
        substitutions = {"user_name": "John", "user_id": "123"}
        
        result = json_string_substitute(json_str, substitutions)
        
        self.assertIn('"name": "John"', result)
        self.assertIn('"id": "123"', result)

    def test_json_string_substitute_without_substitutions(self):
        # Test with None substitutions
        json_str = '{"name": "{user_name}", "id": "{user_id}"}'
        
        result = json_string_substitute(json_str, None)
        
        self.assertEqual(result, json_str)

    def test_json_string_substitute_empty_dict(self):
        # Test with empty dict
        json_str = '{"name": "{user_name}", "id": "{user_id}"}'
        
        result = json_string_substitute(json_str, {})
        
        self.assertEqual(result, json_str)

    def test_json_string_substitute_preserves_braces(self):
        # Test that braces are preserved in JSON
        json_str = '{"data": {"nested": "{value}"}}'
        substitutions = {"value": "test"}
        
        result = json_string_substitute(json_str, substitutions)
        
        # Should preserve JSON structure braces
        self.assertIn('{"data":', result)
        self.assertIn('"nested": "test"', result)


class TestMicrosoftTeamsWebhook(BaseTestCase):
    def test_name(self):
        self.assertEqual(MicrosoftTeamsWebhook.name(), "Microsoft Teams Webhook")

    def test_type(self):
        self.assertEqual(MicrosoftTeamsWebhook.type(), "microsoft_teams_webhook")

    def test_configuration_schema(self):
        schema = MicrosoftTeamsWebhook.configuration_schema()
        
        # Verify schema structure
        self.assertEqual(schema["type"], "object")
        self.assertIn("url", schema["properties"])
        self.assertIn("message_template", schema["properties"])
        
        # Verify required fields
        self.assertIn("url", schema["required"])
        
        # Verify default message template
        self.assertEqual(
            schema["properties"]["message_template"]["default"],
            MicrosoftTeamsWebhook.ALERTS_DEFAULT_MESSAGE_TEMPLATE
        )

    def test_icon(self):
        self.assertEqual(MicrosoftTeamsWebhook.icon(), "fa-bolt")

    def test_default_message_template_structure(self):
        # Verify the default template is valid JSON
        template = MicrosoftTeamsWebhook.ALERTS_DEFAULT_MESSAGE_TEMPLATE
        parsed = json.loads(template)
        
        # Verify structure
        self.assertEqual(parsed["@type"], "MessageCard")
        self.assertIn("sections", parsed)
        self.assertIn("facts", parsed["sections"][0])

    @patch("redash.destinations.microsoft_teams_webhook.requests.post")
    def test_notify_with_default_template(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        teams = MicrosoftTeamsWebhook({"url": "https://outlook.office.com/webhook/xxx"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        
        mock_query = MagicMock()
        mock_query.id = 100
        mock_query.query_text = "SELECT * FROM users"
        
        options = {
            "url": "https://outlook.office.com/webhook/xxx"
        }
        
        # Execute
        teams.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        self.assertEqual(call_args[0][0], "https://outlook.office.com/webhook/xxx")
        self.assertEqual(call_args[1]["headers"]["Content-Type"], "application/json")
        self.assertEqual(call_args[1]["timeout"], 5.0)
        
        # Parse the posted data
        posted_data = json.loads(call_args[1]["data"])
        
        # Verify substitutions were made
        facts = posted_data["sections"][0]["facts"]
        alert_name_fact = next(f for f in facts if f["name"] == "Alert Name")
        self.assertEqual(alert_name_fact["value"], "Test Alert")
        
        query_fact = next(f for f in facts if f["name"] == "Query")
        self.assertEqual(query_fact["value"], "SELECT * FROM users")

    @patch("redash.destinations.microsoft_teams_webhook.requests.post")
    def test_notify_with_custom_template(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        teams = MicrosoftTeamsWebhook({"url": "https://outlook.office.com/webhook/xxx"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        
        mock_query = MagicMock()
        mock_query.id = 100
        mock_query.query_text = "SELECT * FROM users"
        
        custom_template = json.dumps({
            "text": "Alert: {alert_name}",
            "url": "{alert_url}"
        })
        
        options = {
            "url": "https://outlook.office.com/webhook/xxx",
            "message_template": custom_template
        }
        
        # Execute
        teams.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify
        posted_data = json.loads(mock_post.call_args[1]["data"])
        
        # Verify custom template was used
        self.assertEqual(posted_data["text"], "Alert: Test Alert")
        self.assertIn("/alerts/1", posted_data["url"])

    @patch("redash.destinations.microsoft_teams_webhook.requests.post")
    def test_notify_url_construction(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        teams = MicrosoftTeamsWebhook({"url": "https://outlook.office.com/webhook/xxx"})
        
        mock_alert = MagicMock()
        mock_alert.id = 42
        mock_alert.name = "Test Alert"
        
        mock_query = MagicMock()
        mock_query.id = 99
        mock_query.query_text = "SELECT 1"
        
        options = {
            "url": "https://outlook.office.com/webhook/xxx"
        }
        
        # Execute
        teams.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="https://redash.mycompany.com",
            metadata={},
            options=options
        )
        
        # Verify
        posted_data = json.loads(mock_post.call_args[1]["data"])
        
        # Check URL construction
        alert_url_fact = next(f for f in posted_data["sections"][0]["facts"] if f["name"] == "Alert URL")
        self.assertEqual(alert_url_fact["value"], "https://redash.mycompany.com/alerts/42")
        
        query_url_fact = next(f for f in posted_data["sections"][0]["facts"] if f["name"] == "Query URL")
        self.assertEqual(query_url_fact["value"], "https://redash.mycompany.com/queries/99")

    @patch("redash.destinations.microsoft_teams_webhook.logging")
    @patch("redash.destinations.microsoft_teams_webhook.requests.post")
    def test_notify_with_error_response(self, mock_post, mock_logging):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        teams = MicrosoftTeamsWebhook({"url": "https://outlook.office.com/webhook/xxx"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        
        mock_query = MagicMock()
        mock_query.id = 100
        mock_query.query_text = "SELECT 1"
        
        options = {
            "url": "https://outlook.office.com/webhook/xxx"
        }
        
        # Execute
        teams.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify error logging
        mock_logging.error.assert_called()
        error_message = mock_logging.error.call_args[0][0]
        self.assertIn("400", error_message)

    @patch("redash.destinations.microsoft_teams_webhook.logging")
    @patch("redash.destinations.microsoft_teams_webhook.requests.post")
    def test_notify_with_exception(self, mock_post, mock_logging):
        # Setup
        mock_post.side_effect = Exception("Network error")
        
        teams = MicrosoftTeamsWebhook({"url": "https://outlook.office.com/webhook/xxx"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        
        mock_query = MagicMock()
        mock_query.id = 100
        mock_query.query_text = "SELECT 1"
        
        options = {
            "url": "https://outlook.office.com/webhook/xxx"
        }
        
        # Execute - should not raise exception
        teams.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify exception logging
        mock_logging.exception.assert_called_with("MS Teams Webhook send ERROR.")
