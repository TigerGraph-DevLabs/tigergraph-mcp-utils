# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

from typing import Any, Dict, Set
from pydantic import Field, model_validator

from .attribute_schema import AttributeSchema, AttributesType, create_attribute_schema
from .reserved_keywords import is_reserved_keyword

from tigergraphx.config import BaseConfig


class EdgeSchema(BaseConfig):
    """
    Schema for a graph edge type.
    """

    is_directed_edge: bool = Field(
        default=False, description="Whether the edge is directed."
    )
    from_node_type: str = Field(description="The type of the source node.")
    to_node_type: str = Field(description="The type of the target node.")
    discriminator: Set[str] | str = Field(
        default_factory=set,
        description="An attribute or set of attributes that uniquely identifies an edge in a graph, "
        "distinguishing it from other edges with the same source and target.",
    )
    attributes: Dict[str, AttributeSchema] = Field(
        default_factory=dict,
        description="A dictionary of attribute names to their schemas.",
    )

    @model_validator(mode="before")
    def parse_attributes(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse shorthand attributes into full AttributeSchema.

        Args:
            values: Input values.

        Returns:
            Parsed values with attributes as AttributeSchema.
        """
        if isinstance(values.get("discriminator"), str):
            values["discriminator"] = {values["discriminator"]}

        attributes = values.get("attributes", {})
        if attributes:
            values["attributes"] = {
                k: create_attribute_schema(v) for k, v in attributes.items()
            }
        return values

    @model_validator(mode="after")
    def validate_discriminator_and_attributes(self) -> "EdgeSchema":
        """
        Validate that every discriminator is present in attributes.

        Returns:
            The validated edge schema.

        Raises:
            ValueError: If any discriminator is not defined in attributes.
        """
        if isinstance(self.discriminator, str):
            if self.discriminator not in self.attributes:
                raise ValueError(
                    f"Edge identifier '{self.discriminator}' is not defined in attributes."
                )
        else:
            for attribute in self.discriminator:
                if attribute not in self.attributes:
                    raise ValueError(
                        f"Edge identifier '{attribute}' is not defined in attributes."
                    )
        return self

    @model_validator(mode="after")
    def validate_reserved_keywords(self) -> "EdgeSchema":
        for attr_name in self.attributes:
            if is_reserved_keyword(attr_name):
                raise ValueError(f"Attribute name '{attr_name}' is a reserved keyword.")

        return self


def create_edge_schema(
    is_directed_edge: bool,
    from_node_type: str,
    to_node_type: str,
    attributes: AttributesType = {},
) -> EdgeSchema:
    """
    Create an EdgeSchema with simplified syntax.

    Args:
        is_directed_edge: Whether the edge is directed.
        from_node_type: The source node type.
        to_node_type: The target node type.
        attributes: Attributes for the edge.

    Returns:
        The created EdgeSchema.
    """
    attribute_schemas = {
        name: create_attribute_schema(attr) for name, attr in attributes.items()
    }
    return EdgeSchema(
        is_directed_edge=is_directed_edge,
        from_node_type=from_node_type,
        to_node_type=to_node_type,
        attributes=attribute_schemas,
    )
