# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

from typing import Any, Dict, List
from tigergraphx.config import (
    NodeSchema,
    EdgeSchema,
    AttributeSchema,
)


class SchemaChangeBuilder:
    def __init__(self):
        # Node operations
        self.nodes_to_add: Dict[str, NodeSchema] = {}
        self.nodes_to_drop: List[str] = []

        # Alter node operations
        self.nodes_to_alter_add_attrs: Dict[str, Dict[str, AttributeSchema]] = {}
        self.nodes_to_alter_drop_attrs: Dict[str, List[str]] = {}

        # Edge operations
        self.edges_to_add: Dict[str, EdgeSchema] = {}
        self.edges_to_drop: List[str] = []

        # Alter edge operations
        self.edges_to_alter_add_attrs: Dict[str, Dict[str, AttributeSchema]] = {}
        self.edges_to_alter_drop_attrs: Dict[str, List[str]] = {}

    # ---------------- Node/Edge add/drop methods ----------------
    def add_node_type(self, name: str, schema: NodeSchema):
        self.nodes_to_add[name] = schema

    def drop_node_type(self, name: str):
        self.nodes_to_drop.append(name)

    def add_node_attribute(
        self,
        node_name: str,
        attr_name: str,
        schema: AttributeSchema,
    ):
        self.nodes_to_alter_add_attrs.setdefault(node_name, {})[attr_name] = schema

    def drop_node_attribute(self, node_name: str, attr_name: str):
        self.nodes_to_alter_drop_attrs.setdefault(node_name, []).append(attr_name)

    def add_edge_type(self, name: str, schema: EdgeSchema):
        self.edges_to_add[name] = schema

    def drop_edge_type(self, name: str):
        self.edges_to_drop.append(name)

    def add_edge_attribute(
        self,
        edge_name: str,
        attr_name: str,
        schema: AttributeSchema,
    ):
        self.edges_to_alter_add_attrs.setdefault(edge_name, {})[attr_name] = schema

    def drop_edge_attribute(self, edge_name: str, attr_name: str):
        self.edges_to_alter_drop_attrs.setdefault(edge_name, []).append(attr_name)

    # ---------------- Payload conversion ----------------
    def build_payload(self) -> Dict:
        payload = {}

        # Add nodes
        if self.nodes_to_add:
            payload["addVertexTypes"] = [
                self._node_to_payload(name, schema)
                for name, schema in self.nodes_to_add.items()
            ]

        # Add edges
        if self.edges_to_add:
            payload["addEdgeTypes"] = [
                self._edge_to_payload(name, schema)
                for name, schema in self.edges_to_add.items()
            ]

        # Alter nodes
        if any(
            [
                self.nodes_to_alter_add_attrs,
                self.nodes_to_alter_drop_attrs,
            ]
        ):
            payload["alterVertexTypes"] = self._build_alter_vertex_payload()

        # Alter edges
        if any([self.edges_to_alter_add_attrs, self.edges_to_alter_drop_attrs]):
            payload["alterEdgeTypes"] = self._build_alter_edge_payload()

        # Drop nodes/edges
        if self.nodes_to_drop:
            payload["dropVertexTypes"] = self.nodes_to_drop
        if self.edges_to_drop:
            payload["dropEdgeTypes"] = self.edges_to_drop

        return payload

    # ---------------- Helpers ----------------
    def _node_to_payload(self, name: str, schema: NodeSchema) -> Dict:
        """Convert a NodeSchema into the payload format for schema change job."""
        primary_key_name = schema.primary_key
        primary_key_type = schema.attributes[primary_key_name].data_type.value

        attributes = [
            {"AttributeName": k, "AttributeType": {"Name": v.data_type.value}}
            for k, v in schema.attributes.items()
            if k != primary_key_name
        ]

        return {
            "Name": name,
            "PrimaryId": {
                "AttributeName": primary_key_name,
                "AttributeType": {"Name": primary_key_type},
            },
            "Attributes": attributes,
            "Config": {
                "STATS": "OUTDEGREE_BY_EDGETYPE",
                "PRIMARY_ID_AS_ATTRIBUTE": "true",
            },
        }

    def _edge_to_payload(self, name: str, schema: EdgeSchema) -> Dict:
        """Convert an EdgeSchema into the payload format for schema change job."""
        attributes_payload = []

        for attr_name, attr_schema in schema.attributes.items():
            attr_dict = {
                "AttributeName": attr_name,
                "AttributeType": {"Name": attr_schema.data_type.value},
            }
            if (
                isinstance(schema.discriminator, set)
                and attr_name in schema.discriminator
            ):
                attr_dict["IsDiscriminator"] = True
            elif (
                isinstance(schema.discriminator, str)
                and attr_name == schema.discriminator
            ):
                attr_dict["IsDiscriminator"] = True
            attributes_payload.append(attr_dict)

        config = (
            {"REVERSE_EDGE": schema.reverse_edge_name}
            if schema.reverse_edge_name
            else {}
        )

        return {
            "Name": name,
            "IsDirected": schema.is_directed_edge,
            "FromVertexTypeName": schema.from_node_type,
            "ToVertexTypeName": schema.to_node_type,
            "Attributes": attributes_payload,
            "Config": config,
        }

    def _build_alter_vertex_payload(self) -> List[Dict]:
        alter_payload = []
        node_names = set(
            list(self.nodes_to_alter_add_attrs.keys())
            + list(self.nodes_to_alter_drop_attrs.keys())
        )
        for node in node_names:
            entry: Dict[str, Any] = {"name": node}
            if node in self.nodes_to_alter_add_attrs:
                entry["addAttributes"] = [
                    {"AttributeName": k, "AttributeType": {"Name": v.data_type.value}}
                    for k, v in self.nodes_to_alter_add_attrs[node].items()
                ]
            if node in self.nodes_to_alter_drop_attrs:
                entry["dropAttributes"] = self.nodes_to_alter_drop_attrs[node]
            alter_payload.append(entry)
        return alter_payload

    def _build_alter_edge_payload(self) -> List[Dict]:
        alter_payload = []
        edge_names = set(
            list(self.edges_to_alter_add_attrs.keys())
            + list(self.edges_to_alter_drop_attrs.keys())
        )
        for edge in edge_names:
            entry: Dict[str, Any] = {"name": edge}
            if edge in self.edges_to_alter_add_attrs:
                entry["addAttributes"] = [
                    {"AttributeName": k, "AttributeType": {"Name": v.data_type.value}}
                    for k, v in self.edges_to_alter_add_attrs[edge].items()
                ]
            if edge in self.edges_to_alter_drop_attrs:
                entry["dropAttributes"] = self.edges_to_alter_drop_attrs[edge]
            alter_payload.append(entry)
        return alter_payload
