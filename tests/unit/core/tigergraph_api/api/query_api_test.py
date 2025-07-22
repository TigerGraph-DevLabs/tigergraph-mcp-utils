import pytest
from unittest.mock import MagicMock
from datetime import datetime

from tigergraphx.core.tigergraph_api.api import QueryAPI, TigerGraphAPIError
from tigergraphx.config import TigerGraphConnectionConfig


class TestQueryAPI:
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
        mock_registry.get_endpoint.return_value = {
            "path": "/query/interpreted",
            "method": "POST",
            "port": "restpp_port",
        }
        return mock_registry

    @pytest.fixture
    def query_api(self, mock_config, mock_session, mock_registry):
        """Fixture for initializing QueryAPI with mocked dependencies."""
        return QueryAPI(
            config=mock_config, endpoint_registry=mock_registry, session=mock_session
        )

    # ------------------------------ _parse_query_parameters Tests ------------------------------
    def test_parse_query_parameters_basic(self, query_api):
        """Test parsing a basic query parameter dictionary."""
        params = {"name": "Alice", "age": 30}
        result = query_api._parse_query_parameters(params)
        expected = {"name": "Alice", "age": "30"}
        assert result == expected

    def test_parse_query_parameters_vertex(self, query_api):
        """Test parsing a query parameter with a single vertex (id, type)."""
        params = {"vertex": ("123", "Person")}
        result = query_api._parse_query_parameters(params)
        expected = {"vertex": "123", "vertex.type": "Person"}
        assert result == expected

    def test_parse_query_parameters_set_vertex(self, query_api):
        """Test parsing a SET<VERTEX> type parameter."""
        params = {"vertices": [("123", "Person"), ("456", "Company")]}
        result = query_api._parse_query_parameters(params)
        expected = {
            "vertices[0]": "123",
            "vertices[0].type": "Person",
            "vertices[1]": "456",
            "vertices[1].type": "Company",
        }
        assert result == expected

    def test_parse_query_parameters_list(self, query_api):
        """Test parsing a list of primitive values."""
        params = {"values": [1, 2, 3]}
        result = query_api._parse_query_parameters(params)
        expected = {"values": [1, 2, 3]}
        assert result == expected

    def test_parse_query_parameters_datetime(self, query_api):
        """Test parsing a datetime object."""
        dt = datetime(2024, 2, 5, 15, 30, 45)
        params = {"timestamp": dt}
        result = query_api._parse_query_parameters(params)
        expected = {"timestamp": "2024-02-05 15:30:45"}
        assert result == expected

    def test_parse_query_parameters_invalid_vertex(self, query_api):
        """Test parsing an invalid vertex tuple."""
        params = {"vertex": ("123", 456)}
        with pytest.raises(ValueError, match="Invalid parameter format: expected"):
            query_api._parse_query_parameters(params)

    def test_parse_query_parameters_invalid_list_vertex(self, query_api):
        """Test parsing an invalid SET<VERTEX> format."""
        params = {"vertices": [("123",)]}  # Missing type
        with pytest.raises(
            ValueError, match="Invalid parameter format in list: expected"
        ):
            query_api._parse_query_parameters(params)

    # ------------------------------ run_interpreted_query Tests ------------------------------
    def test_run_interpreted_query_success(self, query_api, mock_session):
        """Test running an interpreted query successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": False,
            "results": [{"output": "Query executed successfully"}],
        }
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response

        query = "INTERPRET QUERY(VERTEX<Entity> input) { PRINT input; }"
        result = query_api.run_interpreted_query(query)

        assert result == [{"output": "Query executed successfully"}]

    def test_run_interpreted_query_with_params(self, query_api, mock_session):
        """Test running an interpreted query with parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": False,
            "results": [{"output": "Query executed successfully"}],
        }
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session.headers = {"Content-Type": "application/json"}

        query = (
            "INTERPRET QUERY(VERTEX<Entity> input) for Graph ERGraph { PRINT input; }"
        )
        params = {"name": "Alice", "age": 30}
        result = query_api.run_interpreted_query(query, params)

        expected_params = {"name": "Alice", "age": "30"}
        mock_session.request.assert_called_once_with(
            method="POST",
            url="http://127.0.0.1:14240/query/interpreted",
            params=expected_params,
            data=query,
            json=None,
            headers=mock_session.headers,
        )
        assert result == [{"output": "Query executed successfully"}]

    def test_run_interpreted_query_tigergraph_error(self, query_api, mock_session):
        """Test handling of a TigerGraph API error response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": True,
            "message": "Syntax error in query",
        }
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.status_code = 400
        mock_session.request.return_value = mock_response

        query = "INTERPRET QUERY(VERTEX<Entity> input) for Graph ERGraph { PRINT input }"  # Missing semicolon
        with pytest.raises(
            TigerGraphAPIError, match="Syntax error in query"
        ):
            query_api.run_interpreted_query(query)
