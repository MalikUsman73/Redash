from mock import MagicMock, patch

from redash.tasks.databricks import (
    DATABRICKS_REDIS_EXPIRATION_TIME,
    get_database_tables_with_columns,
    get_databricks_databases,
    get_databricks_table_columns,
    get_databricks_tables,
)
from tests import BaseTestCase


class TestDatabricksTasks(BaseTestCase):
    def test_databricks_redis_expiration_time_constant(self):
        self.assertEqual(DATABRICKS_REDIS_EXPIRATION_TIME, 3600)

    @patch("redash.tasks.databricks.redis_connection")
    @patch("redash.tasks.databricks.models")
    def test_get_databricks_databases_success(self, mock_models, mock_redis):
        # Setup
        mock_datasource = MagicMock()
        mock_query_runner = MagicMock()
        mock_datasource.query_runner = mock_query_runner
        mock_query_runner.get_databases.return_value = ["database1", "database2", "database3"]
        mock_models.DataSource.get_by_id.return_value = mock_datasource

        # Execute
        result = get_databricks_databases(1, "test_redis_key")

        # Verify
        self.assertEqual(result, ["database1", "database2", "database3"])
        mock_models.DataSource.get_by_id.assert_called_once_with(1)
        mock_query_runner.get_databases.assert_called_once()
        mock_redis.set.assert_called_once()
        mock_redis.expire.assert_called_once_with("test_redis_key", DATABRICKS_REDIS_EXPIRATION_TIME)

    @patch("redash.tasks.databricks.redis_connection")
    @patch("redash.tasks.databricks.models")
    def test_get_databricks_databases_exception(self, mock_models, mock_redis):
        # Setup - raise exception
        mock_models.DataSource.get_by_id.side_effect = Exception("Database error")

        # Execute
        result = get_databricks_databases(1, "test_redis_key")

        # Verify error response
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], 2)
        self.assertEqual(result["error"]["message"], "Error retrieving database list.")
        mock_redis.set.assert_not_called()

    @patch("redash.tasks.databricks.redis_connection")
    @patch("redash.tasks.databricks.models")
    def test_get_database_tables_with_columns_success(self, mock_models, mock_redis):
        # Setup
        mock_datasource = MagicMock()
        mock_query_runner = MagicMock()
        mock_datasource.query_runner = mock_query_runner

        tables_data = [
            {"name": "table1", "columns": ["col1", "col2"]},
            {"name": "table2", "columns": ["col3", "col4"]}
        ]
        mock_query_runner.get_database_tables_with_columns.return_value = tables_data
        mock_models.DataSource.get_by_id.return_value = mock_datasource
        mock_redis.exists.return_value = False

        # Execute
        result = get_database_tables_with_columns(1, "test_database", "test_redis_key")

        # Verify
        self.assertIn("schema", result)
        self.assertIn("has_columns", result)
        self.assertEqual(result["schema"], tables_data)
        self.assertTrue(result["has_columns"])
        mock_query_runner.get_database_tables_with_columns.assert_called_once_with("test_database")
        mock_redis.set.assert_called_once()
        mock_redis.expire.assert_called_once_with("test_redis_key", DATABRICKS_REDIS_EXPIRATION_TIME)

    @patch("redash.tasks.databricks.redis_connection")
    @patch("redash.tasks.databricks.models")
    def test_get_database_tables_with_columns_empty_tables_redis_exists(self, mock_models, mock_redis):
        # Setup - empty tables but redis key exists
        mock_datasource = MagicMock()
        mock_query_runner = MagicMock()
        mock_datasource.query_runner = mock_query_runner
        mock_query_runner.get_database_tables_with_columns.return_value = []
        mock_models.DataSource.get_by_id.return_value = mock_datasource
        mock_redis.exists.return_value = True

        # Execute
        result = get_database_tables_with_columns(1, "test_database", "test_redis_key")

        # Verify - should still set redis because key exists
        self.assertEqual(result["schema"], [])
        self.assertTrue(result["has_columns"])
        mock_redis.set.assert_called_once()
        mock_redis.expire.assert_called_once()

    @patch("redash.tasks.databricks.redis_connection")
    @patch("redash.tasks.databricks.models")
    def test_get_database_tables_with_columns_empty_tables_no_redis(self, mock_models, mock_redis):
        # Setup - empty tables and redis key doesn't exist
        mock_datasource = MagicMock()
        mock_query_runner = MagicMock()
        mock_datasource.query_runner = mock_query_runner
        mock_query_runner.get_database_tables_with_columns.return_value = []
        mock_models.DataSource.get_by_id.return_value = mock_datasource
        mock_redis.exists.return_value = False

        # Execute
        result = get_database_tables_with_columns(1, "test_database", "test_redis_key")

        # Verify - should NOT set redis because tables are empty and key doesn't exist
        self.assertEqual(result["schema"], [])
        self.assertTrue(result["has_columns"])
        mock_redis.set.assert_not_called()
        mock_redis.expire.assert_not_called()

    @patch("redash.tasks.databricks.redis_connection")
    @patch("redash.tasks.databricks.models")
    def test_get_database_tables_with_columns_exception(self, mock_models, mock_redis):
        # Setup - raise exception
        mock_models.DataSource.get_by_id.side_effect = Exception("Schema error")

        # Execute
        result = get_database_tables_with_columns(1, "test_database", "test_redis_key")

        # Verify error response
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], 2)
        self.assertEqual(result["error"]["message"], "Error retrieving schema.")
        mock_redis.set.assert_not_called()

    @patch("redash.tasks.databricks.models")
    def test_get_databricks_tables_success(self, mock_models):
        # Setup
        mock_datasource = MagicMock()
        mock_query_runner = MagicMock()
        mock_datasource.query_runner = mock_query_runner

        tables_data = [
            {"name": "table1"},
            {"name": "table2"}
        ]
        mock_query_runner.get_database_tables_with_columns.return_value = tables_data
        mock_models.DataSource.get_by_id.return_value = mock_datasource

        # Execute
        result = get_databricks_tables(1, "test_database")

        # Verify
        self.assertIn("schema", result)
        self.assertIn("has_columns", result)
        self.assertEqual(result["schema"], tables_data)
        self.assertFalse(result["has_columns"])
        mock_query_runner.get_database_tables_with_columns.assert_called_once_with("test_database")

    @patch("redash.tasks.databricks.models")
    def test_get_databricks_tables_exception(self, mock_models):
        # Setup - raise exception
        mock_models.DataSource.get_by_id.side_effect = Exception("Tables error")

        # Execute
        result = get_databricks_tables(1, "test_database")

        # Verify error response
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], 2)
        self.assertEqual(result["error"]["message"], "Error retrieving schema.")

    @patch("redash.tasks.databricks.models")
    def test_get_databricks_table_columns_success(self, mock_models):
        # Setup
        mock_datasource = MagicMock()
        mock_query_runner = MagicMock()
        mock_datasource.query_runner = mock_query_runner

        columns_data = [
            {"name": "col1", "type": "string"},
            {"name": "col2", "type": "int"}
        ]
        mock_query_runner.get_table_columns.return_value = columns_data
        mock_models.DataSource.get_by_id.return_value = mock_datasource

        # Execute
        result = get_databricks_table_columns(1, "test_database", "test_table")

        # Verify
        self.assertEqual(result, columns_data)
        mock_query_runner.get_table_columns.assert_called_once_with("test_database", "test_table")

    @patch("redash.tasks.databricks.models")
    def test_get_databricks_table_columns_exception(self, mock_models):
        # Setup - raise exception
        mock_models.DataSource.get_by_id.side_effect = Exception("Columns error")

        # Execute
        result = get_databricks_table_columns(1, "test_database", "test_table")

        # Verify error response
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], 2)
        self.assertEqual(result["error"]["message"], "Error retrieving table columns.")
