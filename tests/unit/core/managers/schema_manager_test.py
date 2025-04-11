import pytest
from unittest.mock import MagicMock
from tigergraphx.core.managers.schema_manager import SchemaManager
from tigergraphx.config import GraphSchema


class TestSchemaManager:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_tigergraph_api = MagicMock()
        self.mock_tigergraph_api.gsql = MagicMock()

        mock_context = MagicMock()
        mock_context.tigergraph_api = self.mock_tigergraph_api
        mock_context.graph_schema = GraphSchema(
            graph_name="TestGraph", nodes={}, edges={}
        )
        self.schema_manager = SchemaManager(mock_context)

    def test_create_schema_success(self):
        # Mock the gsql method to simulate successful schema creation
        self.mock_tigergraph_api.gsql.return_value = """
The graph TestGraph is created
Successfully created schema change jobs
Local schema change succeeded
Successfully dropped jobs
"""
        self.schema_manager.create_schema(drop_existing_graph=False)
        self.mock_tigergraph_api.gsql.assert_called()

    def test_create_schema_with_drop(self):
        # Mock the gsql method to simulate dropping the graph
        self.mock_tigergraph_api.gsql.side_effect = [
            "Graph dropped successfully",  # First call for dropping
            """
The graph TestGraph is created
Successfully created schema change jobs
Local schema change succeeded
Successfully dropped jobs
""",  # Second call for creating
        ]
        self.schema_manager.create_schema(drop_existing_graph=True)
        assert self.mock_tigergraph_api.gsql.call_count == 2

    def test_create_schema_failure(self):
        # Mock the gsql method to simulate a failure in schema creation
        self.mock_tigergraph_api.gsql.return_value = "Failed to create schema change jobs"
        with pytest.raises(RuntimeError):
            self.schema_manager.create_schema(drop_existing_graph=False)
