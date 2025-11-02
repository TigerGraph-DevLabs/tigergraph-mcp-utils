# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

import logging
from typing import Dict, List, Literal, Optional
from pathlib import Path

from .base_manager import BaseManager

from tigergraphx.core.graph_context import GraphContext
from tigergraphx.config import (
    GraphSchema,
    TigerGraphConnectionConfig,
    NodeSchema,
    EdgeSchema,
    AttributeSchema,
)

from .schema_change import SchemaChangeBuilder


logger = logging.getLogger(__name__)


class SchemaManager(BaseManager):
    def __init__(self, context: GraphContext):
        super().__init__(context)

    def get_schema(self, format: Literal["json", "dict"] = "dict") -> str | Dict:
        if format == "json":
            return self._graph_schema.model_dump_json()
        return self._graph_schema.model_dump()

    def create_schema(self, drop_existing_graph=False) -> bool:
        # Check whether the graph exists
        is_graph_existing = self._check_graph_exists()

        if drop_existing_graph and is_graph_existing:
            self.drop_graph()

        if not is_graph_existing or drop_existing_graph:
            # Create schema
            gsql_graph_schema = self._create_gsql_graph_schema()
            logger.info(f"Creating schema for graph: {self._graph_name}...")
            result = self._tigergraph_api.gsql(gsql_graph_schema)
            logger.debug(f"GSQL response: {result}")
            if f"The graph {self._graph_name} is created" not in result:
                error_msg = f"Graph creation failed. GSQL response: {result}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            if "Successfully created schema change jobs" not in result:
                error_msg = (
                    f"Schema change job creation failed. GSQL response: {result}"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            if "Local schema change succeeded" not in result:
                error_msg = f"Schema change failed. GSQL response: {result}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            if "Successfully dropped jobs" not in result:
                error_msg = f"Schema change job cleanup failed. GSQL response: {result}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            logger.info("Graph schema created successfully.")

            # Add vector attributes
            gsql_add_vector_attr = self._create_gsql_add_vector_attr()
            if gsql_add_vector_attr:
                logger.info(
                    f"Adding vector attribute(s) for graph: {self._graph_name}..."
                )
                result = self._tigergraph_api.gsql(gsql_add_vector_attr)
                logger.debug(f"GSQL response: {result}")
                if f"Using graph '{self._graph_name}'" not in result:
                    error_msg = f"Failed to use graph '{self._graph_name}'. GSQL response: {result}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                if "Successfully created schema change jobs" not in result:
                    error_msg = (
                        f"Schema change job creation failed. GSQL response: {result}"
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                if "Local schema change succeeded" not in result:
                    error_msg = f"Schema change failed. GSQL response: {result}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                if "Successfully dropped jobs" not in result:
                    error_msg = (
                        f"Schema change job cleanup failed. GSQL response: {result}"
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                if "Query installation finished" not in result:
                    error_msg = f"Query installation failed. GSQL response: {result}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                logger.info("Vector attribute(s) added successfully.")

            return True

        logger.debug(
            f"Graph '{self._graph_name}' already exists. Skipping graph creation."
        )
        return False

    def drop_graph(self) -> None:
        logger.info(f"Dropping graph: {self._graph_name}...")
        result = self._tigergraph_api.drop_graph(self._graph_name)
        logger.debug(result)
        if "Successfully dropped graph" not in result:
            error_msg = f"Failed to drop the graph. GSQL response: {result}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        logger.info("Graph dropped successfully.")

    # -------- Schema Change Operations --------
    def apply_schema_changes(
        self,
        add_nodes: Optional[Dict[str, NodeSchema | Dict | str | Path]] = None,
        drop_nodes: Optional[List[str]] = None,
        add_node_attributes: Optional[
            Dict[str, Dict[str, AttributeSchema | Dict | str | Path]]
        ] = None,
        drop_node_attributes: Optional[Dict[str, List[str]]] = None,
        add_edges: Optional[Dict[str, EdgeSchema | Dict | str | Path]] = None,
        drop_edges: Optional[List[str]] = None,
        add_edge_attributes: Optional[
            Dict[str, Dict[str, AttributeSchema | Dict | str | Path]]
        ] = None,
        drop_edge_attributes: Optional[Dict[str, List[str]]] = None,
    ) -> bool:
        """
        Apply multiple schema changes in a single schema change job.

        Returns:
            True if the schema change job was executed successfully, False if no changes were applied.
        """
        builder = SchemaChangeBuilder()

        add_nodes = add_nodes or {}
        drop_nodes = drop_nodes or []
        add_node_attributes = add_node_attributes or {}
        drop_node_attributes = drop_node_attributes or {}
        add_edges = add_edges or {}
        drop_edges = drop_edges or []
        add_edge_attributes = add_edge_attributes or {}
        drop_edge_attributes = drop_edge_attributes or {}

        if not (
            add_nodes
            or drop_nodes
            or add_node_attributes
            or drop_node_attributes
            or add_edges
            or drop_edges
            or add_edge_attributes
            or drop_edge_attributes
        ):
            return False

        # Add nodes
        for node_name, schema in add_nodes.items():
            if node_name in self._graph_schema.nodes:
                raise ValueError(
                    f"Node type '{node_name}' already exists in the graph schema."
                )
            schema = NodeSchema.ensure_config(schema)
            builder.add_node_type(node_name, schema)
            self._graph_schema.nodes[node_name] = schema

        # Drop nodes
        for node_name in drop_nodes:
            if node_name not in self._graph_schema.nodes:
                raise ValueError(
                    f"Node type '{node_name}' does not exist in the graph schema."
                )
            builder.drop_node_type(node_name)
            del self._graph_schema.nodes[node_name]

        # Add node attributes
        for node_name, attrs in add_node_attributes.items():
            if node_name not in self._graph_schema.nodes:
                raise ValueError(
                    f"Node type '{node_name}' does not exist to add attributes."
                )
            schema = self._graph_schema.nodes[node_name]
            for attr_name, attr_type in attrs.items():
                if attr_name in schema.attributes:
                    raise ValueError(
                        f"Attribute '{attr_name}' already exists in node '{node_name}'."
                    )
                attr_type = AttributeSchema.ensure_config(attr_type)
                schema.attributes[attr_name] = attr_type
                builder.add_node_attribute(node_name, attr_name, attr_type)

        # Drop node attributes
        for node_name, attrs in drop_node_attributes.items():
            if node_name not in self._graph_schema.nodes:
                raise ValueError(
                    f"Node type '{node_name}' does not exist to drop attributes."
                )
            schema = self._graph_schema.nodes[node_name]
            for attr_name in attrs:
                if attr_name not in schema.attributes:
                    raise ValueError(
                        f"Attribute '{attr_name}' does not exist in node '{node_name}'."
                    )
                del schema.attributes[attr_name]
                builder.drop_node_attribute(node_name, attr_name)

        # Add edges
        for edge_name, schema in add_edges.items():
            if edge_name in self._graph_schema.edges:
                raise ValueError(
                    f"Edge type '{edge_name}' already exists in the graph schema."
                )
            schema = EdgeSchema.ensure_config(schema)
            schema.set_default_reverse_edge(edge_name)
            builder.add_edge_type(edge_name, schema)
            self._graph_schema.edges[edge_name] = schema

        # Drop edges
        for edge_name in drop_edges:
            if edge_name not in self._graph_schema.edges:
                raise ValueError(
                    f"Edge type '{edge_name}' does not exist in the graph schema."
                )
            builder.drop_edge_type(edge_name)
            del self._graph_schema.edges[edge_name]

        # Add edge attributes
        for edge_name, attrs in add_edge_attributes.items():
            if edge_name not in self._graph_schema.edges:
                raise ValueError(
                    f"Edge type '{edge_name}' does not exist to add attributes."
                )
            schema = self._graph_schema.edges[edge_name]
            for attr_name, attr_type in attrs.items():
                if attr_name in schema.attributes:
                    raise ValueError(
                        f"Attribute '{attr_name}' already exists in edge '{edge_name}'."
                    )
                attr_type = AttributeSchema.ensure_config(attr_type)
                schema.attributes[attr_name] = attr_type
                builder.add_edge_attribute(edge_name, attr_name, attr_type)

        # Drop edge attributes
        for edge_name, attrs in drop_edge_attributes.items():
            if edge_name not in self._graph_schema.edges:
                raise ValueError(
                    f"Edge type '{edge_name}' does not exist to drop attributes."
                )
            schema = self._graph_schema.edges[edge_name]
            for attr_name in attrs:
                if attr_name not in schema.attributes:
                    raise ValueError(
                        f"Attribute '{attr_name}' does not exist in edge '{edge_name}'."
                    )
                del schema.attributes[attr_name]
                builder.drop_edge_attribute(edge_name, attr_name)

        # Execute the schema change job
        job_name = f"schema_change_{self._graph_name}"
        return self._execute_schema_change_job(builder, job_name)

    def add_node_type(self, name: str, schema: NodeSchema | Dict | str | Path) -> bool:
        """Add a single node type to the graph schema."""
        return self.apply_schema_changes(add_nodes={name: schema})

    def add_node_types(self, nodes: Dict[str, NodeSchema | Dict | str | Path]) -> bool:
        """Add multiple node types to the graph schema."""
        return self.apply_schema_changes(add_nodes=nodes)

    def drop_node_type(self, name: str) -> bool:
        """Drop a single node type from the graph schema."""
        return self.apply_schema_changes(drop_nodes=[name])

    def drop_node_types(self, node_names: List[str]) -> bool:
        """Drop multiple node types from the graph schema."""
        return self.apply_schema_changes(drop_nodes=node_names)

    def add_edge_type(self, name: str, schema: EdgeSchema | Dict | str | Path) -> bool:
        """Add a single edge type to the graph schema."""
        return self.apply_schema_changes(add_edges={name: schema})

    def add_edge_types(self, edges: Dict[str, EdgeSchema | Dict | str | Path]) -> bool:
        """Add multiple edge types to the graph schema."""
        return self.apply_schema_changes(add_edges=edges)

    def drop_edge_type(self, name: str) -> bool:
        """Drop a single edge type from the graph schema."""
        return self.apply_schema_changes(drop_edges=[name])

    def drop_edge_types(self, edge_names: List[str]) -> bool:
        """Drop multiple edge types from the graph schema."""
        return self.apply_schema_changes(drop_edges=edge_names)

    def add_node_attributes(
        self, node_attributes: Dict[str, Dict[str, AttributeSchema | Dict | str | Path]]
    ) -> bool:
        """Add attributes to nodes in the graph schema."""
        return self.apply_schema_changes(add_node_attributes=node_attributes)

    def drop_node_attributes(self, node_attributes: Dict[str, List[str]]) -> bool:
        """Drop attributes from nodes in the graph schema."""
        return self.apply_schema_changes(drop_node_attributes=node_attributes)

    def add_edge_attributes(
        self, edge_attributes: Dict[str, Dict[str, AttributeSchema | Dict | str | Path]]
    ) -> bool:
        """Add attributes to edges in the graph schema."""
        return self.apply_schema_changes(add_edge_attributes=edge_attributes)

    def drop_edge_attributes(self, edge_attributes: Dict[str, List[str]]) -> bool:
        """Drop attributes from edges in the graph schema."""
        return self.apply_schema_changes(drop_edge_attributes=edge_attributes)

    def _check_graph_exists(self) -> bool:
        """Check if the specified graph name exists in the gsql_script."""
        result = self._tigergraph_api.gsql(f"USE Graph {self._graph_name}")
        logger.debug(
            "Graph existence check for %s: %s",
            self._graph_name,
            "exists" if "Using graph" in result else "does not exist",
        )
        return "Using graph" in result

    def _create_gsql_graph_schema(self) -> str:
        # Extracting node attributes
        graph_schema = self._graph_schema
        node_definitions = []
        for node_name, node_schema in graph_schema.nodes.items():
            primary_key_name = node_schema.primary_key

            # Extract the primary ID type
            primary_key_type = node_schema.attributes[primary_key_name].data_type.value

            # Build attribute string excluding the primary ID, since it’s declared separately
            node_attr_str = ", ".join(
                [
                    f"{attribute_name} {attribute_schema.data_type.value}"
                    for attribute_name, attribute_schema in node_schema.attributes.items()
                    if attribute_name != primary_key_name
                ]
            )

            # Append the vertex definition with the dynamic primary ID
            node_definitions.append(
                f"ADD VERTEX {node_name}(PRIMARY_ID {primary_key_name} {primary_key_type}"
                + (f", {node_attr_str}" if node_attr_str else "")
                + ') WITH PRIMARY_ID_AS_ATTRIBUTE="true";'
            )

        # Extracting edge attributes
        edge_definitions = []
        for edge_name, edge_schema in graph_schema.edges.items():
            edge_attr_str = []

            # Separate out the regular attributes and discriminator attributes
            regular_attrs = []
            discriminator_attrs = []
            for attribute_name, attribute_schema in edge_schema.attributes.items():
                if attribute_name in edge_schema.discriminator:
                    # This attribute is part of the edge identifier
                    discriminator_attrs.append(
                        f"{attribute_name} {attribute_schema.data_type.value}"
                    )
                else:
                    # This attribute is a regular edge attribute
                    regular_attrs.append(
                        f"{attribute_name} {attribute_schema.data_type.value}"
                    )

            # Combine regular and discriminator attributes
            if discriminator_attrs:
                discriminator_str = f"DISCRIMINATOR({', '.join(discriminator_attrs)})"
                edge_attr_str.append(discriminator_str)

            # Adding regular attributes to edge definition string
            if regular_attrs:
                edge_attr_str.append(", ".join(regular_attrs))

            # Construct the edge definition, with conditional attribute string and direction
            edge_type_str = "DIRECTED" if edge_schema.is_directed_edge else "UNDIRECTED"
            reverse_edge_clause = (
                f' WITH REVERSE_EDGE="{edge_schema.reverse_edge_name}"'
                if edge_schema.is_directed_edge
                else ""
            )

            edge_definitions.append(
                f"ADD {edge_type_str} EDGE {edge_name}(FROM {edge_schema.from_node_type}, TO {edge_schema.to_node_type}"
                + (f", {', '.join(edge_attr_str)}" if edge_attr_str else "")
                + f"){reverse_edge_clause};"
            )

        # Generating the full schema string
        graph_name = graph_schema.graph_name
        if len(node_definitions) + len(edge_definitions) == 0:
            gsql_script = f"""
# 1. Create graph
CREATE GRAPH {graph_name} ()
"""
        else:
            node_definitions_str = "\n  ".join(node_definitions)
            edge_definitions_str = "\n  ".join(edge_definitions)
            gsql_script = f"""
# 1. Create graph
CREATE GRAPH {graph_name} ()

# 2. Create schema_change job
CREATE SCHEMA_CHANGE JOB schema_change_job_for_graph_{graph_name} FOR GRAPH {graph_name} {{
  # 2.1 Create vertices
  {node_definitions_str}

  # 2.2 Create edges
  {edge_definitions_str}
}}

# 3. Run schema_change job
RUN SCHEMA_CHANGE JOB schema_change_job_for_graph_{graph_name}

# 4. Drop schema_change job
DROP JOB schema_change_job_for_graph_{graph_name}

# 5. Install functions in the package gds
USE GLOBAL
IMPORT PACKAGE GDS
INSTALL FUNCTION GDS.**
"""
        logger.debug("GSQL script for creating graph: %s", gsql_script)
        return gsql_script.strip()

    def _create_gsql_add_vector_attr(self) -> str:
        """
        Generate the GSQL script to add vector attributes to vertices.

        Args:
            graph_schema (GraphSchema): The graph schema configuration.

        Returns:
            str: The generated GSQL script.
        """
        graph_schema = self._graph_schema
        # List to hold GSQL commands for adding vector attributes
        vector_attribute_statements = []

        # List to hold GSQL commands for creating vector search query
        query_statements = []

        # Iterate over all nodes and their vector attributes
        for node_type, node_schema in graph_schema.nodes.items():
            if node_schema.vector_attributes:
                for (
                    vector_attribute_name,
                    vector_attr,
                ) in node_schema.vector_attributes.items():
                    # Extract the fields from VectorAttributeSchema
                    dimension = vector_attr.dimension
                    index_type = vector_attr.index_type
                    data_type = vector_attr.data_type
                    metric = vector_attr.metric

                    # Generate GSQL for each vector attribute in the node schema
                    vector_attribute_statements.append(
                        f"ALTER VERTEX {node_type} ADD VECTOR ATTRIBUTE {vector_attribute_name}"
                        f'(DIMENSION={dimension}, INDEXTYPE="{index_type}", '
                        f'DATATYPE="{data_type}", METRIC="{metric}");'
                    )
                    query_statements.append(
                        f"""
CREATE OR REPLACE QUERY api_search_{node_type}_{vector_attribute_name} (
  UINT k=10,
  LIST<float> query_vector,
  SET<VERTEX> set_candidate
) SYNTAX v3 {{
  MapAccum<Vertex, Float> @@map_node_distance;

  IF set_candidate.size() > 0 THEN
    Candidates = {{set_candidate}};
    Nodes = vectorSearch(
      {{{node_type}.{vector_attribute_name}}},
      query_vector,
      k,
      {{ distance_map: @@map_node_distance, candidate_set: Candidates}}
    );
  ELSE
    Nodes = vectorSearch(
      {{{node_type}.{vector_attribute_name}}},
      query_vector,
      k,
      {{ distance_map: @@map_node_distance}}
    );
  END;

  PRINT @@map_node_distance AS map_node_distance;
  PRINT Nodes;
}}
""".strip()
                    )

        # Combine all statements and wrap them into the full GSQL script
        if len(vector_attribute_statements) == 0:
            gsql_script = ""
        else:
            query_statements.append(
                """
CREATE OR REPLACE QUERY api_fetch(
  SET<VERTEX> input
) SYNTAX v3 {
  Nodes = {input};
  PRINT Nodes WITH VECTOR;
}
""".strip()
            )
            vector_attribute_statements_str = "\n  ".join(vector_attribute_statements)
            query_statements_str = "\n".join(query_statements)
            gsql_script = f"""
# 1. Use graph
USE GRAPH {graph_schema.graph_name}

# 2. Create schema_change job
CREATE SCHEMA_CHANGE JOB add_vector_attr_for_graph_{graph_schema.graph_name} FOR GRAPH {graph_schema.graph_name} {{
  # 2.1 Add vector attributes
  {vector_attribute_statements_str}
}}

# 3. Run schema_change job
RUN SCHEMA_CHANGE JOB add_vector_attr_for_graph_{graph_schema.graph_name}

# 4. Drop schema_change job
DROP JOB add_vector_attr_for_graph_{graph_schema.graph_name}
"""
            if len(query_statements) > 0:
                gsql_script = f"""
{gsql_script}
{query_statements_str}
INSTALL QUERY *
"""
        logger.debug("GSQL script for adding vector attributes: %s", gsql_script)
        return gsql_script.rstrip()

    def _execute_schema_change_job(
        self, builder: SchemaChangeBuilder, job_name: str
    ) -> bool:
        """Create, run, and drop a local schema change job, logging all steps."""
        logger.info(
            f"Running schema change job '{job_name}' on graph: {self._graph_name}..."
        )
        try:
            # Create job
            create_result = self._tigergraph_api.create_local_schema_change_job(
                self._graph_name, job_name, builder.build_payload()
            )
            logger.debug(f"Create job result: {create_result}")
            if "Successfully created schema change job" not in create_result:
                raise RuntimeError(
                    f"Failed to create schema change job: {create_result}"
                )

            # Run job
            run_result = self._tigergraph_api.run_local_schema_change_job(
                self._graph_name, job_name
            )
            logger.debug(f"Run job result: {run_result}")
            if "Schema change job run successfully!" not in run_result:
                raise RuntimeError(f"Failed to run schema change job: {run_result}")

            logger.info(f"Schema change job '{job_name}' executed successfully.")
            return True

        except Exception as e:
            logger.error(f"Schema change job '{job_name}' failed: {e}")
            raise

        finally:
            # Always attempt to drop the job
            try:
                drop_result = self._tigergraph_api.drop_local_schema_change_job(
                    self._graph_name, job_name
                )
                logger.debug(f"Drop job result: {drop_result}")
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to drop schema change job '{job_name}' during cleanup: "
                    f"{cleanup_error}"
                )

    @staticmethod
    def get_schema_from_db(
        graph_name: str,
        tigergraph_connection_config: Optional[
            TigerGraphConnectionConfig | Dict | str | Path
        ] = None,
    ) -> Dict:
        # Create a minimal GraphSchema to initialize the context
        initial_graph_schema = GraphSchema(graph_name=graph_name, nodes={}, edges={})
        context = GraphContext(
            graph_schema=initial_graph_schema,
            tigergraph_connection_config=tigergraph_connection_config,
        )

        # Retrieve the schema from TigerGraph DB
        raw_schema = context.tigergraph_api.get_schema(graph_name)
        logger.debug(f"The raw schema: {raw_schema}")

        # Construct nodes dictionary
        nodes = {}
        for vertex in raw_schema.get("VertexTypes", []):
            primary_id = vertex.get("PrimaryId", {})
            primary_id_as_attr = primary_id.get("PrimaryIdAsAttribute")

            if primary_id_as_attr is not True:
                raise ValueError(
                    f"The node type '{vertex.get('Name', '<unknown>')}' has PrimaryIdAsAttribute unset. "
                    f"TigerGraphX requires the primary ID to be used as an attribute for certain methods. "
                    f"Please set PrimaryIdAsAttribute to True for this node type."
                )

            # Extract regular attributes
            attributes = {
                primary_id["AttributeName"]: {
                    "data_type": primary_id["AttributeType"]["Name"],
                    "default_value": None,
                }
            }
            attributes.update(
                {
                    attr["AttributeName"]: {
                        "data_type": attr["AttributeType"]["Name"],
                        "default_value": attr.get("DefaultValue"),
                    }
                    for attr in vertex.get("Attributes", [])
                }
            )

            # Extract vector attributes
            vector_attributes = {}
            vector_attributes.update(
                {
                    attr["Name"]: {
                        "dimension": attr["Dimension"],
                        "index_type": attr["IndexType"],
                        "data_type": attr["DataType"],
                        "metric": attr["Metric"],
                    }
                    for attr in vertex.get("EmbeddingAttributes", [])
                }
            )

            nodes[vertex["Name"]] = {
                "primary_key": primary_id["AttributeName"],
                "attributes": attributes,
                "vector_attributes": vector_attributes,
            }

        # Construct edges dictionary
        edges = {}
        for edge in raw_schema.get("EdgeTypes", []):
            attributes = {
                attr["AttributeName"]: {
                    "data_type": attr["AttributeType"]["Name"],
                    "default_value": attr.get("DefaultValue"),
                }
                for attr in edge.get("Attributes", [])
            }
            discriminator = {
                attr["AttributeName"]
                for attr in edge.get("Attributes", [])
                if attr.get("IsDiscriminator")
            }

            # Determine reverse edge name
            reverse_edge_name = edge.get("Config", {}).get("REVERSE_EDGE")

            # Precheck: reverse_edge_name must not be None for directed edges
            if edge.get("IsDirected") and not reverse_edge_name:
                raise ValueError(
                    f"Directed edge '{edge['Name']}' must have a reverse edge name defined "
                    f"in 'Config.REVERSE_EDGE'."
                )

            edges[edge["Name"]] = {
                "is_directed_edge": edge["IsDirected"],
                "reverse_edge_name": reverse_edge_name,
                "from_node_type": edge["FromVertexTypeName"],
                "to_node_type": edge["ToVertexTypeName"],
                "discriminator": discriminator,
                "attributes": attributes,
            }

        # Combine into a dictionary format
        graph_schema = {
            "graph_name": graph_name,
            "nodes": nodes,
            "edges": edges,
        }
        logger.debug(f"The generated schema: {graph_schema}")
        return graph_schema
