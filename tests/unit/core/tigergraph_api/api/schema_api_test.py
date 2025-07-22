import pytest
from unittest.mock import MagicMock

from tigergraphx.core.tigergraph_api.api import SchemaAPI
from tigergraphx.config import TigerGraphConnectionConfig


class TestSchemaAPI:
    @pytest.fixture
    def mock_config(self):
        """Fixture for TigerGraphConnectionConfig with mock values."""
        return TigerGraphConnectionConfig()

    @pytest.fixture
    def mock_session(self):
        """Fixture for mocking a requests.Session object."""
        return MagicMock()

    @pytest.fixture
    def mock_registry(self):
        """Fixture for mocking an EndpointRegistry."""
        mock_registry = MagicMock()

        # Use side_effect to dynamically adjust the returned path based on input arguments
        def get_endpoint(name, version, **kwargs):
            graph_name = kwargs.get("graph", "DefaultGraph")
            return {
                "path": f"/gsql/v1/schema/graphs/{graph_name}",
                "method": "GET",
                "port": "gsql_port",
            }

        mock_registry.get_endpoint.side_effect = get_endpoint
        return mock_registry

    @pytest.fixture
    def schema_api(self, mock_config, mock_session, mock_registry):
        """Fixture for initializing SchemaAPI with mocked dependencies."""
        return SchemaAPI(
            config=mock_config, session=mock_session, endpoint_registry=mock_registry
        )

    def test_schema_api_get_schema_success(
        self, schema_api, mock_session, mock_registry
    ):
        """Test SchemaAPI get_schema success case."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": False,
            "message": "",
            "results": {"GraphName": "MyGraph", "VertexTypes": [], "EdgeTypes": []},
        }
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response

        result = schema_api.get_schema("MyGraph")

        assert result == {"GraphName": "MyGraph", "VertexTypes": [], "EdgeTypes": []}
        mock_registry.get_endpoint.assert_called_once_with(
            "get_schema", "4.x", graph_name="MyGraph"
        )
