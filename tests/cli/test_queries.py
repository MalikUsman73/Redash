from mock import MagicMock, patch
from tests import BaseTestCase
from click.testing import CliRunner
from redash.cli.queries import rehash, add_tag, remove_tag
from sqlalchemy.orm.exc import NoResultFound


class TestCLIQueries(BaseTestCase):
    @patch("redash.models.Query")
    @patch("redash.models.db")
    def test_rehash(self, mock_db, mock_query_model):
        # Setup mocks
        mock_query1 = MagicMock()
        mock_query1.id = 1
        mock_query1.query_hash = "old_hash_1"
        mock_query1.update_query_hash = MagicMock()
        
        mock_query2 = MagicMock()
        mock_query2.id = 2
        mock_query2.query_hash = "old_hash_2"
        mock_query2.update_query_hash = MagicMock()
        
        # Simulate hash change for query 1
        def update_hash_1():
            mock_query1.query_hash = "new_hash_1"
        mock_query1.update_query_hash.side_effect = update_hash_1
        
        # No hash change for query 2
        def update_hash_2():
            mock_query2.query_hash = "old_hash_2"
        mock_query2.update_query_hash.side_effect = update_hash_2
        
        mock_query_model.query.all.return_value = [mock_query1, mock_query2]
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(rehash)
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Query 1 has changed hash", result.output)
        self.assertNotIn("Query 2 has changed hash", result.output)
        mock_db.session.add.assert_called()
        mock_db.session.commit.assert_called()

    @patch("redash.models.Query")
    @patch("redash.models.db")
    def test_add_tag_success(self, mock_db, mock_query_model):
        # Setup mock query
        mock_query = MagicMock()
        mock_query.tags = ["existing_tag"]
        mock_query_model.get_by_id.return_value = mock_query
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(add_tag, ["123", "new_tag"])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Tag added", result.output)
        self.assertIn("new_tag", mock_query.tags)
        mock_db.session.add.assert_called_with(mock_query)
        mock_db.session.commit.assert_called()

    @patch("redash.models.Query")
    @patch("redash.models.db")
    def test_add_tag_to_empty_tags(self, mock_db, mock_query_model):
        # Setup mock query with None tags
        mock_query = MagicMock()
        mock_query.tags = None
        mock_query_model.get_by_id.return_value = mock_query
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(add_tag, ["123", "first_tag"])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Tag added", result.output)
        self.assertEqual(mock_query.tags, ["first_tag"])

    @patch("redash.models.Query")
    def test_add_tag_query_not_found(self, mock_query_model):
        # Setup mock to raise NoResultFound
        mock_query_model.get_by_id.side_effect = NoResultFound()
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(add_tag, ["999", "tag"])
        
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Query not found", result.output)

    @patch("redash.models.Query")
    @patch("redash.models.db")
    def test_remove_tag_success(self, mock_db, mock_query_model):
        # Setup mock query
        mock_query = MagicMock()
        mock_query.tags = ["tag1", "tag2", "tag3"]
        mock_query_model.get_by_id.return_value = mock_query
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(remove_tag, ["123", "tag2"])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Tag removed", result.output)
        self.assertNotIn("tag2", mock_query.tags)
        mock_db.session.add.assert_called_with(mock_query)
        mock_db.session.commit.assert_called()

    @patch("redash.models.Query")
    def test_remove_tag_query_not_found(self, mock_query_model):
        # Setup mock to raise NoResultFound
        mock_query_model.get_by_id.side_effect = NoResultFound()
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(remove_tag, ["999", "tag"])
        
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Query not found", result.output)

    @patch("redash.models.Query")
    def test_remove_tag_empty_tags(self, mock_query_model):
        # Setup mock query with None tags
        mock_query = MagicMock()
        mock_query.tags = None
        mock_query_model.get_by_id.return_value = mock_query
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(remove_tag, ["123", "tag"])
        
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Tag is empty", result.output)

    @patch("redash.models.Query")
    def test_remove_tag_not_found(self, mock_query_model):
        # Setup mock query with tags that don't include the target
        mock_query = MagicMock()
        mock_query.tags = ["tag1", "tag2"]
        mock_query_model.get_by_id.return_value = mock_query
        
        # Run command
        runner = CliRunner()
        result = runner.invoke(remove_tag, ["123", "nonexistent_tag"])
        
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Tag not found", result.output)
