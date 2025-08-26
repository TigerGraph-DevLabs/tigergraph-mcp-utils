import pytest
from unittest.mock import MagicMock

from tigergraphx.config import LoadingJobConfig, GraphSchema
from tigergraphx.core.managers.data_manager import DataManager


class TestDataManager:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_tigergraph_api = MagicMock()
        self.mock_tigergraph_api.gsql = MagicMock()

        mock_context = MagicMock()
        mock_context.tigergraph_api = self.mock_tigergraph_api
        mock_context.graph_schema = GraphSchema(
            graph_name="MyGraph", nodes={}, edges={}
        )
        self.data_manager = DataManager(mock_context)

    def test_load_data_success(self):
        loading_job_config = LoadingJobConfig(loading_job_name="test_job", files=[])
        # Mock the gsql return value to simulate a successful load process
        self.mock_tigergraph_api.gsql.return_value = (
            "Using graph 'MyGraph'...\n"
            "Successfully created loading jobs:\n"
            "LOAD SUCCESSFUL for loading jobid\n"
            "Successfully dropped jobs"
        )
        self.data_manager.load_data(loading_job_config)

        # Assert the gsql method was called once
        self.mock_tigergraph_api.gsql.assert_called_once()

    def test_load_data_failure(self):
        loading_job_config = LoadingJobConfig(loading_job_name="test_job", files=[])
        # Mock the gsql return value for failure
        self.mock_tigergraph_api.gsql.return_value = "LOAD FAILED"

        # Assert that RuntimeError is raised on failure
        with pytest.raises(RuntimeError):
            self.data_manager.load_data(loading_job_config)

    def test_format_none(self):
        assert DataManager._format_column_name(None) == "_"

    def test_format_int(self):
        assert DataManager._format_column_name(3) == "$3"

    def test_format_str_simple(self):
        assert DataManager._format_column_name("person") == '$"person"'

    def test_format_str_with_space(self):
        assert DataManager._format_column_name("person name") == '$"person name"'

    def test_format_function_dict(self):
        assert (
            DataManager._format_column_name({"func": "gsql_uuid_v4()"})
            == "gsql_uuid_v4()"
        )

    def test_format_function_dict_invalid_type(self):
        with pytest.raises(TypeError):
            DataManager._format_column_name({"func": 123})

    def test_format_unsupported_type(self):
        with pytest.raises(TypeError):
            DataManager._format_column_name([1, 2, 3])  # pyright: ignore
