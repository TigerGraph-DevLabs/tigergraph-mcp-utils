# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

from typing import Any, Dict, Optional
from pydantic import Field, model_validator

from .attribute_schema import AttributeSchema, AttributesType, create_attribute_schema
from .vector_attribute_schema import (
    VectorAttributeSchema,
    VectorAttributesType,
    create_vector_attribute_schema,
)
from .reserved_keywords import is_reserved_keyword

from tigergraphx.config import BaseConfig


class NodeSchema(BaseConfig):
    """
    Schema for a graph node type.
    """

    primary_key: str = Field(description="The primary key for the node type.")
    attributes: Dict[str, AttributeSchema] = Field(
        default_factory=dict,
        description="A dictionary of attribute names to their schemas.",
    )
    vector_attributes: Dict[str, VectorAttributeSchema] = Field(
        default_factory=dict,
        description="A dictionary of vector attribute names to their schemas.",
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
        attributes = values.get("attributes", {})
        if attributes:
            values["attributes"] = {
                k: create_attribute_schema(v) for k, v in attributes.items()
            }
        vector_attributes = values.get("vector_attributes", {})
        if vector_attributes:
            values["vector_attributes"] = {
                k: create_vector_attribute_schema(v)
                for k, v in vector_attributes.items()
            }
        return values

    @model_validator(mode="after")
    def validate_primary_key_and_attributes(self) -> "NodeSchema":
        """
        Validate that the primary key is present in attributes.

        Returns:
            The validated node schema.

        Raises:
            ValueError: If the primary key is not defined in attributes.
        """
        if self.primary_key not in self.attributes:
            raise ValueError(
                f"Primary key '{self.primary_key}' is not defined in attributes."
            )
        return self

    @model_validator(mode="after")
    def validate_reserved_keywords(self) -> "NodeSchema":
        for attr_name in self.attributes:
            if is_reserved_keyword(attr_name):
                raise ValueError(f"Attribute name '{attr_name}' is a reserved keyword.")

        for vec_attr_name in self.vector_attributes:
            if is_reserved_keyword(vec_attr_name):
                raise ValueError(
                    f"Vector attribute name '{vec_attr_name}' is a reserved keyword."
                )

        return self


def create_node_schema(
    primary_key: str,
    attributes: AttributesType,
    vector_attributes: Optional[VectorAttributesType] = None,
) -> NodeSchema:
    """
    Create a NodeSchema with simplified syntax.

    Args:
        primary_key: The primary key for the node type.
        attributes: Attributes for the node.
        vector_attributes: Vector attributes for the node.

    Returns:
        The created node schema.
    """
    attribute_schemas = {
        name: create_attribute_schema(attr) for name, attr in attributes.items()
    }
    vector_attribute_schemas = {}
    if vector_attributes:
        vector_attribute_schemas = {
            name: create_vector_attribute_schema(attr)
            for name, attr in vector_attributes.items()
        }
    return NodeSchema(
        primary_key=primary_key,
        attributes=attribute_schemas,
        vector_attributes=vector_attribute_schemas,
    )
