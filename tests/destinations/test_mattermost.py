import json

from mock import MagicMock, patch

from redash.destinations.mattermost import Mattermost
from tests import BaseTestCase


class TestMattermost(BaseTestCase):
    def test_configuration_schema(self):
        schema = Mattermost.configuration_schema()

        # Verify schema structure
        self.assertEqual(schema["type"], "object")
        self.assertIn("url", schema["properties"])
        self.assertIn("username", schema["properties"])
        self.assertIn("icon_url", schema["properties"])
        self.assertIn("channel", schema["properties"])

        # Verify secret field
        self.assertEqual(schema["secret"], "url")

    def test_icon(self):
        self.assertEqual(Mattermost.icon(), "fa-bolt")

    @patch("redash.destinations.mattermost.requests.post")
    def test_notify_triggered_state(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        mattermost = Mattermost({"url": "https://mattermost.example.com/hooks/xxx"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None

        mock_query = MagicMock()
        mock_query.id = 100

        options = {
            "url": "https://mattermost.example.com/hooks/xxx"
        }

        # Execute
        mattermost.notify(
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

        self.assertEqual(call_args[0][0], "https://mattermost.example.com/hooks/xxx")

        # Parse the posted data
        posted_data = json.loads(call_args[1]["data"])

        # Verify triggered message
        self.assertIn("Test Alert just triggered", posted_data["text"])
        self.assertIn("####", posted_data["text"])

    @patch("redash.destinations.mattermost.requests.post")
    def test_notify_ok_state(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        mattermost = Mattermost({"url": "https://mattermost.example.com/hooks/xxx"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None

        mock_query = MagicMock()

        options = {
            "url": "https://mattermost.example.com/hooks/xxx"
        }

        # Execute
        mattermost.notify(
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
        self.assertIn("Test Alert went back to normal", posted_data["text"])
        self.assertIn("####", posted_data["text"])

    @patch("redash.destinations.mattermost.requests.post")
    def test_notify_with_custom_subject(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        mattermost = Mattermost({"url": "https://mattermost.example.com/hooks/xxx"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = "Custom Subject Message"
        mock_alert.custom_body = None

        mock_query = MagicMock()

        options = {
            "url": "https://mattermost.example.com/hooks/xxx"
        }

        # Execute
        mattermost.notify(
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

        # Verify custom subject is used
        self.assertEqual(posted_data["text"], "Custom Subject Message")

    @patch("redash.destinations.mattermost.requests.post")
    def test_notify_with_custom_body(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        mattermost = Mattermost({"url": "https://mattermost.example.com/hooks/xxx"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = "Custom body content with details"

        mock_query = MagicMock()

        options = {
            "url": "https://mattermost.example.com/hooks/xxx"
        }

        # Execute
        mattermost.notify(
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

        # Verify attachments with custom body
        self.assertIn("attachments", posted_data)
        self.assertEqual(len(posted_data["attachments"]), 1)
        self.assertEqual(posted_data["attachments"][0]["fields"][0]["title"], "Description")
        self.assertEqual(posted_data["attachments"][0]["fields"][0]["value"], "Custom body content with details")

    @patch("redash.destinations.mattermost.requests.post")
    def test_notify_with_username(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        mattermost = Mattermost({"url": "https://mattermost.example.com/hooks/xxx"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None

        mock_query = MagicMock()

        options = {
            "url": "https://mattermost.example.com/hooks/xxx",
            "username": "Redash Bot"
        }

        # Execute
        mattermost.notify(
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

        # Verify username is set
        self.assertEqual(posted_data["username"], "Redash Bot")

    @patch("redash.destinations.mattermost.requests.post")
    def test_notify_with_icon_url(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        mattermost = Mattermost({"url": "https://mattermost.example.com/hooks/xxx"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None

        mock_query = MagicMock()

        options = {
            "url": "https://mattermost.example.com/hooks/xxx",
            "icon_url": "https://example.com/icon.png"
        }

        # Execute
        mattermost.notify(
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

        # Verify icon_url is set
        self.assertEqual(posted_data["icon_url"], "https://example.com/icon.png")

    @patch("redash.destinations.mattermost.requests.post")
    def test_notify_with_channel(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        mattermost = Mattermost({"url": "https://mattermost.example.com/hooks/xxx"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None

        mock_query = MagicMock()

        options = {
            "url": "https://mattermost.example.com/hooks/xxx",
            "channel": "#alerts"
        }

        # Execute
        mattermost.notify(
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

        # Verify channel is set
        self.assertEqual(posted_data["channel"], "#alerts")

    @patch("redash.destinations.mattermost.requests.post")
    def test_notify_with_all_options(self, mock_post):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        mattermost = Mattermost({"url": "https://mattermost.example.com/hooks/xxx"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = "Custom Subject"
        mock_alert.custom_body = "Custom Body"

        mock_query = MagicMock()

        options = {
            "url": "https://mattermost.example.com/hooks/xxx",
            "username": "Redash Bot",
            "icon_url": "https://example.com/icon.png",
            "channel": "#alerts"
        }

        # Execute
        mattermost.notify(
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

        # Verify all options are set
        self.assertEqual(posted_data["text"], "Custom Subject")
        self.assertEqual(posted_data["username"], "Redash Bot")
        self.assertEqual(posted_data["icon_url"], "https://example.com/icon.png")
        self.assertEqual(posted_data["channel"], "#alerts")
        self.assertIn("attachments", posted_data)

    @patch("redash.destinations.mattermost.logging")
    @patch("redash.destinations.mattermost.requests.post")
    def test_notify_with_error_response(self, mock_post, mock_logging):
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        mattermost = Mattermost({"url": "https://mattermost.example.com/hooks/xxx"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None

        mock_query = MagicMock()

        options = {
            "url": "https://mattermost.example.com/hooks/xxx"
        }

        # Execute
        mattermost.notify(
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

    @patch("redash.destinations.mattermost.logging")
    @patch("redash.destinations.mattermost.requests.post")
    def test_notify_with_exception(self, mock_post, mock_logging):
        # Setup
        mock_post.side_effect = Exception("Network error")

        mattermost = Mattermost({"url": "https://mattermost.example.com/hooks/xxx"})

        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None

        mock_query = MagicMock()

        options = {
            "url": "https://mattermost.example.com/hooks/xxx"
        }

        # Execute - should not raise exception
        mattermost.notify(
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
        mock_logging.exception.assert_called_with("Mattermost webhook send ERROR.")
