# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

import logging
from typing import Dict, Literal, Optional
from pathlib import Path

from .base_manager import BaseManager

from tigergraphx.core.graph_context import GraphContext
from tigergraphx.config import GraphSchema, TigerGraphConnectionConfig


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
        gsql_script = self._create_gsql_drop_graph()
        result = self._tigergraph_api.gsql(gsql_script)
        logger.debug(result)
        if f"The graph {self._graph_name} is dropped" not in result:
            error_msg = f"Failed to drop the graph. GSQL response: {result}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        logger.info("Graph dropped successfully.")

    def _check_graph_exists(self) -> bool:
        """Check if the specified graph name exists in the gsql_script."""
        result = self._tigergraph_api.gsql(f"USE Graph {self._graph_name}")
        logger.debug(
            "Graph existence check for %s: %s",
            self._graph_name,
            "exists" if "Using graph" in result else "does not exist",
        )
        return "Using graph" in result

    def _create_gsql_drop_graph(self) -> str:
        # Generating the gsql script to drop graph
        gsql_script = f"""
USE GRAPH {self._graph_name}
DROP QUERY *
DROP JOB *
DROP GRAPH {self._graph_name}
"""
        return gsql_script.strip()

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
                f' WITH REVERSE_EDGE="reverse_{edge_name}"'
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
            edges[edge["Name"]] = {
                "is_directed_edge": edge["IsDirected"],
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
