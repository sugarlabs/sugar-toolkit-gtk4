# NOTE: DATA was mocked and actualy d bus testing would be nicer.
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sugar4.datastore import datastore
from sugar4.datastore.datastore import DSObject, DSMetadata, RawObject


class TestDSMetadata(unittest.TestCase):
    """Test cases for DSMetadata class."""

    def test_metadata_creation_empty(self):
        """Test creating empty metadata."""
        metadata = DSMetadata()
        self.assertIn("activity", metadata)
        self.assertIn("activity_id", metadata)
        self.assertIn("mime_type", metadata)
        self.assertIn("title_set_by_user", metadata)

    def test_metadata_creation_with_properties(self):
        """Test creating metadata with properties."""
        props = {"title": "Test Title", "custom_field": "value"}
        metadata = DSMetadata(props)
        self.assertEqual(metadata["title"], "Test Title")
        self.assertEqual(metadata["custom_field"], "value")

    def test_metadata_getitem_setitem(self):
        """Test getting and setting metadata items."""
        metadata = DSMetadata()
        metadata["title"] = "New Title"
        self.assertEqual(metadata["title"], "New Title")

    def test_metadata_contains(self):
        """Test membership testing."""
        metadata = DSMetadata({"title": "Test"})
        self.assertIn("title", metadata)
        self.assertNotIn("nonexistent", metadata)

    def test_metadata_keys(self):
        """Test getting keys."""
        metadata = DSMetadata({"title": "Test", "author": "Me"})
        keys = metadata.keys()
        self.assertIn("title", keys)
        self.assertIn("author", keys)

    def test_metadata_get(self):
        """Test get method."""
        metadata = DSMetadata({"title": "Test"})
        self.assertEqual(metadata.get("title"), "Test")
        self.assertEqual(metadata.get("nonexistent", "default"), "default")

    def test_metadata_copy(self):
        """Test copying metadata."""
        metadata = DSMetadata({"title": "Test"})
        copy = metadata.copy()
        self.assertEqual(copy["title"], "Test")
        self.assertIsNot(copy, metadata)

    def test_metadata_update(self):
        """Test updating metadata."""
        metadata = DSMetadata()
        metadata.update({"title": "Updated", "author": "Author"})
        self.assertEqual(metadata["title"], "Updated")
        self.assertEqual(metadata["author"], "Author")


class TestDSObject(unittest.TestCase):
    """Test cases for DSObject class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_metadata = DSMetadata({"title": "Test Object"})

    @patch("sugar4.datastore.datastore._get_data_store")
    def test_dsobject_creation(self, mock_get_ds):
        """Test DSObject creation."""
        # Mock the data store to avoid D-Bus connection
        mock_ds = Mock()
        mock_ds.connect_to_signal.return_value = Mock()  # Mock signal connection
        mock_get_ds.return_value = mock_ds

        obj = DSObject("test_id", self.mock_metadata, "/test/path")
        self.assertEqual(obj.object_id, "test_id")
        self.assertEqual(obj.metadata, self.mock_metadata)
        self.assertEqual(obj.file_path, "/test/path")

    @patch("sugar4.datastore.datastore._get_data_store")
    def test_dsobject_object_id_property(self, mock_get_ds):
        """Test object_id property."""
        # Mock the data store to avoid D-Bus connection
        mock_ds = Mock()
        mock_ds.connect_to_signal.return_value = Mock()
        mock_get_ds.return_value = mock_ds

        obj = DSObject(None)
        obj.object_id = "new_id"
        self.assertEqual(obj.object_id, "new_id")

    @patch("sugar4.datastore.datastore._get_data_store")
    def test_dsobject_get_metadata_lazy(self, mock_get_ds):
        """Test lazy loading of metadata."""
        mock_ds = Mock()
        mock_ds.get_properties.return_value = {"title": "Lazy Title"}
        mock_ds.connect_to_signal.return_value = Mock()
        mock_get_ds.return_value = mock_ds

        obj = DSObject("test_id")
        metadata = obj.metadata

        self.assertIsInstance(metadata, DSMetadata)
        self.assertEqual(metadata["title"], "Lazy Title")

    @patch("sugar4.datastore.datastore._get_data_store")
    def test_dsobject_get_file_path_lazy(self, mock_get_ds):
        """Test lazy loading of file path."""
        mock_ds = Mock()
        mock_ds.get_filename.return_value = "/lazy/path"
        mock_ds.connect_to_signal.return_value = Mock()
        mock_get_ds.return_value = mock_ds

        obj = DSObject("test_id")
        file_path = obj.file_path

        self.assertEqual(file_path, "/lazy/path")

    @patch("sugar4.datastore.datastore._get_data_store")
    def test_dsobject_copy(self, mock_get_ds):
        """Test copying DSObject."""
        mock_ds = Mock()
        mock_ds.connect_to_signal.return_value = Mock()
        mock_get_ds.return_value = mock_ds

        obj = DSObject("test_id", self.mock_metadata, "/test/path")
        copy = obj.copy()

        self.assertIsNone(copy.object_id)
        self.assertEqual(copy.file_path, "/test/path")
        self.assertIsNot(copy.metadata, obj.metadata)

    @patch("os.path.isfile")
    @patch("os.remove")
    @patch("sugar4.datastore.datastore._get_data_store")
    def test_dsobject_destroy(self, mock_get_ds, mock_remove, mock_isfile):
        """Test destroying DSObject."""
        mock_ds = Mock()
        mock_signal_match = Mock()
        mock_ds.connect_to_signal.return_value = mock_signal_match
        mock_get_ds.return_value = mock_ds
        mock_isfile.return_value = True

        obj = DSObject("test_id", self.mock_metadata, "/test/path")
        obj.set_owns_file(True)
        obj.destroy()

        self.assertTrue(obj.is_destroyed())
        mock_remove.assert_called_once_with("/test/path")


class TestRawObject(unittest.TestCase):
    """Test cases for RawObject class."""

    @patch("os.stat")
    @patch("sugar4.profile.get_color")
    def test_rawobject_creation(self, mock_get_color, mock_stat):
        """Test RawObject creation."""
        mock_stat.return_value = Mock(st_mtime=1234567890)
        mock_color = Mock()
        mock_color.to_string.return_value = "#FF0000,#00FF00"
        mock_get_color.return_value = mock_color

        obj = RawObject("/test/file.txt")

        self.assertEqual(obj.object_id, "/test/file.txt")
        self.assertEqual(obj.metadata["title"], "file.txt")
        self.assertEqual(obj.metadata["timestamp"], 1234567890)

    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("os.symlink")
    @patch("tempfile.mktemp")
    @patch("sugar4.env.get_profile_path")
    def test_rawobject_get_file_path(
        self, mock_get_profile, mock_mktemp, mock_symlink, mock_makedirs, mock_exists
    ):
        """Test RawObject file path creation."""
        mock_get_profile.return_value = "/profile"
        mock_mktemp.return_value = "/profile/data/tempfile"
        mock_exists.return_value = True

        with patch("os.stat"):
            with patch("sugar4.profile.get_color"):
                obj = RawObject("/test/file.txt")
                file_path = obj.file_path

                self.assertEqual(file_path, "/profile/data/tempfile")
                mock_symlink.assert_called_once_with(
                    "/test/file.txt", "/profile/data/tempfile"
                )


class TestDatastoreFunctions(unittest.TestCase):
    """Test cases for datastore module functions."""

    @patch("sugar4.datastore.datastore._get_data_store")
    def test_get_function(self, mock_get_ds):
        """Test get function."""
        mock_ds = Mock()
        mock_ds.get_properties.return_value = {"title": "Test Object"}
        mock_ds.connect_to_signal.return_value = Mock()
        mock_get_ds.return_value = mock_ds

        obj = datastore.get("test_id")

        self.assertIsInstance(obj, DSObject)
        self.assertEqual(obj.object_id, "test_id")

    def test_get_function_raw_object(self):
        """Test get function with file path."""
        with patch("os.stat"):
            with patch("sugar4.profile.get_color"):
                obj = datastore.get("/test/file.txt")
                self.assertIsInstance(obj, RawObject)

    def test_create_function(self):
        """Test create function."""
        obj = datastore.create()
        self.assertIsInstance(obj, DSObject)
        self.assertIsNone(obj.object_id)
        self.assertIsInstance(obj.metadata, DSMetadata)

    @patch("sugar4.datastore.datastore._get_data_store")
    def test_delete_function(self, mock_get_ds):
        """Test delete function."""
        mock_ds = Mock()
        mock_get_ds.return_value = mock_ds

        datastore.delete("test_id")

        mock_ds.delete.assert_called_once_with("test_id")

    @patch("sugar4.datastore.datastore._get_data_store")
    def test_find_function(self, mock_get_ds):
        """Test find function."""
        mock_ds = Mock()
        mock_ds.find.return_value = ([{"uid": "obj1", "title": "Object 1"}], 1)
        mock_get_ds.return_value = mock_ds

        objects, count = datastore.find({"title": "Object 1"})

        self.assertEqual(count, 1)
        self.assertEqual(len(objects), 1)
        self.assertIsInstance(objects[0], DSObject)

    @patch("sugar4.datastore.datastore._get_data_store")
    @patch("sugar4.datastore.datastore.write")
    def test_copy_function(self, mock_write, mock_get_ds):
        """Test copy function."""
        mock_ds = Mock()
        mock_ds.connect_to_signal.return_value = Mock()
        mock_get_ds.return_value = mock_ds

        original_obj = DSObject("original_id", DSMetadata({"title": "Original"}))
        new_obj = datastore.copy(original_obj, "/mount/point")

        self.assertEqual(new_obj.metadata["mountpoint"], "/mount/point")
        mock_write.assert_called_once()


class TestDatastoreSignals(unittest.TestCase):
    """Test cases for datastore signals."""

    @patch("sugar4.datastore.datastore._get_data_store")
    def test_signal_callbacks(self, mock_get_ds):
        """Test datastore signal callbacks."""
        mock_ds = Mock()
        mock_ds.get_properties.return_value = {"title": "Test"}
        mock_ds.connect_to_signal.return_value = Mock()
        mock_get_ds.return_value = mock_ds

        with patch("sugar4.datastore.datastore.created") as mock_created:
            datastore._datastore_created_cb("test_id")
            mock_created.send.assert_called_once()

        with patch("sugar4.datastore.datastore.updated") as mock_updated:
            datastore._datastore_updated_cb("test_id")
            mock_updated.send.assert_called_once()

        with patch("sugar4.datastore.datastore.deleted") as mock_deleted:
            datastore._datastore_deleted_cb("test_id")
            mock_deleted.send.assert_called_once()
            mock_deleted.send.assert_called_once_with(None, object_id="test_id")


if __name__ == "__main__":
    unittest.main()
