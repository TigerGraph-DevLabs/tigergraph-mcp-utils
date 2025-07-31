import pytest

from tigergraphx.config import (
    DataType,
    AttributeSchema,
    VectorAttributeSchema,
    NodeSchema,
)


class TestNodeSchema:
    def test_node_schema_valid(self):
        """Test creating a valid NodeSchema."""
        attributes = {
            "id": AttributeSchema(data_type=DataType.STRING),
            "name": AttributeSchema(
                data_type=DataType.STRING, default_value="Default Name"
            ),
        }
        node = NodeSchema(primary_key="id", attributes=attributes)
        assert node.primary_key == "id"
        assert "id" in node.attributes
        assert node.attributes["name"].default_value == "Default Name"

    def test_node_schema_missing_primary_key(self):
        """Test NodeSchema with a missing primary key in attributes."""
        attributes = {
            "name": AttributeSchema(
                data_type=DataType.STRING, default_value="Default Name"
            ),
        }
        with pytest.raises(
            ValueError, match="Primary key 'id' is not defined in attributes."
        ):
            NodeSchema(primary_key="id", attributes=attributes)

    def test_node_schema_reserved_keyword_in_attribute(self):
        """Test NodeSchema with a reserved keyword as an attribute name."""
        attributes = {
            "id": AttributeSchema(data_type=DataType.STRING),
            "select": AttributeSchema(data_type=DataType.STRING),
        }
        with pytest.raises(
            ValueError, match="Attribute name 'select' is a reserved keyword."
        ):
            NodeSchema(primary_key="id", attributes=attributes)

    def test_node_schema_reserved_keyword_in_vector_attribute(self):
        """Test NodeSchema with a reserved keyword as vector attribute name."""
        attributes = {
            "id": AttributeSchema(data_type=DataType.STRING),
        }
        vector_attributes = {
            "SElEcT": VectorAttributeSchema(dimension=128)
        }
        with pytest.raises(
            ValueError, match="Vector attribute name 'SElEcT' is a reserved keyword."
        ):
            NodeSchema(
                primary_key="id",
                attributes=attributes,
                vector_attributes=vector_attributes,
            )
