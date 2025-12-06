from mock import MagicMock, patch
from tests import BaseTestCase
from redash.destinations.pagerduty import PagerDuty


class TestPagerDuty(BaseTestCase):
    def test_enabled(self):
        # PagerDuty should be enabled if pypd is available
        # Since pypd is imported in the module, enabled should be True
        self.assertTrue(PagerDuty.enabled())

    def test_configuration_schema(self):
        schema = PagerDuty.configuration_schema()
        
        # Verify schema structure
        self.assertEqual(schema["type"], "object")
        self.assertIn("integration_key", schema["properties"])
        self.assertIn("description", schema["properties"])
        
        # Verify required fields
        self.assertIn("integration_key", schema["required"])
        
        # Verify secret fields
        self.assertIn("integration_key", schema["secret"])

    def test_icon(self):
        self.assertEqual(PagerDuty.icon(), "creative-commons-pd-alt")

    def test_key_string_constant(self):
        self.assertEqual(PagerDuty.KEY_STRING, "{alert_id}_{query_id}")

    def test_description_str_constant(self):
        self.assertEqual(PagerDuty.DESCRIPTION_STR, "Alert: {alert_name}")

    @patch("redash.destinations.pagerduty.pypd.EventV2.create")
    def test_notify_triggered_state(self, mock_create):
        # Setup
        mock_event = MagicMock()
        mock_create.return_value = mock_event
        
        pagerduty = PagerDuty({"integration_key": "test_key"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "integration_key": "test_integration_key"
        }
        
        # Execute
        pagerduty.notify(
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
        mock_create.assert_called_once()
        call_data = mock_create.call_args[1]["data"]
        
        self.assertEqual(call_data["routing_key"], "test_integration_key")
        self.assertEqual(call_data["incident_key"], "1_100")
        self.assertEqual(call_data["dedup_key"], "1_100")
        self.assertEqual(call_data["event_action"], "trigger")
        self.assertEqual(call_data["payload"]["summary"], "Alert: Test Alert")
        self.assertEqual(call_data["payload"]["severity"], "error")
        self.assertEqual(call_data["payload"]["source"], "redash")

    @patch("redash.destinations.pagerduty.pypd.EventV2.create")
    def test_notify_resolved_state(self, mock_create):
        # Setup
        mock_event = MagicMock()
        mock_create.return_value = mock_event
        
        pagerduty = PagerDuty({"integration_key": "test_key"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "integration_key": "test_integration_key"
        }
        
        # Execute with "ok" state (should resolve)
        pagerduty.notify(
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
        call_data = mock_create.call_args[1]["data"]
        self.assertEqual(call_data["event_action"], "resolve")

    @patch("redash.destinations.pagerduty.logging")
    @patch("redash.destinations.pagerduty.pypd.EventV2.create")
    def test_notify_unknown_state(self, mock_create, mock_logging):
        # Setup
        pagerduty = PagerDuty({"integration_key": "test_key"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "integration_key": "test_integration_key"
        }
        
        # Execute with "unknown" state
        pagerduty.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="unknown",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify - should log and return early without creating event
        mock_logging.info.assert_called_with("Unknown state, doing nothing")
        mock_create.assert_not_called()

    @patch("redash.destinations.pagerduty.pypd.EventV2.create")
    def test_notify_with_custom_subject(self, mock_create):
        # Setup
        mock_event = MagicMock()
        mock_create.return_value = mock_event
        
        pagerduty = PagerDuty({"integration_key": "test_key"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = "Custom Subject Message"
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "integration_key": "test_integration_key"
        }
        
        # Execute
        pagerduty.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify custom subject is used
        call_data = mock_create.call_args[1]["data"]
        self.assertEqual(call_data["payload"]["summary"], "Custom Subject Message")

    @patch("redash.destinations.pagerduty.pypd.EventV2.create")
    def test_notify_with_description_option(self, mock_create):
        # Setup
        mock_event = MagicMock()
        mock_create.return_value = mock_event
        
        pagerduty = PagerDuty({"integration_key": "test_key"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "integration_key": "test_integration_key",
            "description": "Custom Description from Options"
        }
        
        # Execute
        pagerduty.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify description option is used
        call_data = mock_create.call_args[1]["data"]
        self.assertEqual(call_data["payload"]["summary"], "Custom Description from Options")

    @patch("redash.destinations.pagerduty.pypd.EventV2.create")
    def test_notify_with_custom_body(self, mock_create):
        # Setup
        mock_event = MagicMock()
        mock_create.return_value = mock_event
        
        pagerduty = PagerDuty({"integration_key": "test_key"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = "Custom body with details"
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "integration_key": "test_integration_key"
        }
        
        # Execute
        pagerduty.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify custom body is added to custom_details
        call_data = mock_create.call_args[1]["data"]
        self.assertEqual(call_data["payload"]["custom_details"], "Custom body with details")

    @patch("redash.destinations.pagerduty.pypd.EventV2.create")
    def test_notify_incident_key_format(self, mock_create):
        # Setup
        mock_event = MagicMock()
        mock_create.return_value = mock_event
        
        pagerduty = PagerDuty({"integration_key": "test_key"})
        
        mock_alert = MagicMock()
        mock_alert.id = 42
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 99
        
        options = {
            "integration_key": "test_integration_key"
        }
        
        # Execute
        pagerduty.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify incident key format
        call_data = mock_create.call_args[1]["data"]
        self.assertEqual(call_data["incident_key"], "42_99")
        self.assertEqual(call_data["dedup_key"], "42_99")

    @patch("redash.destinations.pagerduty.logging")
    @patch("redash.destinations.pagerduty.pypd.EventV2.create")
    def test_notify_with_exception(self, mock_create, mock_logging):
        # Setup
        mock_create.side_effect = Exception("PagerDuty API error")
        
        pagerduty = PagerDuty({"integration_key": "test_key"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = None
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "integration_key": "test_integration_key"
        }
        
        # Execute - should not raise exception
        pagerduty.notify(
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
        mock_logging.exception.assert_called_with("PagerDuty trigger failed!")

    @patch("redash.destinations.pagerduty.pypd.EventV2.create")
    def test_notify_description_priority(self, mock_create):
        # Test that custom_subject takes priority over description option
        mock_event = MagicMock()
        mock_create.return_value = mock_event
        
        pagerduty = PagerDuty({"integration_key": "test_key"})
        
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.name = "Test Alert"
        mock_alert.custom_subject = "Custom Subject"
        mock_alert.custom_body = None
        
        mock_query = MagicMock()
        mock_query.id = 100
        
        options = {
            "integration_key": "test_integration_key",
            "description": "Description from Options"
        }
        
        # Execute
        pagerduty.notify(
            alert=mock_alert,
            query=mock_query,
            user=None,
            new_state="triggered",
            app=None,
            host="http://redash.example.com",
            metadata={},
            options=options
        )
        
        # Verify custom_subject takes priority
        call_data = mock_create.call_args[1]["data"]
        self.assertEqual(call_data["payload"]["summary"], "Custom Subject")
