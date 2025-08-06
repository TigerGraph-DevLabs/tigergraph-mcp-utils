# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

import logging
from typing import Any, Dict, Optional, List, Literal
from pathlib import Path

from tigergraphx.config import TigerGraphConnectionConfig
from tigergraphx.core.tigergraph_api import TigerGraphAPI, DataSourceType

logger = logging.getLogger(__name__)


class TigerGraphDatabase:
    """
    High-level interface for managing TigerGraph database operations.

    Provides access to general database-level functionality such as admin tasks,
    running GSQL commands, and managing data sources.

    For graph-specific operations, use the `Graph` class instead.
    """

    def __init__(
        self,
        tigergraph_connection_config: Optional[
            TigerGraphConnectionConfig | Dict | str | Path
        ] = None,
    ):
        """
        Initialize the TigerGraphDatabase with the given connection configuration.

        Args:
            tigergraph_connection_config: Connection settings for TigerGraph.
        """
        self._tigergraph_api = TigerGraphAPI(tigergraph_connection_config)

    # ------------------------------ Admin ------------------------------
    def ping(self) -> str:
        """
        Ping the TigerGraph server and return its response.

        Returns:
            Response string from the server.
        """
        return self._tigergraph_api.ping()

    # ------------------------------ GSQL ------------------------------
    def gsql(self, command: str) -> str:
        """
        Run a raw GSQL command and return the response.

        Args:
            command: GSQL command string.

        Returns:
            Response string from the GSQL server.
        """
        return self._tigergraph_api.gsql(command)

    def list_metadata(self, graph_name: Optional[str] = None) -> str:
        """
        List metadata in the TigerGraph database, including vertex/edge types, graphs, jobs,
        data sources, and packages.

        If a graph name is provided, runs `USE GRAPH {graph_name}` followed by `LS`.
        Otherwise, runs global `LS`.

        Args:
            graph_name: Optional graph name to scope the metadata listing.

        Returns:
            The string output of the LS command.
        """
        command = "LS"
        if graph_name:
            command = f"USE GRAPH {graph_name}\n{command}"
        return self._tigergraph_api.gsql(command)

    # ------------------------------ Security ------------------------------
    def show_secrets(self) -> str:
        """
        List secrets configured in the TigerGraph database.

        Executes the global `SHOW SECRET` command.

        Returns:
            The string output of the SHOW SECRET command.
        """
        command = "SHOW SECRET"
        return self._tigergraph_api.gsql(command)

    def create_secret(self, alias: str) -> str:
        """
        Create a new secret in the TigerGraph database with the specified alias.

        Executes the global `CREATE SECRET {alias}` command.

        Args:
            alias: The alias name for the new secret.

        Returns:
            The string output of the CREATE SECRET command.
        """
        command = f"CREATE SECRET {alias}"
        return self._tigergraph_api.gsql(command)

    def drop_secret(self, alias: str) -> str:
        """
        Drop an existing secret from the TigerGraph database with the specified alias.

        Executes the global `DROP SECRET {alias}` command.

        Args:
            alias: The alias name of the secret to be dropped.

        Returns:
            The string output of the DROP SECRET command.
        """
        command = f"DROP SECRET {alias}"
        return self._tigergraph_api.gsql(command)

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
        return self._tigergraph_api.create_token(secret_alias, graph_name, lifetime_seconds)

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
        return self._tigergraph_api.drop_token(token)

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
        return self._tigergraph_api.create_data_source(
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
        return self._tigergraph_api.update_data_source(
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
        return self._tigergraph_api.get_data_source(name=name)

    def drop_data_source(self, name: str, graph_name: Optional[str] = None) -> str:
        """
        Drop a data source by name. Can specify a graph if removing from a graph-specific context.

        Args:
            name: Name of the data source to remove.
            graph_name: Optional graph name, required if the data source is local.

        Returns:
            API response message.
        """
        return self._tigergraph_api.drop_data_source(name=name, graph_name=graph_name)

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
        return self._tigergraph_api.get_all_data_sources(graph_name=graph_name)

    def drop_all_data_sources(self, graph_name: Optional[str] = None) -> str:
        """
        Drop all data source configurations, optionally within a specific graph.

        Args:
            graph_name: Optional graph name.

        Returns:
            API response message.
        """
        return self._tigergraph_api.drop_all_data_sources(graph_name=graph_name)

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
        return self._tigergraph_api.preview_sample_data(
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
