# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

import logging
from typing import Any, Dict, List, Literal, Optional, Sequence, Set, Tuple
from pathlib import Path
import pandas as pd

from tigergraphx.config import (
    TigerGraphConnectionConfig,
    GraphSchema,
    LoadingJobConfig,
)

from tigergraphx.core.graph_context import GraphContext
from tigergraphx.core.managers import (
    SchemaManager,
    DataManager,
    NodeManager,
    EdgeManager,
    QueryManager,
    StatisticsManager,
    VectorManager,
)

logger = logging.getLogger(__name__)


class Graph:
    """
    A versatile graph data structure for representing both homogeneous and heterogeneous graphs.

    This class supports a variety of graph types, including:

    - **Undirected Homogeneous Graphs** (comparable to NetworkX's `Graph`)
    - **Directed Homogeneous Graphs** (comparable to NetworkX's `DiGraph`)
    - **Undirected Homogeneous Graphs with Parallel Edges** (comparable to NetworkX's `MultiGraph`)
    - **Directed Homogeneous Graphs with Parallel Edges** (comparable to NetworkX's `MultiDiGraph`)
    - **Heterogeneous Graphs** that can include multiple node and edge types

    By bridging established concepts from NetworkX with enhanced support for complex,
    heterogeneous structures, the `Graph` class provides a flexible and powerful interface
    for various applications in network analysis, data modeling, and beyond.
    """

    def __init__(
        self,
        graph_schema: GraphSchema | Dict | str | Path,
        tigergraph_connection_config: Optional[
            TigerGraphConnectionConfig | Dict | str | Path
        ] = None,
        drop_existing_graph: bool = False,
        mode: Literal["normal", "lazy"] = "normal",
    ):
        """
        Initialize a Graph instance.

        Args:
            graph_schema: The schema of the graph.
            tigergraph_connection_config: Connection configuration for TigerGraph.
            drop_existing_graph: If True, drop existing graph before schema creation.
            mode: Defines the initialization behavior. "normal" ensures that the schema
                is created if it doesn’t exist, while "lazy" skips schema creation.
        """
        # Initialize the graph context with the provided schema and connection config
        self._context = GraphContext(
            graph_schema=graph_schema,
            tigergraph_connection_config=tigergraph_connection_config,
        )

        # Extract the graph name, node types, and edge types from the graph schema,
        # including reverse edges for directed edges.
        self.name = self._context.graph_schema.graph_name
        self.node_types: Set[str] = set(self._context.graph_schema.nodes.keys())
        self.edge_types: Set[str] = set()
        for edge_name, edge in self._context.graph_schema.edges.items():
            self.edge_types.add(edge_name)
            if edge.is_directed_edge:
                self.edge_types.add(f"reverse_{edge_name}")
        logger.debug(f"self.name: {self.name}")
        logger.debug(f"self.node_types: {self.node_types}")
        logger.debug(f"self.edge_types: {self.edge_types}")

        # Initialize managers for handling different aspects of the graph
        self._schema_manager = SchemaManager(self._context)
        self._data_manager = DataManager(self._context)
        self._node_manager = NodeManager(self._context)
        self._edge_manager = EdgeManager(self._context)
        self._statistics_manager = StatisticsManager(self._context)
        self._query_manager = QueryManager(self._context)
        self._vector_manager = VectorManager(self._context)

        # Create the schema, drop the graph first if drop_existing_graph is True
        if mode == "normal":
            self.create_schema(drop_existing_graph=drop_existing_graph)

    @classmethod
    def from_db(
        cls,
        graph_name: str,
        tigergraph_connection_config: Optional[
            TigerGraphConnectionConfig | Dict | str | Path
        ] = None,
    ) -> "Graph":
        """
        Retrieve an existing graph schema from TigerGraph and initialize a Graph.

        Args:
            graph_name: The name of the graph to retrieve.
            tigergraph_connection_config: Connection configuration for TigerGraph.

        Returns:
            An instance of Graph initialized from the database schema.
        """
        # Retrieve schema using SchemaManager
        graph_schema = SchemaManager.get_schema_from_db(
            graph_name, tigergraph_connection_config
        )
        # Initialize the graph with the retrieved schema
        return cls(
            graph_schema=graph_schema,
            tigergraph_connection_config=tigergraph_connection_config,
            mode="lazy",
        )

    from tigergraphx.core.view.node_view import NodeView

    @property
    def nodes(self) -> NodeView:
        """
        Return a NodeView instance.

        Returns:
            The node view for the graph.
        """

        from tigergraphx.core.view.node_view import NodeView

        return NodeView(self)

    # ------------------------------ Schema Operations ------------------------------
    def get_schema(self, format: Literal["json", "dict"] = "dict") -> str | Dict:
        """
        Get the schema of the graph.

        Args:
            format: Format of the schema.

        Returns:
            The graph schema.
        """
        return self._schema_manager.get_schema(format)

    def create_schema(self, drop_existing_graph: bool = False) -> bool:
        """
        Create the graph schema.

        Args:
            drop_existing_graph: If True, drop the graph before creation.

        Returns:
            True if schema was created successfully.
        """
        return self._schema_manager.create_schema(drop_existing_graph)

    def drop_graph(self) -> None:
        """
        Drop the graph from TigerGraph.
        """
        return self._schema_manager.drop_graph()

    # ------------------------------ Data Loading Operations ------------------------------
    def load_data(
        self, loading_job_config: LoadingJobConfig | Dict | str | Path
    ) -> str:
        """
        Load data into the graph using the provided loading job configuration.

        Args:
            loading_job_config: Loading job config.

        Returns:
            GSQL response string after executing the loading job.
        """
        return self._data_manager.load_data(loading_job_config)

    # ------------------------------ Node Operations ------------------------------
    def add_node(self, node_id: str | int, node_type: Optional[str] = None, **attr):
        """
        Add a node to the graph.

        Args:
            node_id: The identifier of the node.
            node_type: The type of the node.
            **attr: Additional attributes for the node.
        """
        node_id = self._to_str_node_id(node_id)
        node_type = self._validate_node_type(node_type)
        return self._node_manager.add_node(node_id, node_type, **attr)

    def add_nodes_from(
        self,
        nodes_for_adding: List[str | int] | List[Tuple[str | int, Dict[str, Any]]],
        node_type: Optional[str] = None,
        **attr,
    ) -> Optional[int]:
        """
        Add nodes from a list of IDs or tuples of ID and attributes.

        Args:
            nodes_for_adding: List of node IDs or (ID, attributes) tuples.
            node_type: The type of the nodes.
            **attr: Common attributes for all nodes.

        Returns:
            The number of nodes added
        """
        normalized_nodes = self._normalize_nodes_for_adding(nodes_for_adding, **attr)
        if normalized_nodes is None:
            return None
        node_type = self._validate_node_type(node_type)
        return self._node_manager.add_nodes_from(normalized_nodes, node_type)

    def remove_node(self, node_id: str | int, node_type: Optional[str] = None) -> bool:
        """
        Remove a node from the graph.

        Args:
            node_id: The identifier of the node.
            node_type: The type of the node.

        Returns:
            True if the node was removed, False otherwise.
        """
        node_id = self._to_str_node_id(node_id)
        node_type = self._validate_node_type(node_type)
        return self._node_manager.remove_node(node_id, node_type)

    def has_node(self, node_id: str | int, node_type: Optional[str] = None) -> bool:
        """
        Check if a node exists in the graph.

        Args:
            node_id: The identifier of the node.
            node_type: The type of the node.

        Returns:
            True if the node exists, False otherwise.
        """
        node_id = self._to_str_node_id(node_id)
        node_type = self._validate_node_type(node_type)
        return self._node_manager.has_node(node_id, node_type)

    def get_node_data(
        self, node_id: str | int, node_type: Optional[str] = None
    ) -> Dict | None:
        """
        Get data for a specific node.

        Args:
            node_id: The identifier of the node.
            node_type: The type of the node.

        Returns:
            The node data or None if not found.
        """
        node_id = self._to_str_node_id(node_id)
        node_type = self._validate_node_type(node_type)
        return self._node_manager.get_node_data(node_id, node_type)

    def get_node_edges(
        self,
        node_id: str | int,
        node_type: Optional[str] = None,
        edge_types: Optional[List[str] | str] = None,
    ) -> List[Tuple]:
        """
        Get edges connected to a specific node.

        Args:
            node_id: The identifier of the node.
            node_type: The type of the node.
            edge_types: A list of edge types. If None, consider all edge types.

        Returns:
            A list of edges represented as (from_id, to_id).
        """
        node_id = self._to_str_node_id(node_id)
        node_type = self._validate_node_type(node_type)
        edge_type_set = self._validate_edge_types_as_set(edge_types)
        return self._node_manager.get_node_edges(node_id, node_type, edge_type_set)

    def clear(self) -> bool:
        """
        Clear all nodes from the graph.

        Returns:
            True if nodes were cleared.
        """
        return self._node_manager.clear()

    # ------------------------------ Edge Operations ------------------------------
    def add_edge(
        self,
        src_node_id: str | int,
        tgt_node_id: str | int,
        src_node_type: Optional[str] = None,
        edge_type: Optional[str] = None,
        tgt_node_type: Optional[str] = None,
        **attr,
    ):
        """
        Add an edge to the graph.

        Args:
            src_node_id: Source node identifier.
            tgt_node_id: Target node identifier.
            src_node_type: Source node type.
            edge_type: Edge type.
            tgt_node_type: Target node type.
            **attr: Additional edge attributes.
        """
        src_node_id, tgt_node_id = self._to_str_edge_ids(src_node_id, tgt_node_id)
        src_node_type, edge_type, tgt_node_type = self._validate_edge_type(
            src_node_type, edge_type, tgt_node_type
        )
        return self._edge_manager.add_edge(
            src_node_id, tgt_node_id, src_node_type, edge_type, tgt_node_type, **attr
        )

    def add_edges_from(
        self,
        ebunch_to_add: Sequence[Tuple[str | int, str | int]]
        | Sequence[Tuple[str | int, str | int, Dict[str, Any]]],
        src_node_type: Optional[str] = None,
        edge_type: Optional[str] = None,
        tgt_node_type: Optional[str] = None,
        **attr: Any,
    ) -> Optional[int]:
        """
        Add edges from a list of edge tuples.

        Args:
            ebunch_to_add: List of edges to add.
            src_node_type: Source node type.
            edge_type: Edge type.
            tgt_node_type: Target node type.
            **attr: Common attributes for all edges.

        Returns:
            The number of edges added
        """
        normalized_edges = self._normalize_edges_for_adding(ebunch_to_add, **attr)
        if normalized_edges is None:
            return None
        src_node_type, edge_type, tgt_node_type = self._validate_edge_type(
            src_node_type, edge_type, tgt_node_type
        )
        return self._edge_manager.add_edges_from(
            normalized_edges, src_node_type, edge_type, tgt_node_type
        )

    def has_edge(
        self,
        src_node_id: str | int,
        tgt_node_id: str | int,
        src_node_type: Optional[str] = None,
        edge_type: Optional[str] = None,
        tgt_node_type: Optional[str] = None,
    ) -> bool:
        """
        Check if an edge exists in the graph.

        Args:
            src_node_id: Source node identifier.
            tgt_node_id: Target node identifier.
            src_node_type: Source node type.
            edge_type: Edge type.
            tgt_node_type: Target node type.

        Returns:
            True if the edge exists, False otherwise.
        """
        src_node_id, tgt_node_id = self._to_str_edge_ids(src_node_id, tgt_node_id)
        src_node_type, edge_type, tgt_node_type = self._validate_edge_type(
            src_node_type, edge_type, tgt_node_type
        )
        return self._edge_manager.has_edge(
            src_node_id, tgt_node_id, src_node_type, edge_type, tgt_node_type
        )

    def get_edge_data(
        self,
        src_node_id: str | int,
        tgt_node_id: str | int,
        src_node_type: Optional[str] = None,
        edge_type: Optional[str] = None,
        tgt_node_type: Optional[str] = None,
    ) -> Dict | Dict[int | str, Dict] | None:
        """
        Get data for a specific edge.

        Args:
            src_node_id: Source node identifier.
            tgt_node_id: Target node identifier.
            src_node_type: Source node type.
            edge_type: Edge type.
            tgt_node_type: Target node type.

        Returns:
            The edge data or None if not found.
        """
        src_node_id, tgt_node_id = self._to_str_edge_ids(src_node_id, tgt_node_id)
        src_node_type, edge_type, tgt_node_type = self._validate_edge_type(
            src_node_type, edge_type, tgt_node_type
        )
        return self._edge_manager.get_edge_data(
            src_node_id, tgt_node_id, src_node_type, edge_type, tgt_node_type
        )

    # ------------------------------ Statistics Operations ------------------------------
    def degree(
        self,
        node_id: str | int,
        node_type: Optional[str] = None,
        edge_types: Optional[List[str] | str] = None,
    ) -> int:
        """
        Get the out-degree of a node based on the specified edge types.

        If the node has both a directed edge (e.g., "transfer") and its reverse
        (e.g., "reverse_transfer"), only the directed edge is counted unless both are
        explicitly included in edge_types.

        Args:
            node_id: Node identifier.
            node_type: Node type.
            edge_types: List of edge types to consider. If None, use all edge types.

        Returns:
            The out-degree of the node.
        """
        node_id = self._to_str_node_id(node_id)
        node_type = self._validate_node_type(node_type)
        edge_type_set = self._validate_edge_types_as_set(edge_types)
        return self._statistics_manager.degree(node_id, node_type, edge_type_set)

    def number_of_nodes(self, node_type: Optional[str] = None) -> int:
        """
        Get the number of nodes in the graph.

        Args:
            node_type: Type of nodes to count.

        Returns:
            The number of nodes.
        """
        if node_type is not None:
            node_type = self._validate_node_type(node_type)
        return self._statistics_manager.number_of_nodes(node_type)

    def number_of_edges(self, edge_type: Optional[str] = None) -> int:
        """
        Get the number of edges in the graph.

        Args:
            edge_type: Edge type to count.

        Returns:
            The number of edges.
        """
        if edge_type is not None:
            if edge_type not in self.edge_types:
                raise ValueError(
                    f"Invalid edge type '{edge_type}'. Must be one of {self.edge_types}."
                )
        return self._statistics_manager.number_of_edges(edge_type)

    # ------------------------------ Query Operations ------------------------------
    def create_query(self, gsql_query: str) -> bool:
        """
        Create a GSQL query on the graph.

        Args:
            gsql_query: A valid GSQL query string to be created.
                The query must follow TigerGraph's GSQL syntax.
                See the [GSQL Query Language Reference](https://docs.tigergraph.com/gsql-ref/current/intro/)
                for guidance on writing GSQL queries.

        Returns:
            True if the query was successfully installed, False otherwise.
        """
        return self._query_manager.create_query(gsql_query)

    def install_query(self, query_name: str) -> bool:
        """
        Install a GSQL query on the graph.

        Args:
            query_name: Name of the query to install.

        Returns:
            True if the query was successfully installed, False otherwise.
        """
        return self._query_manager.install_query(query_name)

    def drop_query(self, query_name: str) -> bool:
        """
        Drop a GSQL query from the graph.

        Args:
            query_name: Name of the query to drop.

        Returns:
            True if the query was successfully dropped, False otherwise.
        """
        return self._query_manager.drop_query(query_name)

    def run_query(self, query_name: str, params: Dict = {}) -> Optional[List]:
        """
        Run a pre-installed query on the graph.

        Args:
            query_name: Name of the query.
            params: Parameters for the query.

        Returns:
            The query result or None if an error occurred.
        """
        return self._query_manager.run_query(query_name, params)

    def is_query_installed(self, query_name: str) -> bool:
        """
        Check if a query is installed on the graph.

        Args:
            query_name: Name of the query.

        Returns:
            True if the query is installed, False otherwise.
        """
        return self._query_manager.is_query_installed(query_name)

    def get_nodes(
        self,
        node_type: Optional[str] = None,
        all_node_types: bool = False,
        node_alias: str = "s",
        filter_expression: Optional[str] = None,
        return_attributes: Optional[str | List[str]] = None,
        limit: Optional[int] = None,
        output_type: Literal["DataFrame", "List"] = "DataFrame",
    ) -> pd.DataFrame | List[Dict[str, Any]]:
        """
        Retrieve nodes from the graph.

        Args:
            node_type: Node type to retrieve.
            all_node_types: If True, ignore filtering by node type.
            node_alias: Alias for the node. Used in filter_expression.
            filter_expression: Filter expression.
            return_attributes: Attributes to return.
            limit: Maximum number of nodes to return.
            output_type: Output format, either "DataFrame" (default) or "List".

        Returns:
            A DataFrame or List containing the nodes.
        """
        if not all_node_types:
            node_type = self._validate_node_type(node_type)
        return self._query_manager.get_nodes(
            node_type=node_type,
            all_node_types=all_node_types,
            node_alias=node_alias,
            filter_expression=filter_expression,
            return_attributes=return_attributes,
            limit=limit,
            output_type=output_type,
        )

    def get_edges(
        self,
        source_node_types: Optional[str | List[str]] = None,
        source_node_alias: str = "s",
        edge_types: Optional[str | List[str]] = None,
        edge_alias: str = "e",
        target_node_types: Optional[str | List[str]] = None,
        target_node_alias: str = "t",
        filter_expression: Optional[str] = None,
        return_attributes: Optional[str | List[str]] = None,
        limit: Optional[int] = None,
        output_type: Literal["DataFrame", "List"] = "DataFrame",
    ) -> pd.DataFrame | List[Dict[str, Any]]:
        """
        Retrieve edges from the graph.

        Args:
            source_node_types: Source node types.
            source_node_alias: Alias for the source node. Used in filter_expression.
            edge_types: Edge types to consider.
            edge_alias: Alias for the edge. Used in filter_expression.
            target_node_types: Target node types.
            target_node_alias: Alias for the target node. Used in filter_expression.
            filter_expression: Filter expression.
            return_attributes: Attributes to return.
            limit: Maximum number of edges.
            output_type: Output format, either "DataFrame" (default) or "List".

        Returns:
            A DataFrame or List containing the edges.
        """
        source_node_type_set = self._validate_node_types_as_set(source_node_types)
        edge_type_set = self._validate_edge_types_as_set(edge_types)
        target_node_type_set = self._validate_node_types_as_set(target_node_types)
        return self._query_manager.get_edges(
            source_node_type_set=source_node_type_set,
            source_node_alias=source_node_alias,
            edge_type_set=edge_type_set,
            edge_alias=edge_alias,
            target_node_type_set=target_node_type_set,
            target_node_alias=target_node_alias,
            filter_expression=filter_expression,
            return_attributes=return_attributes,
            limit=limit,
            output_type=output_type,
        )

    def get_neighbors(
        self,
        start_nodes: str | int | List[str] | List[int],
        start_node_type: Optional[str] = None,
        start_node_alias: str = "s",
        edge_types: Optional[str | List[str]] = None,
        edge_alias: str = "e",
        target_node_types: Optional[str | List[str]] = None,
        target_node_alias: str = "t",
        filter_expression: Optional[str] = None,
        return_attributes: Optional[str | List[str]] = None,
        limit: Optional[int] = None,
        output_type: Literal["DataFrame", "List"] = "DataFrame",
    ) -> pd.DataFrame | List[Dict[str, Any]]:
        """
        Get neighbors of specified nodes.

        Args:
            start_nodes: Starting node or nodes.
            start_node_type: Type of starting nodes.
            start_node_alias: Alias for the starting node. Used in filter_expression.
            edge_types: Edge types to consider.
            edge_alias: Alias for the edge. Used in filter_expression.
            target_node_types: Types of target nodes.
            target_node_alias: Alias for the target node. Used in filter_expression.
            filter_expression: Filter expression.
            return_attributes: Attributes to return.
            limit: Maximum number of neighbors.
            output_type: Output format, either "DataFrame" (default) or "List".

        Returns:
            A DataFrame or List containing the neighbors.
        """
        if isinstance(start_nodes, str | int):
            new_start_nodes = self._to_str_node_id(start_nodes)
        else:
            new_start_nodes = self._to_str_node_ids(start_nodes)
        start_node_type = self._validate_node_type(start_node_type)
        edge_type_set = self._validate_edge_types_as_set(edge_types)
        target_node_type_set = self._validate_node_types_as_set(target_node_types)
        return self._query_manager.get_neighbors(
            start_nodes=new_start_nodes,
            start_node_type=start_node_type,
            start_node_alias=start_node_alias,
            edge_type_set=edge_type_set,
            edge_alias=edge_alias,
            target_node_type_set=target_node_type_set,
            target_node_alias=target_node_alias,
            filter_expression=filter_expression,
            return_attributes=return_attributes,
            limit=limit,
            output_type=output_type,
        )

    def bfs(
        self,
        start_nodes: str | int | List[str] | List[int],
        node_type: Optional[str] = None,
        edge_types: Optional[str | List[str]] = None,
        max_hops: Optional[int] = None,
        limit: Optional[int] = None,
        output_type: Literal["DataFrame", "List"] = "DataFrame",
    ) -> pd.DataFrame | List[Dict[str, Any]]:
        """
        Perform BFS traversal from a set of start nodes, using batch processing.

        Args:
            start_nodes: Starting node(s) for BFS.
            node_type: Type of the nodes.
            edge_types: Edge types to consider.
            max_hops: Maximum depth (number of hops) for BFS traversal.
            limit: Maximum number of neighbors per hop.
            output_type: Format of the output, either "DataFrame" or "List".

        Returns:
            A DataFrame or List containing the BFS results, with an added '_bfs_level'.
        """
        if isinstance(start_nodes, str | int):
            new_start_nodes = self._to_str_node_id(start_nodes)
        else:
            new_start_nodes = self._to_str_node_ids(start_nodes)
        node_type = self._validate_node_type(node_type)
        edge_type_set = self._validate_edge_types_as_set(edge_types)

        return self._query_manager.bfs(
            start_nodes=new_start_nodes,
            node_type=node_type,
            edge_type_set=edge_type_set,
            max_hops=max_hops,
            limit=limit,
            output_type=output_type,
        )

    # ------------------------------ Vector Operations ------------------------------
    def upsert(
        self,
        data: Dict | List[Dict],
        node_type: Optional[str] = None,
    ) -> Optional[int]:
        """
        Upsert nodes with vector data into the graph.

        Args:
            data: Record(s) to upsert.
            node_type: The node type for the upsert operation.

        Returns:
            The result of the upsert operation or None if an error occurs.
        """
        node_type = self._validate_node_type(node_type)
        return self._vector_manager.upsert(data, node_type)

    def fetch_node(
        self,
        node_id: str | int,
        vector_attribute_name: str,
        node_type: Optional[str] = None,
    ) -> Optional[List[float]]:
        """
        Fetch the embedding vector for a single node.

        Args:
            node_id: The node's identifier.
            vector_attribute_name: The vector attribute name.
            node_type: The node type.

        Returns:
            The embedding vector or None if not found.
        """
        node_id = self._to_str_node_id(node_id)
        node_type = self._validate_node_type(node_type)
        return self._vector_manager.fetch_node(
            node_id, vector_attribute_name, node_type
        )

    def fetch_nodes(
        self,
        node_ids: List[str] | List[int],
        vector_attribute_name: str,
        node_type: Optional[str] = None,
    ) -> Dict[str, List[float]]:
        """
        Fetch embedding vectors for multiple nodes.

        Args:
            node_ids: List of node identifiers.
            vector_attribute_name: The vector attribute name.
            node_type: The node type.

        Returns:
            Mapping of node IDs to embedding vectors.
        """
        new_node_ids = self._to_str_node_ids(node_ids)
        node_type = self._validate_node_type(node_type)
        return self._vector_manager.fetch_nodes(
            new_node_ids, vector_attribute_name, node_type
        )

    def search(
        self,
        data: List[float],
        vector_attribute_name: str,
        node_type: Optional[str] = None,
        limit: int = 10,
        return_attributes: Optional[str | List[str]] = None,
        candidate_ids: Optional[Set[str]] = None,
    ) -> List[Dict]:
        """
        Search for similar nodes based on a query vector.

        Args:
            data: Query vector.
            vector_attribute_name: The vector attribute name.
            node_type: The node type to search.
            limit: Number of nearest neighbors to return.
            return_attributes: Attributes to return.
            candidate_ids: Limit search to these node IDs.

        Returns:
            List of similar nodes and their details.
        """
        node_type = self._validate_node_type(node_type)
        return self._vector_manager.search(
            data=data,
            vector_attribute_name=vector_attribute_name,
            node_type=node_type,
            limit=limit,
            return_attributes=return_attributes,
            candidate_ids=candidate_ids,
        )

    def search_multi_vector_attributes(
        self,
        data: List[float],
        vector_attribute_names: List[str],
        node_types: Optional[List[str]] = None,
        limit: int = 10,
        return_attributes_list: Optional[List[List[str]]] = None,
    ) -> List[Dict]:
        """
        Search for similar nodes using multiple vector attributes.

        Args:
            data: Query vector.
            vector_attribute_names: List of vector attribute names.
            node_types: List of node types corresponding to the attributes.
            limit: Number of nearest neighbors to return.
            return_attributes_list: Attributes to return per node type.

        Returns:
            List of similar nodes and their details.
        """
        new_node_types = []
        if node_types is not None:
            for node_type in node_types:
                new_node_type = self._validate_node_type(node_type)
                new_node_types.append(new_node_type)
        elif len(self.node_types) == 1:
            new_node_types = [next(iter(self.node_types))] * len(vector_attribute_names)
        else:
            raise ValueError("Invalid input: node_types must be provided.")
        return self._vector_manager.search_multi_vector_attributes(
            data=data,
            vector_attribute_names=vector_attribute_names,
            node_types=new_node_types,
            limit=limit,
            return_attributes_list=return_attributes_list,
        )

    def search_top_k_similar_nodes(
        self,
        node_id: str | int,
        vector_attribute_name: str,
        node_type: Optional[str] = None,
        limit: int = 5,
        return_attributes: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Retrieve the top-k nodes similar to a given node.

        Args:
            node_id: The source node's identifier.
            vector_attribute_name: The embedding attribute name.
            node_type: The type of nodes to search.
            limit: Number of similar nodes to return.
            return_attributes: Attributes to return.

        Returns:
            List of similar nodes.
        """
        node_id = self._to_str_node_id(node_id)
        node_type = self._validate_node_type(node_type)
        return self._vector_manager.search_top_k_similar_nodes(
            node_id=node_id,
            vector_attribute_name=vector_attribute_name,
            node_type=node_type,
            limit=limit,
            return_attributes=return_attributes,
        )

    # ------------------------------ Utilities ------------------------------
    def _validate_node_type(self, node_type: Optional[str] = None) -> str:
        """
        Validate and return the effective node type.

        Args:
            node_type: The node type to validate.

        Returns:
            The validated node type.

        Raises:
            ValueError: If the node type is invalid or ambiguous.
        """
        if node_type is not None:
            if node_type not in self.node_types:
                raise ValueError(
                    f"Invalid node type '{node_type}'. Must be one of {self.node_types}."
                )
            return node_type
        if len(self.node_types) == 0:
            raise ValueError("The graph has no node types defined.")
        if len(self.node_types) > 1:
            raise ValueError(
                "Multiple node types detected. Please specify a node type."
            )
        return next(iter(self.node_types))

    def _validate_edge_type(
        self,
        src_node_type: Optional[str] = None,
        edge_type: Optional[str] = None,
        tgt_node_type: Optional[str] = None,
    ) -> tuple[str, str, str]:
        """
        Validate node and edge types and return effective types.

        Args:
            src_node_type: Source node type.
            edge_type: Edge type.
            tgt_node_type: Target node type.

        Returns:
            Validated (src_node_type, edge_type, tgt_node_type).

        Raises:
            ValueError: If any provided type is invalid or ambiguous.
        """
        src_node_type = self._validate_node_type(src_node_type)
        tgt_node_type = self._validate_node_type(tgt_node_type)
        if edge_type is not None:
            if edge_type not in self.edge_types:
                raise ValueError(
                    f"Invalid edge type '{edge_type}'. Must be one of {self.edge_types}."
                )
        else:
            if len(self.edge_types) == 0:
                raise ValueError("The graph has no edge types defined.")
            if len(self.edge_types) > 1:
                raise ValueError(
                    "Multiple edge types detected. Please specify an edge type."
                )
            edge_type = next(iter(self.edge_types))
        return src_node_type, edge_type, tgt_node_type

    def _validate_edge_types_as_set(
        self,
        edge_types: Optional[List[str] | str] = None,
    ) -> Optional[Set[str]]:
        """
        Validate edge types and return effective types.

        Args:
            edge_types: A list of edge types. If None, consider all edge types.

        Returns:
            Validated edge types as a set.

        Raises:
            ValueError: If any provided type is invalid or ambiguous.
        """
        if edge_types is None:
            return None  # None indicates all edge types
        # Ensure edge_types is a list for consistent processing
        if isinstance(edge_types, str):
            edge_types = [edge_types]
        # Check that all edge types are valid
        invalid_types = [etype for etype in edge_types if etype not in self.edge_types]
        if invalid_types:
            raise ValueError(
                f"Invalid edge type(s): {', '.join(invalid_types)}. "
                f"Valid edge types are: {', '.join(self.edge_types)}."
            )
        return set(edge_types)

    def _validate_node_types_as_set(
        self,
        node_types: Optional[List[str] | str] = None,
    ) -> Optional[Set[str]]:
        """
        Validate node types and return effective types.

        Args:
            node_types: A list of node types. If None, consider all node types.

        Returns:
            Validated node types as a set.

        Raises:
            ValueError: If any provided type is invalid or ambiguous.
        """
        if node_types is None:
            return None  # None indicates all node types
        # Ensure node_types is a list for consistent processing
        if isinstance(node_types, str):
            node_types = [node_types]
        # Check that all node types are valid
        invalid_types = [ntype for ntype in node_types if ntype not in self.node_types]
        if invalid_types:
            raise ValueError(
                f"Invalid node type(s): {', '.join(invalid_types)}. "
                f"Valid node types are: {', '.join(self.node_types)}."
            )
        return set(node_types)

    @staticmethod
    def _to_str_node_id(node_id: str | int) -> str:
        """Converts the node identifier to a string.

        Args:
            node_id: The node identifier.

        Returns:
            The node identifier as a string.
        """
        return str(node_id)

    @staticmethod
    def _to_str_edge_ids(
        src_node_id: str | int, tgt_node_id: str | int
    ) -> Tuple[str, str]:
        """Converts source and target node IDs to strings.

        Args:
            src_node_id: The source node identifier.
            tgt_node_id: The target node identifier.

        Returns:
            A tuple containing both node IDs as strings.
        """
        return str(src_node_id), str(tgt_node_id)

    @staticmethod
    def _to_str_node_ids(
        node_ids: List[str] | List[int],
    ) -> List[str]:
        """Converts node_ids to a list of strings.

        Args:
            node_ids: A list of node identifiers.

        Returns:
            A list of strings.
        """
        return [str(node) for node in node_ids]

    @staticmethod
    def _normalize_nodes_for_adding(
        nodes_for_adding: List[str | int] | List[Tuple[str | int, Dict[str, Any]]],
        **common_attr: Any,
    ) -> Optional[List[Tuple[str, Dict[str, Any]]]]:
        """
        Normalizes node definitions by converting all node IDs to str and merging common attributes.

        Parameters:
            nodes_for_adding: A list of node definitions, which can be either:
                - A list of node IDs (str or int), or
                - A list of tuples (node_id, attributes dictionary)
            common_attr: Common attributes to merge with each node's attributes.

        Returns:
            A normalized list of node definitions as tuples (str, Dict[str, Any]),
            or None if there is an error in the input format.
        """
        normalized_nodes: List[Tuple[str, Dict[str, Any]]] = []

        for node in nodes_for_adding:
            # Case: node is just a node ID (str or int)
            if isinstance(node, (str, int)):
                node_id = str(node)
                attributes = {}
            # Case: node is a tuple (node_id, attributes)
            elif isinstance(node, tuple) and len(node) == 2:
                node_id_raw, attributes = node
                if not isinstance(attributes, dict):
                    print(
                        f"Error: Attributes for node {node_id_raw} should be a dictionary."
                    )
                    return None
                node_id = str(node_id_raw)
            else:
                print(
                    f"Error: Invalid node format: {node}. Expected str, int, or Tuple[str | int, dict]."
                )
                return None

            # Combine node-specific attributes with common attributes
            node_data = {**attributes, **common_attr}
            normalized_nodes.append((node_id, node_data))

        return normalized_nodes

    @staticmethod
    def _normalize_edges_for_adding(
        ebunch_to_add: Sequence[Tuple[str | int, str | int]]
        | Sequence[Tuple[str | int, str | int, Dict[str, Any]]],
        **common_attr: Any,
    ) -> Optional[List[Tuple[str, str, Dict[str, Any]]]]:
        """
        Normalize edges by converting node IDs to strings and merging attributes.

        Args:
            ebunch_to_add: List of edges to normalize.
            **common_attr: Common attributes to merge with edge-specific attributes.

        Returns:
            A normalized list of edges as tuples (src_node_id, tgt_node_id, attributes).
            Returns None if there is an error in the input format.
        """
        normalized_edges = []

        for edge in ebunch_to_add:
            if isinstance(edge, tuple) and len(edge) == 2:
                src_node_id, tgt_node_id = edge
                attributes = {}
            elif isinstance(edge, tuple) and len(edge) == 3:
                src_node_id, tgt_node_id, attributes = edge
                if not isinstance(attributes, dict):
                    logger.error(
                        f"Attributes for edge {src_node_id} -> {tgt_node_id} should be a dictionary."
                    )
                    return None
            else:
                logger.error(
                    f"Invalid edge format: {edge}. Expected Tuple[str|int, str|int] or "
                    f"Tuple[str|int, str|int, Dict[str, Any]]."
                )
                return None

            # Convert node IDs to strings and merge attributes
            src_node_id = str(src_node_id)
            tgt_node_id = str(tgt_node_id)
            edge_data = {**attributes, **common_attr}

            # Append the normalized edge
            normalized_edges.append((src_node_id, tgt_node_id, edge_data))

        return normalized_edges
