from mock import MagicMock, patch
from tests import BaseTestCase
from redash.destinations.hangoutschat import HangoutsChat
import json


class TestHangoutsChat(BaseTestCase):
    def test_name(self):
        self.assertEqual(HangoutsChat.name(), "Google Hangouts Chat")

    def test_type(self):
        self.assertEqual(HangoutsChat.type(), "hangouts_chat")

    def test_configuration_schema(self):
        schema = HangoutsChat.configuration_schema()
        
        # Verify schema structure
        self.assertEqual(schema["type"], "object")
        self.assertIn("url", schema["properties"])
        self.assertIn("icon_url", schema["properties"])
        
        # Verify required fields
        self.assertIn("url", schema["required"])
        
        # Verify secret fields
        self.assertIn("url", schema["secret"])

    def test_icon(self):
        self.assertEqual(HangoutsChat.icon(), "fa-bolt")

    @patch("redash.destinations.hangoutschat.requests.post")
    def test_notify_triggered_state(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        hangouts = HangoutsChat({"url": "https://chat.googleapis.com/webhook"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "url": "https://chat.googleapis.com/webhook"
        }
        
        # Execute
        hangouts.notify(
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
        
        self.assertEqual(call_args[0][0], "https://chat.googleapis.com/webhook")
        
        # Parse the posted data
        posted_data = json.loads(call_args[1]["data"])
        
        # Verify card structure
        self.assertIn("cards", posted_data)
        self.assertEqual(posted_data["cards"][0]["header"]["title"], "Test Alert")
        
        # Verify triggered message
        message_text = posted_data["cards"][0]["sections"][0]["widgets"][0]["textParagraph"]["text"]
        self.assertIn("Triggered", message_text)
        self.assertIn("#c0392b", message_text)  # Red color
        
        # Verify button with query link
        button = posted_data["cards"][0]["sections"][0]["widgets"][1]["buttons"][0]
        self.assertEqual(button["textButton"]["text"], "OPEN QUERY")
        self.assertIn("/queries/100", button["textButton"]["onClick"]["openLink"]["url"])

    @patch("redash.destinations.hangoutschat.requests.post")
    def test_notify_ok_state(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        hangouts = HangoutsChat({"url": "https://chat.googleapis.com/webhook"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "url": "https://chat.googleapis.com/webhook"
        }
        
        # Execute
        hangouts.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="ok",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify
        posted_data = json.loads(mock_post.call_args[1]["data"])
        
        # Verify ok message
        message_text = posted_data["cards"][0]["sections"][0]["widgets"][0]["textParagraph"]["text"]
        self.assertIn("Went back to normal", message_text)
        self.assertIn("#27ae60", message_text)  # Green color

    @patch("redash.destinations.hangoutschat.requests.post")
    def test_notify_unknown_state(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        hangouts = HangoutsChat({"url": "https://chat.googleapis.com/webhook"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "url": "https://chat.googleapis.com/webhook"
        }
        
        # Execute with unknown state
        hangouts.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="unknown",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify
        posted_data = json.loads(mock_post.call_args[1]["data"])
        
        # Verify unknown state message
        message_text = posted_data["cards"][0]["sections"][0]["widgets"][0]["textParagraph"]["text"]
        self.assertIn("Unable to determine status", message_text)

    @patch("redash.destinations.hangoutschat.requests.post")
    def test_notify_with_custom_subject_and_body(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        hangouts = HangoutsChat({"url": "https://chat.googleapis.com/webhook"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = "Custom Subject"
        mock_alert.custom_body = "Custom Body Content"
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "url": "https://chat.googleapis.com/webhook"
        }
        
        # Execute
        hangouts.notify(
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
        
        # Verify custom subject
        self.assertEqual(posted_data["cards"][0]["header"]["title"], "Custom Subject")
        
        # Verify custom body is added as second section
        self.assertEqual(len(posted_data["cards"][0]["sections"]), 2)
        custom_body_text = posted_data["cards"][0]["sections"][1]["widgets"][0]["textParagraph"]["text"]
        self.assertEqual(custom_body_text, "Custom Body Content")

    @patch("redash.destinations.hangoutschat.requests.post")
    def test_notify_with_icon_url(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        hangouts = HangoutsChat({"url": "https://chat.googleapis.com/webhook"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "url": "https://chat.googleapis.com/webhook",
            "icon_url": "https://example.com/icon.png"
        }
        
        # Execute
        hangouts.notify(
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
        
        # Verify icon URL is set
        self.assertEqual(posted_data["cards"][0]["header"]["imageUrl"], "https://example.com/icon.png")

    @patch("redash.destinations.hangoutschat.requests.post")
    def test_notify_without_host(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        hangouts = HangoutsChat({"url": "https://chat.googleapis.com/webhook"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "url": "https://chat.googleapis.com/webhook"
        }
        
        # Execute without host
        hangouts.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host=None,
            metadata={},
            options=options
        )
        
        # Verify
        posted_data = json.loads(mock_post.call_args[1]["data"])
        
        # Verify no button is added when host is None
        widgets = posted_data["cards"][0]["sections"][0]["widgets"]
        self.assertEqual(len(widgets), 1)  # Only the message widget, no button

    @patch("redash.destinations.hangoutschat.logging")
    @patch("redash.destinations.hangoutschat.requests.post")
    def test_notify_with_error_response(self, mock_post, mock_logging):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        hangouts = HangoutsChat({"url": "https://chat.googleapis.com/webhook"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "url": "https://chat.googleapis.com/webhook"
        }
        
        # Execute
        hangouts.notify(
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

    @patch("redash.destinations.hangoutschat.logging")
    @patch("redash.destinations.hangoutschat.requests.post")
    def test_notify_with_exception(self, mock_post, mock_logging):
        # Setup
        mock_post.side_effect = Exception("Network error")
        
        hangouts = HangoutsChat({"url": "https://chat.googleapis.com/webhook"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "url": "https://chat.googleapis.com/webhook"
        }
        
        # Execute - should not raise exception
        hangouts.notify(
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
        mock_logging.exception.assert_called_with("webhook send ERROR.")
