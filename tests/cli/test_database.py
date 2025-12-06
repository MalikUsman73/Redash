from click.testing import CliRunner
from mock import MagicMock, patch

from redash.cli.database import create_tables, drop_tables, is_db_empty
from tests import BaseTestCase


class TestCLIDatabase(BaseTestCase):
    @patch("redash.models.db")
    @patch("redash.cli.database.sqlalchemy.inspect")
    def test_is_db_empty(self, mock_inspect, mock_db):
        # Scenario 1: DB is empty
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.get_table_names.return_value = []

        self.assertTrue(is_db_empty())

        # Scenario 2: DB is not empty
        mock_inspector.get_table_names.return_value = ["users"]
        self.assertFalse(is_db_empty())

    @patch("redash.models.db")
    @patch("redash.cli.database._wait_for_db_connection")
    @patch("redash.cli.database.is_db_empty")
    @patch("redash.cli.database.stamp")
    @patch("redash.cli.database.load_extensions")
    def test_create_tables(self, mock_load_extensions, mock_stamp, mock_is_empty, mock_wait, mock_db):
        # Setup: DB is empty
        mock_is_empty.return_value = True

        runner = CliRunner()
        result = runner.invoke(create_tables)

        self.assertEqual(result.exit_code, 0)
        mock_wait.assert_called()
        mock_load_extensions.assert_called()
        mock_db.create_all.assert_called()
        mock_stamp.assert_called()

    @patch("redash.models.db")
    @patch("redash.cli.database._wait_for_db_connection")
    @patch("redash.cli.database.is_db_empty")
    def test_create_tables_not_empty(self, mock_is_empty, mock_wait, mock_db):
        # Setup: DB is NOT empty
        mock_is_empty.return_value = False

        runner = CliRunner()
        result = runner.invoke(create_tables)

        self.assertEqual(result.exit_code, 0)
        mock_wait.assert_called()
        # Should NOT call create_all or load_extensions
        mock_db.create_all.assert_not_called()

    @patch("redash.models.db")
    @patch("redash.cli.database._wait_for_db_connection")
    def test_drop_tables(self, mock_wait, mock_db):
        runner = CliRunner()
        result = runner.invoke(drop_tables)

        self.assertEqual(result.exit_code, 0)
        mock_wait.assert_called()
        mock_db.drop_all.assert_called()

    @patch("redash.models.db")
    @patch("redash.cli.database._wait_for_db_connection")
    @patch("redash.cli.database.sqlalchemy.Table")
    @patch("redash.cli.database.EncryptedConfiguration")
    @patch("redash.cli.database.ConfigurationContainer")
    def test_reencrypt(self, mock_container, mock_encrypted_config, mock_table, mock_wait, mock_db):
        from redash.cli.database import reencrypt

        # Setup mocks
        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter(
            [
                {"id": 1, "encrypted_options": "old_encrypted_data"},
                {"id": 2, "encrypted_options": "old_encrypted_data_2"},
            ]
        )
        mock_db.session.execute.return_value = mock_result

        # We need mock_table to return a mock that has an update() method
        mock_table_instance = MagicMock()
        mock_table.return_value = mock_table_instance
        mock_update = mock_table_instance.update.return_value
        mock_update.where.return_value.values.return_value = "update_stmt"

        # Run reencrypt
        runner = CliRunner()
        result = runner.invoke(reencrypt, ["old_secret", "new_secret"], catch_exceptions=False)

        self.assertEqual(result.exit_code, 0)

        # Verification
        mock_wait.assert_called()
        mock_container.as_mutable.assert_called()
        mock_encrypted_config.assert_called()
        # Should start transaction/execute select/update/commit
        self.assertTrue(mock_db.session.execute.called)
        self.assertTrue(mock_db.session.commit.called)

        # Check if update was called for each item
        self.assertEqual(mock_db.session.execute.call_count, 2 + 2)  # 2 items + 2 updates
