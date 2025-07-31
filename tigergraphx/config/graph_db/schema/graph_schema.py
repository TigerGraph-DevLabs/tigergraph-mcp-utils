# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

from typing import Dict
from pydantic import Field, model_validator

from .node_schema import NodeSchema
from .edge_schema import EdgeSchema
from .reserved_keywords import is_reserved_keyword

from tigergraphx.config import BaseConfig


class GraphSchema(BaseConfig):
    """
    Schema for a graph, including nodes and edges.
    """

    graph_name: str = Field(description="The name of the graph.")
    nodes: Dict[str, NodeSchema] = Field(
        description="A dictionary of node type names to their schemas."
    )
    edges: Dict[str, EdgeSchema] = Field(
        description="A dictionary of edge type names to their schemas."
    )

    @model_validator(mode="after")
    def validate_edge_references(self) -> "GraphSchema":
        """
        Ensure all edges reference existing nodes in the graph schema.

        Returns:
            The validated graph schema.

        Raises:
            ValueError: If any edge references undefined node types.
        """
        node_types = set(self.nodes.keys())
        missing_node_edges = [
            f"Edge '{edge_type}' requires nodes '{edge.from_node_type}' and '{edge.to_node_type}' "
            f"to be defined"
            for edge_type, edge in self.edges.items()
            if edge.from_node_type not in node_types
            or edge.to_node_type not in node_types
        ]
        if missing_node_edges:
            raise ValueError(
                f"Invalid edges in schema for graph '{self.graph_name}': {'; '.join(missing_node_edges)}"
            )
        return self

    @model_validator(mode="after")
    def validate_reserved_keywords(self) -> "GraphSchema":
        """
        Ensure graph name, node type names, and edge type names are not reserved keywords.

        Returns:
            The validated graph schema.

        Raises:
            ValueError: If any name is a reserved keyword.
        """
        violations = []

        if is_reserved_keyword(self.graph_name):
            violations.append(f"Graph name '{self.graph_name}' is a reserved keyword.")

        for node_type in self.nodes:
            if is_reserved_keyword(node_type):
                violations.append(f"Node type '{node_type}' is a reserved keyword.")

        for edge_type in self.edges:
            if is_reserved_keyword(edge_type):
                violations.append(f"Edge type '{edge_type}' is a reserved keyword.")

        if violations:
            raise ValueError(
                f"Invalid schema for graph '{self.graph_name}': {'; '.join(violations)}"
            )

        return self
