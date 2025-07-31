import pytest
from tigergraphx.config import (
    DataType,
    AttributeSchema,
    EdgeSchema,
)


class TestEdgeSchema:
    def test_edge_schema_valid_set(self):
        """Test creating a valid EdgeSchema."""
        attributes = {
            "weight": AttributeSchema(data_type=DataType.DOUBLE),
            "date": AttributeSchema(data_type=DataType.DATETIME),
            "amount": AttributeSchema(data_type=DataType.DOUBLE),
        }
        edge = EdgeSchema(
            is_directed_edge=True,
            from_node_type="NodeA",
            to_node_type="NodeB",
            discriminator={"date", "amount"},
            attributes=attributes,
        )
        assert edge.is_directed_edge is True
        assert edge.from_node_type == "NodeA"
        assert edge.to_node_type == "NodeB"
        assert edge.discriminator == {"date", "amount"}

    def test_edge_schema_valid_str(self):
        """Test creating a valid EdgeSchema."""
        attributes = {
            "weight": AttributeSchema(data_type=DataType.DOUBLE),
            "date": AttributeSchema(data_type=DataType.DATETIME),
            "amount": AttributeSchema(data_type=DataType.DOUBLE),
        }
        edge = EdgeSchema(
            is_directed_edge=True,
            from_node_type="NodeA",
            to_node_type="NodeB",
            discriminator="date",
            attributes=attributes,
        )
        assert edge.is_directed_edge is True
        assert edge.from_node_type == "NodeA"
        assert edge.to_node_type == "NodeB"
        assert edge.discriminator == {"date"}

    def test_edge_schema_invalid_attribute(self):
        """Test EdgeSchema with invalid attribute default value."""
        with pytest.raises(TypeError, match="must be of type float or int"):
            EdgeSchema(
                is_directed_edge=True,
                from_node_type="NodeA",
                to_node_type="NodeB",
                discriminator={"date", "amount"},
                attributes={
                    "weight": AttributeSchema(
                        data_type=DataType.DOUBLE, default_value="invalid"
                    ),
                },
            )

    def test_edge_schema_reserved_keyword_in_attributes(self):
        """Test EdgeSchema with a reserved keyword as attribute name."""
        attributes = {
            "weight": AttributeSchema(data_type=DataType.DOUBLE),
            "from": AttributeSchema(data_type=DataType.STRING),
        }
        with pytest.raises(
            ValueError, match="Attribute name 'from' is a reserved keyword."
        ):
            EdgeSchema(
                is_directed_edge=True,
                from_node_type="NodeA",
                to_node_type="NodeB",
                attributes=attributes,
            )
