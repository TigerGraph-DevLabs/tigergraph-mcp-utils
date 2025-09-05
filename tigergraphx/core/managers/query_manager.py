# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

import logging
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
import pandas as pd

from tigergraphx.config import (
    NodeSpec,
    EdgeSpec,
    NeighborSpec,
)

from .base_manager import BaseManager

from tigergraphx.core.graph_context import GraphContext


logger = logging.getLogger(__name__)


class QueryManager(BaseManager):
    def __init__(self, context: GraphContext):
        super().__init__(context)

    def create_query(self, gsql_query: str) -> bool:
        try:
            result = self._tigergraph_api.create_query(self._graph_name, gsql_query)
            return "Successfully created queries" in result
        except Exception as e:
            logger.error(f"Error creating query: {e}")
            return False

    def install_query(self, query_name: str) -> bool:
        try:
            logger.info(
                f"Installing query '{query_name}' for graph '{self._graph_name}'..."
            )
            result = self._tigergraph_api.install_query(self._graph_name, query_name)
            if "Query installed successfully" in result:
                logger.info(f"Query '{query_name}' installed successfully.")
                return True
            logger.warning(
                f"Query installation failed for '{query_name}'. Result: {result}"
            )
            return False
        except Exception as e:
            logger.error(f"Exception while installing query '{query_name}': {e}")
            return False

    def drop_query(self, query_name: str) -> bool:
        try:
            result = self._tigergraph_api.drop_query(self._graph_name, query_name)
            return query_name in result.get("dropped", [])
        except Exception as e:
            logger.error(f"Error dropping query '{query_name}': {e}")
            return False

    def run_query(self, query_name: str, params: Dict = {}) -> Optional[List]:
        try:
            return self._tigergraph_api.run_installed_query_get(
                self._graph_name, query_name, params
            )
        except Exception as e:
            logger.error(f"Error running query {query_name}: {e}")
            return None

    def is_query_installed(self, query_name: str) -> bool:
        try:
            query_info = self._tigergraph_api.get_query_info(self._graph_name)
            for query in query_info:
                if (
                    query.get("name") == query_name
                    and query.get("installed")
                ):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking if query {query_name} is installed: {e}")
            return False

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
        High-level function to retrieve nodes with multiple parameters.
        Converts parameters into a NodeSpec and delegates to `_get_nodes_from_spec`.
        """
        spec = NodeSpec(
            node_type=node_type,
            all_node_types=all_node_types,
            node_alias=node_alias,
            filter_expression=filter_expression,
            return_attributes=return_attributes,
            limit=limit,
        )
        return self.get_nodes_from_spec(spec, output_type)

    def get_nodes_from_spec(
        self, spec: NodeSpec, output_type: Literal["DataFrame", "List"] = "DataFrame"
    ) -> pd.DataFrame | List[Dict[str, Any]]:
        """
        Core function to retrieve nodes based on a NodeSpec object.
        """
        gsql_script = self._create_gsql_get_nodes(spec)
        try:
            result = self._tigergraph_api.run_interpreted_query(gsql_script)
            if not result or not isinstance(result, list):
                return self._initialize_empty_result(output_type)
            nodes = result[0].get("Nodes")
            if not nodes or not isinstance(nodes, list):
                return self._initialize_empty_result(output_type)
            if output_type == "List":
                clean_nodes = []
                for node in nodes:
                    attributes = node.get("attributes", {})
                    if spec.return_attributes is None:
                        clean_nodes.append(attributes)
                    else:
                        clean_nodes.append(
                            {
                                attr: attributes.get(attr)
                                for attr in spec.return_attributes
                            }
                        )
                return clean_nodes
            elif output_type == "DataFrame":
                df = pd.DataFrame(pd.json_normalize(nodes))
                if df.empty:
                    return pd.DataFrame()
                attribute_columns = [
                    col for col in df.columns if col.startswith("attributes.")
                ]
                if spec.return_attributes is None:
                    rename_map = {
                        col: col.replace("attributes.", "") for col in attribute_columns
                    }
                    reordered_columns = []
                else:
                    rename_map = {
                        f"attributes.{attr}": attr for attr in spec.return_attributes
                    }
                    reordered_columns = [
                        attr
                        for attr in spec.return_attributes
                        if attr in rename_map.values()
                    ]
                df.rename(columns=rename_map, inplace=True)
                drop_columns = []
                if spec.return_attributes is not None:
                    drop_columns = ["v_id"]
                    if spec.node_type is not None and "v_type" in df.columns:
                        drop_columns.append("v_type")
                df.drop(
                    columns=[col for col in drop_columns if col in df.columns],
                    inplace=True,
                )
                remaining_columns = [
                    col for col in df.columns if col not in reordered_columns
                ]
                return pd.DataFrame(df[reordered_columns + remaining_columns])
        except Exception as e:
            logger.error(f"Error retrieving nodes for type {spec.node_type}: {e}")
        return self._initialize_empty_result(output_type)

    def get_edges(
        self,
        source_node_type_set: Optional[Set[str]] = None,
        source_node_alias: str = "s",
        edge_type_set: Optional[Set[str]] = None,
        edge_alias: str = "e",
        target_node_type_set: Optional[Set[str]] = None,
        target_node_alias: str = "t",
        filter_expression: Optional[str] = None,
        return_attributes: Optional[str | List[str]] = None,
        limit: Optional[int] = None,
        output_type: Literal["DataFrame", "List"] = "DataFrame",
    ) -> pd.DataFrame | List[Dict[str, Any]]:
        spec = EdgeSpec(
            source_node_type_set=source_node_type_set,
            source_node_alias=source_node_alias,
            edge_type_set=edge_type_set,
            edge_alias=edge_alias,
            target_node_type_set=target_node_type_set,
            target_node_alias=target_node_alias,
            filter_expression=filter_expression,
            return_attributes=return_attributes,
            limit=limit,
        )
        return self.get_edges_from_spec(spec, output_type)

    def get_edges_from_spec(
        self, spec: EdgeSpec, output_type: Literal["DataFrame", "List"] = "DataFrame"
    ) -> pd.DataFrame | List[Dict[str, Any]]:
        gsql_script = self._create_gsql_get_edges(spec)
        try:
            result = self._tigergraph_api.run_interpreted_query(gsql_script)
            if not result or not isinstance(result, list):
                return self._initialize_empty_result(output_type)
            rows = result[0].get("T")
            if not rows or not isinstance(rows, list):
                return self._initialize_empty_result(output_type)

            if output_type == "List":
                if spec.return_attributes is None:
                    return rows
                if isinstance(spec.return_attributes, str):
                    spec.return_attributes = [spec.return_attributes]
                return [
                    {
                        key: row.get(key)
                        for key in [spec.source_node_alias, spec.target_node_alias]
                        + spec.return_attributes
                    }
                    for row in rows
                ]

            elif output_type == "DataFrame":
                df = pd.DataFrame(rows)
                if df.empty:
                    return pd.DataFrame()
                if spec.return_attributes is None:
                    return df
                if isinstance(spec.return_attributes, str):
                    spec.return_attributes = [spec.return_attributes]
                ordered_cols = [
                    spec.source_node_alias,
                    spec.target_node_alias,
                    *spec.return_attributes,
                ]
                remaining_cols = [col for col in df.columns if col not in ordered_cols]
                return pd.DataFrame(df[ordered_cols + remaining_cols])
        except Exception as e:
            logger.error(f"Error retrieving edges: {e}")
        return self._initialize_empty_result(output_type)

    def get_neighbors(
        self,
        start_nodes: str | List[str],
        start_node_type: str,
        start_node_alias: str = "s",
        edge_type_set: Optional[Set[str]] = None,
        edge_alias: str = "e",
        target_node_type_set: Optional[Set[str]] = None,
        target_node_alias: str = "t",
        filter_expression: Optional[str] = None,
        return_attributes: Optional[str | List[str]] = None,
        limit: Optional[int] = None,
        output_type: Literal["DataFrame", "List"] = "DataFrame",
    ) -> pd.DataFrame | List[Dict[str, Any]]:
        """
        High-level function to retrieve neighbors with multiple parameters.
        Converts parameters into a NeighborSpec and delegates to `_get_neighbors_from_spec`.
        """
        spec = NeighborSpec(
            start_nodes=start_nodes,
            start_node_type=start_node_type,
            start_node_alias=start_node_alias,
            edge_type_set=edge_type_set,
            edge_alias=edge_alias,
            target_node_type_set=target_node_type_set,
            target_node_alias=target_node_alias,
            filter_expression=filter_expression,
            return_attributes=return_attributes,
            limit=limit,
        )
        return self.get_neighbors_from_spec(spec, output_type=output_type)

    def get_neighbors_from_spec(
        self,
        spec: NeighborSpec,
        output_type: Literal["DataFrame", "List"] = "DataFrame",
    ) -> pd.DataFrame | List[Dict[str, Any]]:
        """
        Core function to retrieve neighbors based on a NeighborSpec object.
        """
        gsql_script, params = self._create_gsql_get_neighbors(spec)
        try:
            result = self._tigergraph_api.run_interpreted_query(gsql_script, params)
            if not result or not isinstance(result, list):
                return self._initialize_empty_result(output_type)
            neighbors = result[0].get("Neighbors")
            if not neighbors or not isinstance(neighbors, list):
                return self._initialize_empty_result(output_type)
            if output_type == "List":
                clean_neighbors = []
                for neighbor in neighbors:
                    attributes = neighbor.get("attributes", {})
                    if spec.return_attributes is None:
                        clean_neighbors.append(attributes)
                    else:
                        clean_neighbors.append(
                            {
                                attr: attributes.get(attr)
                                for attr in spec.return_attributes
                            }
                        )
                return clean_neighbors
            elif output_type == "DataFrame":
                df = pd.DataFrame(pd.json_normalize(neighbors))
                if df.empty:
                    return pd.DataFrame()
                attribute_columns = [
                    col for col in df.columns if col.startswith("attributes.")
                ]
                if spec.return_attributes is None:
                    rename_map = {
                        col: col.replace("attributes.", "") for col in attribute_columns
                    }
                    reordered_columns = []
                else:
                    rename_map = {
                        f"attributes.{attr}": attr for attr in spec.return_attributes
                    }
                    reordered_columns = [
                        attr
                        for attr in spec.return_attributes
                        if attr in rename_map.values()
                    ]
                df.rename(columns=rename_map, inplace=True)
                drop_columns = [col for col in ["v_id", "v_type"] if col in df.columns]
                df.drop(columns=drop_columns, inplace=True)
                remaining_columns = [
                    col for col in df.columns if col not in reordered_columns
                ]
                return pd.DataFrame(df[reordered_columns + remaining_columns])
        except Exception as e:
            logger.error(
                f"Error retrieving neighbors for node(s) {spec.start_nodes}: {e}"
            )
        return self._initialize_empty_result(output_type)

    def bfs(
        self,
        start_nodes: str | List[str],
        node_type: str,
        edge_type_set: Optional[Set[str]] = None,
        max_hops: Optional[int] = 3,
        limit: Optional[int] = None,
        output_type: Literal["DataFrame", "List"] = "DataFrame",
    ) -> pd.DataFrame | List[Dict[str, Any]]:
        """
        Perform BFS traversal from a set of start nodes, using batch processing.

        Args:
            start_nodes: Starting node(s) for BFS.
            node_type: Type of the nodes.
            edge_type_set: Edge types to consider.
            max_hops: Maximum depth (number of hops) for BFS traversal.
            limit: Maximum number of neighbors per hop.
            output_type: Format of the output, either "DataFrame" or "List".

        Returns:
            A DataFrame or List containing the BFS results, with an added '_bfs_level'.
        """
        start_node_set = (
            {start_nodes} if isinstance(start_nodes, str) else set(start_nodes)
        )
        visited = start_node_set.copy()
        queue = start_node_set.copy()
        level = 0

        last_level_result = self._initialize_empty_result(output_type)

        primary_key = self._graph_schema.nodes[node_type].primary_key

        while queue and (not max_hops or level < max_hops):
            neighbors = self.get_neighbors(
                start_nodes=list(queue),
                start_node_type=node_type,
                edge_type_set=edge_type_set,
                target_node_type_set={node_type},
                limit=limit,
                output_type=output_type,
            )

            # Handle DataFrame case
            if isinstance(neighbors, pd.DataFrame):
                if neighbors.empty:
                    break
                neighbor_ids = set(neighbors[primary_key].astype(str))
                neighbors = neighbors.copy()
                neighbors["_bfs_level"] = level  # Add bfs level here

            # Handle List case
            else:
                if not neighbors:
                    break
                neighbor_ids = {str(n[primary_key]) for n in neighbors}
                # Add _bfs_level for each neighbor dict
                for neighbor in neighbors:
                    neighbor["_bfs_level"] = level

            next_queue = neighbor_ids - visited
            if not next_queue:
                break

            if max_hops and level == max_hops - 1:
                if isinstance(neighbors, pd.DataFrame):
                    last_level_result = pd.DataFrame(
                        neighbors[~neighbors[primary_key].isin(list(visited))]
                    )
                else:
                    last_level_result = [
                        n for n in neighbors if n[primary_key] not in visited
                    ]

            visited.update(next_queue)
            queue = next_queue
            level += 1

        return last_level_result

    def _create_gsql_get_nodes(self, spec: NodeSpec) -> str:
        """
        Core function to generate a GSQL query based on a NodeSpec object.
        """
        node_type_str = f"{spec.node_type}.*" if not spec.all_node_types else "ANY"
        filter_expression_str = (
            f"WHERE {spec.filter_expression}" if spec.filter_expression else ""
        )
        limit_clause = f"LIMIT {spec.limit}" if spec.limit else ""
        return_attributes = spec.return_attributes or []

        # Generate the base query
        query = f"""
INTERPRET QUERY() FOR GRAPH {self._graph_name} {{
  Nodes = {{{node_type_str}}};
"""
        # Add SELECT block only if filter or limit is specified
        if filter_expression_str or limit_clause:
            query += f"""  Nodes =
    SELECT {spec.node_alias}
    FROM Nodes:{spec.node_alias}
"""
            if filter_expression_str:
                query += f"    {filter_expression_str}\n"
            if limit_clause:
                query += f"    {limit_clause}\n"
            query += "  ;\n"

        # Add PRINT statement
        if return_attributes:
            prefixed_attributes = ",\n    ".join(
                [f"Nodes.{attr} AS {attr}" for attr in return_attributes]
            )
            query += f"  PRINT Nodes[\n    {prefixed_attributes}\n  ];"
        else:
            query += "  PRINT Nodes;"

        query += "\n}"
        return query.strip()

    def _create_gsql_get_edges(self, spec: EdgeSpec) -> str:
        """
        Core function to generate a query based on an EdgeSpec object.
        """
        source_types = self._format_type_set(spec.source_node_type_set)
        edge_types = self._format_type_set(spec.edge_type_set)
        target_types = self._format_type_set(spec.target_node_type_set)

        # Build FROM clause triple
        source_part = (
            f"{spec.source_node_alias}:{source_types}"
            if source_types
            else spec.source_node_alias
        )
        edge_part = f"{spec.edge_alias}:{edge_types}" if edge_types else spec.edge_alias
        target_part = (
            f"{spec.target_node_alias}:{target_types}"
            if target_types
            else spec.target_node_alias
        )

        from_clause = f"FROM ({source_part}) -[{edge_part}]- ({target_part})"

        # Build SELECT clause
        select_items = [spec.source_node_alias, spec.target_node_alias]
        if spec.return_attributes:
            attrs = (
                [spec.return_attributes]
                if isinstance(spec.return_attributes, str)
                else spec.return_attributes
            )
            for attr in attrs:
                select_items.append(f"{spec.edge_alias}.{attr}")

        select_clause = f"SELECT {', '.join(select_items)} INTO T"

        # Optional clauses
        where_clause = (
            f"  WHERE {spec.filter_expression}" if spec.filter_expression else ""
        )
        limit_clause = f"  LIMIT {spec.limit}" if spec.limit else ""

        # Compose query
        query = f"""
INTERPRET QUERY() FOR GRAPH {self._graph_name} SYNTAX V3 {{
  {select_clause}
  {from_clause}
"""
        if where_clause:
            query += f"{where_clause}\n"
        if limit_clause:
            query += f"{limit_clause}\n"
        query += """  ;
  PRINT T;
}"""

        return query.strip()

    def _create_gsql_get_neighbors(
        self, spec: NeighborSpec
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Core function to generate a GSQL query based on a NeighborSpec object.
        """
        # Normalize fields to lists
        params = {
            "start_nodes": (
                [spec.start_nodes]
                if isinstance(spec.start_nodes, str)
                else spec.start_nodes
            )
        }
        return_attributes = (
            [spec.return_attributes]
            if isinstance(spec.return_attributes, str)
            else spec.return_attributes
        )

        # Handle filter expression
        filter_expression = spec.filter_expression
        filter_expression_str = (
            filter_expression if isinstance(filter_expression, str) else None
        )

        # Prepare components
        start_node_type = spec.start_node_type
        edge_types_str = (
            f"(({'|'.join(spec.edge_type_set)}):{spec.edge_alias})"
            if spec.edge_type_set and len(spec.edge_type_set) > 1
            else f"({'|'.join(spec.edge_type_set)}:{spec.edge_alias})"
            if spec.edge_type_set is not None
            else f"(:{spec.edge_alias})"
        )
        target_node_types_str = (
            f"(({'|'.join(spec.target_node_type_set)}))"
            if spec.target_node_type_set and len(spec.target_node_type_set) > 1
            else f"{'|'.join(spec.target_node_type_set)}"
            if spec.target_node_type_set is not None
            else ""
        )

        where_clause = (
            f"    WHERE {filter_expression_str}" if filter_expression_str else ""
        )
        limit_clause = f"    LIMIT {spec.limit}" if spec.limit else ""

        # Generate the query
        s_alias = spec.start_node_alias
        t_alias = spec.target_node_alias
        query = f"""
INTERPRET QUERY(
  SET<VERTEX<{start_node_type}>> start_nodes
) FOR GRAPH {self._graph_name} {{
  Nodes = {{start_nodes}};
  Neighbors =
    SELECT {t_alias}
    FROM Nodes:{s_alias} -{edge_types_str}- {target_node_types_str}:{t_alias}
"""
        if where_clause:
            query += f"{where_clause}\n"
        if limit_clause:
            query += f"{limit_clause}\n"

        query += "  ;\n"

        # Add PRINT statement
        if return_attributes:
            prefixed_attributes = ",\n    ".join(
                [f"Neighbors.{attr} AS {attr}" for attr in return_attributes]
            )
            query += f"  PRINT Neighbors[\n    {prefixed_attributes}\n  ];"
        else:
            query += "  PRINT Neighbors;"

        query += "\n}"
        return (query.strip(), params)

    def _initialize_empty_result(
        self, output_type: Literal["DataFrame", "List"]
    ) -> pd.DataFrame | List:
        if output_type == "DataFrame":
            return pd.DataFrame()
        elif output_type == "List":
            return []

    def _format_type_set(
        self, types: Optional[Set[str]], wrap_always: bool = False
    ) -> str:
        """
        Format a set of types for GSQL V3 syntax:
        - If None: return ""
        - If one type: return it as-is
        - If multiple types: return (type1|type2)
        - If wrap_always: force parentheses even for one type
        """
        if types is None:
            return ""
        type_str = "|".join(sorted(types))
        if len(types) > 1 or wrap_always:
            return f"({type_str})"
        return type_str
