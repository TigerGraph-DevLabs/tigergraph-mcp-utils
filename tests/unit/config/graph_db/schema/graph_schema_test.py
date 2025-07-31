import pytest
import json

from tigergraphx.config import (
    DataType,
    AttributeSchema,
    NodeSchema,
    EdgeSchema,
    GraphSchema,
)


class TestGraphSchema:
    def test_graph_schema_valid(self):
        """Test creating a valid GraphSchema."""
        nodes = {
            "NodeA": NodeSchema(
                primary_key="id",
                attributes={
                    "id": AttributeSchema(data_type=DataType.STRING),
                    "name": AttributeSchema(data_type=DataType.STRING),
                },
            ),
            "NodeB": NodeSchema(
                primary_key="id",
                attributes={
                    "id": AttributeSchema(data_type=DataType.STRING),
                    "value": AttributeSchema(data_type=DataType.INT),
                },
            ),
        }
        edges = {
            "edgeA": EdgeSchema(
                is_directed_edge=True,
                from_node_type="NodeA",
                to_node_type="NodeB",
                attributes={"weight": AttributeSchema(data_type=DataType.DOUBLE)},
            )
        }
        graph = GraphSchema(graph_name="TestGraph", nodes=nodes, edges=edges)
        assert graph.graph_name == "TestGraph"
        assert "NodeA" in graph.nodes
        assert "edgeA" in graph.edges

    def test_graph_schema_invalid_edge(self):
        """Test GraphSchema with an edge referencing missing nodes."""
        nodes = {
            "NodeA": NodeSchema(
                primary_key="id",
                attributes={"id": AttributeSchema(data_type=DataType.STRING)},
            )
        }
        edges = {
            "edgeA": EdgeSchema(
                is_directed_edge=True,
                from_node_type="NodeA",
                to_node_type="NodeB",  # NodeB does not exist
                attributes={"weight": AttributeSchema(data_type=DataType.DOUBLE)},
            )
        }
        with pytest.raises(
            ValueError, match="requires nodes 'NodeA' and 'NodeB' to be defined"
        ):
            GraphSchema(graph_name="InvalidGraph", nodes=nodes, edges=edges)

    def test_graph_name_reserved_keyword(self):
        """Graph name should not be a reserved keyword."""
        nodes = {
            "Person": NodeSchema(
                primary_key="id",
                attributes={"id": AttributeSchema(data_type=DataType.STRING)},
            )
        }
        with pytest.raises(ValueError, match="Graph name 'ADD' is a reserved keyword"):
            GraphSchema(graph_name="ADD", nodes=nodes, edges={})

    def test_node_name_reserved_keyword(self):
        """Node type name should not be a reserved keyword."""
        nodes = {
            "ASC": NodeSchema(
                primary_key="id",
                attributes={"id": AttributeSchema(data_type=DataType.STRING)},
            )
        }
        with pytest.raises(ValueError, match="Node type 'ASC' is a reserved keyword"):
            GraphSchema(graph_name="MyGraph", nodes=nodes, edges={})

    def test_edge_name_reserved_keyword(self):
        """Edge type name should not be a reserved keyword."""
        nodes = {
            "NodeA": NodeSchema(
                primary_key="id",
                attributes={"id": AttributeSchema(data_type=DataType.STRING)},
            ),
            "NodeB": NodeSchema(
                primary_key="id",
                attributes={"id": AttributeSchema(data_type=DataType.STRING)},
            ),
        }
        edges = {
            "CASE": EdgeSchema(
                is_directed_edge=True,
                from_node_type="NodeA",
                to_node_type="NodeB",
                attributes={},
            )
        }
        with pytest.raises(ValueError, match="Edge type 'CASE' is a reserved keyword"):
            GraphSchema(graph_name="MyGraph", nodes=nodes, edges=edges)

    def test_ensure_config_from_dict(self):
        """Test ensure_config with a dictionary input."""
        config_dict = {
            "graph_name": "TestGraph",
            "nodes": {
                "NodeA": {
                    "primary_key": "id",
                    "attributes": {"id": {"data_type": "STRING"}},
                }
            },
            "edges": {},
        }
        graph_schema = GraphSchema.ensure_config(config_dict)
        assert graph_schema.graph_name == "TestGraph"
        assert "NodeA" in graph_schema.nodes

    def test_ensure_config_from_yaml(self, tmp_path):
        """Test ensure_config with a YAML file."""
        yaml_content = """
        graph_name: TestGraph
        nodes:
          NodeA:
            primary_key: id
            attributes:
              id:
                data_type: STRING
        edges: {}
        """
        yaml_path = tmp_path / "config.yaml"
        yaml_path.write_text(yaml_content)

        graph_schema = GraphSchema.ensure_config(yaml_path)
        assert graph_schema.graph_name == "TestGraph"
        assert "NodeA" in graph_schema.nodes

    def test_ensure_config_from_json(self, tmp_path):
        """Test ensure_config with a JSON file."""
        json_content = {
            "graph_name": "TestGraph",
            "nodes": {
                "NodeA": {
                    "primary_key": "id",
                    "attributes": {"id": {"data_type": "STRING"}},
                }
            },
            "edges": {},
        }
        json_path = tmp_path / "config.json"
        json_path.write_text(json.dumps(json_content))

        graph_schema = GraphSchema.ensure_config(json_path)
        assert graph_schema.graph_name == "TestGraph"
        assert "NodeA" in graph_schema.nodes

    def test_ensure_config_with_existing_object(self):
        """Test ensure_config with an existing GraphSchema object."""
        existing_schema = GraphSchema(
            graph_name="ExistingGraph",
            nodes={},
            edges={},
        )
        result = GraphSchema.ensure_config(existing_schema)
        assert result == existing_schema

    def test_ensure_config_complex_schema(self):
        """Test ensure_config with a complex schema containing multiple nodes and edges."""
        complex_config = {
            "graph_name": "ComplexGraph",
            "nodes": {
                "User": {
                    "primary_key": "id",
                    "attributes": {
                        "id": {"data_type": "STRING"},
                        "name": {"data_type": "STRING"},
                        "age": {"data_type": "UINT"},
                    },
                },
                "Product": {
                    "primary_key": "id",
                    "attributes": {
                        "id": {"data_type": "STRING"},
                        "name": {"data_type": "STRING"},
                        "price": {"data_type": "DOUBLE"},
                    },
                },
            },
            "edges": {
                "purchased": {
                    "is_directed_edge": True,
                    "from_node_type": "User",
                    "to_node_type": "Product",
                    "attributes": {
                        "purchase_date": {"data_type": "DATETIME"},
                        "quantity": {"data_type": "UINT"},
                    },
                },
                "friend_of": {
                    "is_directed_edge": False,
                    "from_node_type": "User",
                    "to_node_type": "User",
                    "attributes": {
                        "since": {"data_type": "DATETIME"},
                    },
                },
            },
        }

        graph_schema = GraphSchema.ensure_config(complex_config)

        # Assertions for the graph name
        assert graph_schema.graph_name == "ComplexGraph"

        # Assertions for nodes
        assert "User" in graph_schema.nodes
        assert "Product" in graph_schema.nodes
        assert graph_schema.nodes["User"].primary_key == "id"
        assert "name" in graph_schema.nodes["User"].attributes
        assert (
            graph_schema.nodes["Product"].attributes["price"].data_type
            == DataType.DOUBLE
        )

        # Assertions for edges
        assert "purchased" in graph_schema.edges
        assert "friend_of" in graph_schema.edges
        assert graph_schema.edges["purchased"].is_directed_edge is True
        assert (
            graph_schema.edges["purchased"].attributes["quantity"].data_type
            == DataType.UINT
        )
        assert graph_schema.edges["friend_of"].is_directed_edge is False
