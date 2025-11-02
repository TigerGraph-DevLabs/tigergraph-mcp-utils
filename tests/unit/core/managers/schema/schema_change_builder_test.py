import pytest

from tigergraphx.config import (
    NodeSchema,
    EdgeSchema,
    AttributeSchema,
    DataType,
)
from tigergraphx.core.managers.schema.schema_change_builder import SchemaChangeBuilder


class TestSchemaChangeBuilder:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.builder = SchemaChangeBuilder()

    def test_add_node_type(self):
        node_schema = NodeSchema(
            primary_key="id",
            attributes={"id": AttributeSchema(data_type=DataType.STRING)},
        )
        self.builder.add_node_type("Person", node_schema)
        payload = self.builder.build_payload()
        assert "addVertexTypes" in payload
        assert payload["addVertexTypes"][0]["Name"] == "Person"
        assert payload["addVertexTypes"][0]["PrimaryId"]["AttributeName"] == "id"

    def test_drop_node_type(self):
        self.builder.drop_node_type("Person")
        payload = self.builder.build_payload()
        assert "dropVertexTypes" in payload
        assert "Person" in payload["dropVertexTypes"]

    def test_add_node_attribute(self):
        attr_schema = AttributeSchema(data_type=DataType.STRING)
        self.builder.add_node_attribute("Person", "name", attr_schema)
        payload = self.builder.build_payload()
        alter_node = payload["alterVertexTypes"][0]
        assert alter_node["name"] == "Person"
        assert alter_node["addAttributes"][0]["AttributeName"] == "name"
        assert alter_node["addAttributes"][0]["AttributeType"]["Name"] == "STRING"

    def test_drop_node_attribute(self):
        self.builder.drop_node_attribute("Person", "name")
        payload = self.builder.build_payload()
        alter_node = payload["alterVertexTypes"][0]
        assert alter_node["name"] == "Person"
        assert "name" in alter_node["dropAttributes"]

    def test_add_edge_type(self):
        edge_schema = EdgeSchema(
            from_node_type="Person", to_node_type="Company", is_directed_edge=True
        )
        self.builder.add_edge_type("works_at", edge_schema)
        payload = self.builder.build_payload()
        edge = payload["addEdgeTypes"][0]
        assert edge["Name"] == "works_at"
        assert edge["IsDirected"] is True
        assert edge["FromVertexTypeName"] == "Person"
        assert edge["ToVertexTypeName"] == "Company"

    def test_drop_edge_type(self):
        self.builder.drop_edge_type("works_at")
        payload = self.builder.build_payload()
        assert "works_at" in payload["dropEdgeTypes"]

    def test_add_edge_attribute(self):
        attr_schema = AttributeSchema(data_type=DataType.INT)
        self.builder.add_edge_attribute("works_at", "since", attr_schema)
        payload = self.builder.build_payload()
        alter_edge = payload["alterEdgeTypes"][0]
        assert alter_edge["name"] == "works_at"
        assert alter_edge["addAttributes"][0]["AttributeName"] == "since"
        assert alter_edge["addAttributes"][0]["AttributeType"]["Name"] == "INT"

    def test_drop_edge_attribute(self):
        self.builder.drop_edge_attribute("works_at", "since")
        payload = self.builder.build_payload()
        alter_edge = payload["alterEdgeTypes"][0]
        assert "since" in alter_edge["dropAttributes"]

    def test_complex_node_and_edge_changes(self):
        # add node + vector attr + edge + edge attr + drops
        node_schema = NodeSchema(
            primary_key="id",
            attributes={"id": AttributeSchema(data_type=DataType.STRING)},
        )
        self.builder.add_node_type("Person", node_schema)
        edge_schema = EdgeSchema(from_node_type="Person", to_node_type="Company")
        self.builder.add_edge_type("works_at", edge_schema)

        payload = self.builder.build_payload()
        # Node
        node = payload["addVertexTypes"][0]
        assert node["Name"] == "Person"
        # Edge
        edge = payload["addEdgeTypes"][0]
        assert edge["Name"] == "works_at"
