from mock import MagicMock, patch
from tests import BaseTestCase
from redash.destinations.chatwork import ChatWork


class TestChatWork(BaseTestCase):
    def test_configuration_schema(self):
        schema = ChatWork.configuration_schema()
        
        # Verify schema structure
        self.assertEqual(schema["type"], "object")
        self.assertIn("api_token", schema["properties"])
        self.assertIn("room_id", schema["properties"])
        self.assertIn("message_template", schema["properties"])
        
        # Verify required fields
        self.assertIn("api_token", schema["required"])
        self.assertIn("room_id", schema["required"])
        self.assertIn("message_template", schema["required"])
        
        # Verify secret fields
        self.assertIn("api_token", schema["secret"])
        
        # Verify default message template
        self.assertEqual(
            schema["properties"]["message_template"]["default"],
            ChatWork.ALERTS_DEFAULT_MESSAGE_TEMPLATE
        )

    def test_icon(self):
        self.assertEqual(ChatWork.icon(), "fa-comment")

    @patch("redash.destinations.chatwork.requests.post")
    def test_notify_with_custom_subject_and_body(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_post.return_value = mock_response
        
        chatwork = ChatWork({"api_token": "test_token", "room_id": "12345"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = "Custom Subject"
        mock_alert.custom_body = "Custom Body"
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "api_token": "test_token",
            "room_id": "12345",
            "message_template": ChatWork.ALERTS_DEFAULT_MESSAGE_TEMPLATE
        }
        
        # Execute
        chatwork.notify(
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
        
        self.assertEqual(call_args[0][0], "https://api.chatwork.com/v2/rooms/12345/messages")
        self.assertEqual(call_args[1]["headers"]["X-ChatWorkToken"], "test_token")
        self.assertEqual(call_args[1]["data"]["body"], "Custom Subject\nCustom Body")
        self.assertEqual(call_args[1]["timeout"], 5.0)

    @patch("redash.destinations.chatwork.requests.post")
    def test_notify_with_default_template(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_post.return_value = mock_response
        
        chatwork = ChatWork({"api_token": "test_token", "room_id": "12345"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "api_token": "test_token",
            "room_id": "12345",
            "message_template": ChatWork.ALERTS_DEFAULT_MESSAGE_TEMPLATE
        }
        
        # Execute
        chatwork.notify(
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
        
        expected_message = "Test Alert changed state to TRIGGERED.\nhttp://redash.example.com/alerts/1\nhttp://redash.example.com/queries/100"
        self.assertEqual(call_args[1]["data"]["body"], expected_message)

    @patch("redash.destinations.chatwork.requests.post")
    def test_notify_with_custom_subject_only(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_post.return_value = mock_response
        
        chatwork = ChatWork({"api_token": "test_token", "room_id": "12345"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = "Custom Subject"
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "api_token": "test_token",
            "room_id": "12345",
            "message_template": ChatWork.ALERTS_DEFAULT_MESSAGE_TEMPLATE
        }
        
        # Execute
        chatwork.notify(
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
        call_args = mock_post.call_args
        message = call_args[1]["data"]["body"]
        
        self.assertIn("Custom Subject", message)
        self.assertIn("Test Alert changed state to TRIGGERED", message)

    @patch("redash.destinations.chatwork.requests.post")
    @patch("redash.destinations.chatwork.logging")
    def test_notify_with_error_response(self, mock_logging, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        chatwork = ChatWork({"api_token": "test_token", "room_id": "12345"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "api_token": "test_token",
            "room_id": "12345",
            "message_template": ChatWork.ALERTS_DEFAULT_MESSAGE_TEMPLATE
        }
        
        # Execute
        chatwork.notify(
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

    @patch("redash.destinations.chatwork.requests.post")
    @patch("redash.destinations.chatwork.logging")
    def test_notify_with_exception(self, mock_logging, mock_post):
        # Setup
        mock_post.side_effect = Exception("Network error")
        
        chatwork = ChatWork({"api_token": "test_token", "room_id": "12345"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "api_token": "test_token",
            "room_id": "12345",
            "message_template": ChatWork.ALERTS_DEFAULT_MESSAGE_TEMPLATE
        }
        
        # Execute - should not raise exception
        chatwork.notify(
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
        mock_logging.exception.assert_called_with("ChatWork send ERROR.")

    @patch("redash.destinations.chatwork.requests.post")
    def test_notify_message_template_newline_replacement(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_post.return_value = mock_response
        
        chatwork = ChatWork({"api_token": "test_token", "room_id": "12345"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        # Custom template with \\n
        options = {
            "api_token": "test_token",
            "room_id": "12345",
            "message_template": "Alert: {alert_name}\\nState: {new_state}"
        }
        
        # Execute
        chatwork.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify newlines are properly replaced
        call_args = mock_post.call_args
        message = call_args[1]["data"]["body"]
        
        self.assertIn("\n", message)  # Real newline
        self.assertNotIn("\\n", message)  # Not escaped newline
        self.assertIn("Alert: Test Alert", message)
        self.assertIn("State: TRIGGERED", message)
