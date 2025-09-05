# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

from typing import Any, Dict, List, Literal, Optional
from pathlib import Path
from requests import Session
from requests.auth import AuthBase, HTTPBasicAuth

from .endpoint_handler.endpoint_registry import EndpointRegistry
from .api import (
    AdminAPI,
    GSQLAPI,
    SecurityAPI,
    SchemaAPI,
    DataSourceAPI,
    NodeAPI,
    EdgeAPI,
    QueryAPI,
    UpsertAPI,
)
from .api.data_source_api import DataSourceType

from tigergraphx.config import TigerGraphConnectionConfig


class BearerAuth(AuthBase):
    """Custom authentication class for handling Bearer tokens."""

    def __init__(self, token):
        """
        Initialize with a bearer token.

        Args:
            token: Bearer token string.
        """
        self.token = token

    def __call__(self, r):
        """
        Add Authorization header to the request.

        Args:
            r: Request object.

        Returns:
            Modified request object with Authorization header.
        """
        r.headers["Authorization"] = f"Bearer {self.token}"
        return r


class TigerGraphAPI:
    def __init__(
        self,
        config: Optional[TigerGraphConnectionConfig | Dict | str | Path] = None,
    ):
        """
        Initialize TigerGraphAPI with a connection configuration.

        Args:
            config: Configuration object for TigerGraph connection.
        """
        # Create a TigerGraph connection
        if config is None:  # Set default options
            config = TigerGraphConnectionConfig()
        else:
            config = TigerGraphConnectionConfig.ensure_config(config)
        self.config = config

        # Initialize the EndpointRegistry
        self.endpoint_registry = EndpointRegistry(config=self.config)

        # Create a shared session
        self.session = self._initialize_session()

        # Get the version of TigerGraph
        self.full_version, self.version = self._fetch_and_validate_version()

        if self.version != "4.x":
            raise ValueError(
                f"Only TigerGraph 4.x is supported, but found {self.full_version}."
            )

        # Initialize API classes
        self._admin_api = AdminAPI(
            self.config, self.endpoint_registry, self.session, self.version
        )
        self._gsql_api = GSQLAPI(
            self.config, self.endpoint_registry, self.session, self.version
        )
        self._security_api = SecurityAPI(
            self.config, self.endpoint_registry, self.session, self.version
        )
        self._data_source_api = DataSourceAPI(
            self.config, self.endpoint_registry, self.session, self.version
        )
        self._schema_api = SchemaAPI(
            self.config, self.endpoint_registry, self.session, self.version
        )
        self._node_api = NodeAPI(
            self.config, self.endpoint_registry, self.session, self.version
        )
        self._edge_api = EdgeAPI(
            self.config, self.endpoint_registry, self.session, self.version
        )
        self._query_api = QueryAPI(
            self.config, self.endpoint_registry, self.session, self.version
        )
        self._upsert_api = UpsertAPI(
            self.config, self.endpoint_registry, self.session, self.version
        )

    # ------------------------------ Admin ------------------------------
    def ping(self) -> str:
        """
        Ping the TigerGraph server and return its response.

        Returns:
            Response string from the server.
        """
        return self._admin_api.ping()

    def get_version(self) -> str:
        """
        Get the version string of the connected TigerGraph instance.

        Returns:
            Version string from the TigerGraph server.
        """
        return self._admin_api.get_version()

    # ------------------------------ GSQL ------------------------------
    def gsql(self, command: str) -> str:
        """
        Run a raw GSQL command and return the response.

        Args:
            command: GSQL command string.

        Returns:
            Response string from the GSQL server.
        """
        return self._gsql_api.gsql(command)

    # ------------------------------ Security ------------------------------
    def create_token(
        self,
        secret_alias: str,
        graph_name: Optional[str] = None,
        lifetime_seconds: Optional[int] = None,
    ) -> str:
        """Create an auth token using a secret.

        Args:
            secret_alias: The secret alias to use for token generation.
            graph_name: The name of the graph to scope the token.
            lifetime_seconds: Duration in seconds before the token expires.

        Returns:
            The generated authentication token as a string.
        """
        return self._security_api.create_token(secret_alias, graph_name, lifetime_seconds)

    def drop_token(
        self,
        token: str,
    ) -> str:
        """Drop an authentication token.

        Args:
            token: The token to be revoked.

        Returns:
            The response message from the server.
        """
        return self._security_api.drop_token(token)

    # ------------------------------ Data Source ------------------------------
    def create_data_source(
        self,
        name: str,
        data_source_type: str | DataSourceType,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        extra_config: Optional[Dict[str, Any]] = None,
        graph_name: Optional[str] = None,
    ) -> str:
        """
        Create a new data source configuration.

        Args:
            name: Name of the data source.
            data_source_type: Type of the source (e.g., s3, gcs, abs).
            access_key: Optional access key for cloud storage.
            secret_key: Optional secret key for cloud storage.
            extra_config: Additional configuration values to merge into the request payload.
            graph_name: Optional graph name.

        Returns:
            API response message.
        """
        return self._data_source_api.create_data_source(
            name=name,
            data_source_type=data_source_type,
            access_key=access_key,
            secret_key=secret_key,
            extra_config=extra_config,
            graph_name=graph_name,
        )

    def update_data_source(
        self,
        name: str,
        data_source_type: str | DataSourceType,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        extra_config: Optional[Dict[str, Any]] = None,
        graph_name: Optional[str] = None,
    ) -> str:
        """
        Update an existing data source configuration.

        Args:
            name: Name of the data source.
            data_source_type: Type of the source (e.g., s3, gcs, abs).
            access_key: Optional access key.
            secret_key: Optional secret key.
            extra_config: Extra config values to merge in.
            graph_name: Optional graph name.

        Returns:
            API response message.
        """
        return self._data_source_api.update_data_source(
            name=name,
            data_source_type=data_source_type,
            access_key=access_key,
            secret_key=secret_key,
            extra_config=extra_config,
            graph_name=graph_name,
        )

    def get_data_source(self, name: str) -> Dict[str, Any]:
        """
        Get a data source's configuration.

        Args:
            name: Name of the data source.

        Returns:
            A dictionary with data source configuration.
        """
        return self._data_source_api.get_data_source(name=name)

    def drop_data_source(self, name: str, graph_name: Optional[str] = None) -> str:
        """
        Drop a data source by name. Can specify a graph if removing from a graph-specific context.

        Args:
            name: Name of the data source to remove.
            graph_name: Optional graph name, required if the data source is local.

        Returns:
            API response message.
        """
        return self._data_source_api.drop_data_source(name=name, graph_name=graph_name)

    def get_all_data_sources(
        self, graph_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve a list of all data sources, optionally filtered by graph name.

        Args:
            graph_name: Optional graph name.

        Returns:
            List of data source dictionaries.
        """
        return self._data_source_api.get_all_data_sources(graph_name=graph_name)

    def drop_all_data_sources(self, graph_name: Optional[str] = None) -> str:
        """
        Drop all data source configurations, optionally within a specific graph.

        Args:
            graph_name: Optional graph name.

        Returns:
            API response message.
        """
        return self._data_source_api.drop_all_data_sources(graph_name=graph_name)

    def preview_sample_data(
        self,
        path: str,
        data_source_type: Optional[str | DataSourceType] = None,
        data_source: Optional[str] = None,
        data_format: Optional[Literal["csv", "json"]] = "csv",
        size: Optional[int] = 10,
        has_header: bool = True,
        separator: Optional[str] = ",",
        eol: Optional[str] = "\\n",
        quote: Optional[Literal["'", '"']] = '"',
    ) -> Dict[str, Any]:
        """
        Preview sample data from a file path.

        Args:
            path: The full file path or URI to preview data from.
            data_source_type: The source type, e.g., 's3', 'gcs', 'abs', etc.
            data_source: Optional named data source configuration.
            data_format: Format of the file, either 'csv' or 'json'.
            size: Number of rows to preview.
            has_header: Whether the file contains a header row.
            separator: Field separator used in the file.
            eol: End-of-line character.
            quote: Optional quote character used in the file.

        Returns:
            A dictionary containing the previewed sample data.
        """
        return self._data_source_api.preview_sample_data(
            path=path,
            data_source_type=data_source_type,
            data_source=data_source,
            data_format=data_format,
            size=size,
            has_header=has_header,
            separator=separator,
            eol=eol,
            quote=quote,
        )

    # ------------------------------ Schema ------------------------------
    def get_schema(self, graph_name: str) -> Dict:
        """
        Retrieve the schema of a graph.

        Args:
            graph_name: The name of the graph.

        Returns:
            The schema as JSON.
        """
        return self._schema_api.get_schema(graph_name)

    # ------------------------------ Node ------------------------------
    def retrieve_a_node(self, graph_name: str, node_type: str, node_id: str) -> List:
        """
        Retrieve a single node from the graph.

        Args:
            graph_name: The name of the graph.
            node_type: The type of the node.
            node_id: The ID of the node.

        Returns:
            A list containing the node data.
        """
        return self._node_api.retrieve_a_node(graph_name, node_type, node_id)

    def delete_a_node(self, graph_name: str, node_type: str, node_id: str) -> Dict:
        """
        Delete a single node from the graph.

        Args:
            graph_name: The name of the graph.
            node_type: The type of the node.
            node_id: The ID of the node.

        Returns:
            API response as a dictionary.
        """
        return self._node_api.delete_a_node(graph_name, node_type, node_id)

    def delete_nodes(self, graph_name: str, node_type: str) -> Dict:
        """
        Delete all nodes of a given type from the graph.

        Args:
            graph_name: The name of the graph.
            node_type: The type of nodes to delete.

        Returns:
            API response as a dictionary.
        """
        return self._node_api.delete_nodes(graph_name, node_type)

    # ------------------------------ Edge ------------------------------
    def retrieve_a_edge(
        self,
        graph_name: str,
        source_node_type: str,
        source_node_id: str,
        edge_type: str,
        target_node_type: str,
        target_node_id: str,
    ) -> List:
        """
        Retrieve a specific edge between two nodes.

        Args:
            graph_name: The name of the graph.
            source_node_type: Type of the source node.
            source_node_id: ID of the source node.
            edge_type: Type of the edge.
            target_node_type: Type of the target node.
            target_node_id: ID of the target node.

        Returns:
            A list containing the edge data.
        """
        return self._edge_api.retrieve_a_edge(
            graph_name=graph_name,
            source_node_type=source_node_type,
            source_node_id=source_node_id,
            edge_type=edge_type,
            target_node_type=target_node_type,
            target_node_id=target_node_id,
        )

    # ------------------------------ Query ------------------------------
    def create_query(self, graph_name: str, gsql_query: str) -> str:
        """
        Create a new GSQL query.

        Args:
            graph_name: The name of the graph.
            gsql_query: The full GSQL query text.

        Returns:
            API response as a string.
        """
        return self._query_api.create_query(graph_name, gsql_query)

    def install_query(self, graph_name: str, query_names: str | List[str]) -> str:
        """
        Install one or more GSQL queries.

        Args:
            graph_name: The name of the graph.
            query_names: Query name or list of query names to install.

        Returns:
            API response as a string.
        """
        return self._query_api.install_query(graph_name, query_names)

    def drop_query(self, graph_name: str, query_name: str) -> Dict:
        """
        Drop a GSQL query from the graph.

        Args:
            graph_name: The name of the graph.
            query_name: The name of the query to drop.

        Returns:
            API response as a dictionary.
        """
        return self._query_api.drop_query(graph_name, query_name)

    def run_interpreted_query(
        self, gsql_query: str, params: Optional[Dict[str, Any]] = None
    ) -> List:
        """
        Execute a GSQL interpreted query.

        Args:
            gsql_query: The GSQL query to run.
            params: Optional parameters for the query.

        Returns:
            Query result as a list.
        """
        return self._query_api.run_interpreted_query(gsql_query, params)

    def run_installed_query_get(
        self, graph_name: str, query_name: str, params: Optional[Dict[str, Any]] = None
    ) -> List:
        """
        Run an installed query using HTTP GET.

        Args:
            graph_name: The name of the graph.
            query_name: The name of the installed query.
            params: Optional parameters for the query.

        Returns:
            Query result as a list.
        """
        return self._query_api.run_installed_query_get(graph_name, query_name, params)

    def run_installed_query_post(
        self, graph_name: str, query_name: str, params: Optional[Dict[str, Any]] = None
    ) -> List:
        """
        Run an installed query using HTTP POST.

        Args:
            graph_name: The name of the graph.
            query_name: The name of the installed query.
            params: Optional parameters for the query.

        Returns:
            Query result as a list.
        """
        return self._query_api.run_installed_query_post(graph_name, query_name, params)

    def get_query_info(self, graph_name: str) -> List:
        """
        Retrieve information about all queries for a given graph.

        This includes query code, endpoints, parameters, and status.

        Args:
            graph_name: The name of the graph.

        Returns:
            API response as a list.
        """
        return self._query_api.get_query_info(graph_name)

    # ------------------------------ Upsert ------------------------------
    def upsert_graph_data(self, graph_name: str, payload: Dict[str, Any]) -> List:
        """
        Upsert nodes and edges into the graph.

        Args:
            graph_name: The name of the graph.
            payload: Dictionary containing nodes and edges.

        Returns:
            API response as a list.
        """
        return self._upsert_api.upsert_graph_data(graph_name, payload)

    def _initialize_session(self) -> Session:
        """
        Create a shared requests.Session with retries and default headers.

        Returns:
            A configured session object.
        """
        session = Session()

        # Set authentication
        session.auth = self._get_auth()
        return session

    def _get_auth(self):
        """
        Generate authentication object for the session.

        Returns:
            HTTPBasicAuth for username/password, BearerAuth for tokens, or None.
        """
        if self.config.secret:
            return HTTPBasicAuth("__GSQL__secret", self.config.secret)
        elif self.config.username and self.config.password:
            return HTTPBasicAuth(self.config.username, self.config.password)
        elif self.config.token:
            return BearerAuth(self.config.token)  # Use custom class for Bearer token
        return None  # No authentication needed

    def _fetch_and_validate_version(self) -> tuple[str, Literal["3.x", "4.x"]]:
        """
        Retrieve TigerGraph version and determine major version group.

        Returns:
            A tuple of (full_version, major_version_literal).

        Raises:
            ValueError: If the version is not supported.
        """
        admin_api = AdminAPI(self.config, self.endpoint_registry, self.session, "4.x")
        full_version = admin_api.get_version()

        if full_version.startswith("4."):
            return full_version, "4.x"
        elif full_version.startswith("3."):
            return full_version, "3.x"
        else:
            raise ValueError(
                f"Unsupported TigerGraph version: {full_version}. "
                f"Only 3.x and 4.x are supported."
            )
