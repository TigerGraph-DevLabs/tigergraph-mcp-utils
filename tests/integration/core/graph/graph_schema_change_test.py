import pytest
from typing import Any, Dict, List, Optional

from .base_graph_fixture import BaseGraphFixture

from tigergraphx.core import Graph


class TestGraphSchemaChange(BaseGraphFixture):
    def setup_graph(self):
        """Set up the graph."""
        graph_schema = {
            "graph_name": "SchemaChangeGraph",
            "nodes": {
                "Employee": {
                    "primary_key": "id",
                    "attributes": {
                        "id": "STRING",
                    },
                }
            },
            "edges": {},
        }
        self.G = Graph(
            graph_schema=graph_schema,
            tigergraph_connection_config=self.tigergraph_connection_config,
        )

    @pytest.fixture(autouse=True)
    def setup_graph_and_run_test_case(self):
        """Add nodes and edges before each test case."""
        self.setup_graph()
        yield

    @pytest.fixture(scope="class", autouse=True)
    def drop_graph(self):
        """Drop the graph after all tests are done in the session."""
        yield
        self.setup_graph()
        self.G.drop_graph()

    def test_apply_schema_changes_no_change(self):
        """Test applying schema changes when no changes are provided."""
        # Should execute successfully and return True even if nothing to do
        result = self.G.apply_schema_changes()
        assert result is False

        # Schema should remain unchanged
        self._assert_schema_contains(nodes=["Employee"], should_exist=True)

    def test_apply_schema_changes_add_and_drop_nodes_and_edges(self):
        """Test apply_schema_changes with adding and dropping nodes and edges,
        including edge cases like existing node/edge names and empty changes.
        The schema before and after the test remains the same.
        """
        nodes_to_add: Dict[str, Any] = {
            "Department": {
                "primary_key": "id",
                "attributes": {"id": "STRING", "name": "STRING"},
            },
        }
        edges_to_add: Dict[str, Any] = {
            "mentors": {
                "is_directed_edge": True,
                "from_node_type": "Employee",
                "to_node_type": "Employee",
            },
        }

        # Use try/finally to ensure cleanup
        try:
            # Add nodes and edges
            result = self.G.apply_schema_changes(
                add_nodes=nodes_to_add, add_edges=edges_to_add
            )
            assert result is True
            self._assert_schema_contains(
                nodes=list(nodes_to_add.keys()),
                edges=list(edges_to_add.keys()),
                should_exist=True,
            )

            # Attempt to add nodes/edges that already exist (should raise ValueError)
            with pytest.raises(ValueError):
                self.G.apply_schema_changes(add_nodes=nodes_to_add)
            with pytest.raises(ValueError):
                self.G.apply_schema_changes(add_edges=edges_to_add)
        finally:
            # Drop the nodes and edges to restore schema
            result = self.G.apply_schema_changes(
                drop_nodes=list(nodes_to_add), drop_edges=list(edges_to_add)
            )
            assert result is True
            self._assert_schema_contains(
                nodes=list(nodes_to_add.keys()),
                edges=list(edges_to_add.keys()),
                should_exist=False,
            )

    def test_apply_schema_changes_drop_nonexistent_node(self):
        """Test dropping a node that does not exist raises ValueError."""
        with pytest.raises(
            ValueError, match="Node type 'NonexistentNode' does not exist"
        ):
            self.G.apply_schema_changes(drop_nodes=["NonexistentNode"])

    def test_apply_schema_changes_drop_nonexistent_edge(self):
        """Test dropping an edge that does not exist raises ValueError."""
        with pytest.raises(
            ValueError, match="Edge type 'NonexistentEdge' does not exist"
        ):
            self.G.apply_schema_changes(drop_edges=["NonexistentEdge"])

    def test_apply_schema_changes_add_and_drop_node_attributes(self):
        """Test adding and dropping node attributes."""
        node_attrs_to_add: Dict[str, Any] = {
            "Employee": {
                "name": {"data_type": "STRING"},
                "age": {"data_type": "INT"},
            }
        }

        # Use try/finally to ensure cleanup
        try:
            # Add attributes to Employee
            result = self.G.apply_schema_changes(add_node_attributes=node_attrs_to_add)
            assert result is True
            self._assert_schema_contains(
                node_attributes={"Employee": ["name", "age"]}, should_exist=True
            )

            # Attempt to add attribute that already exists (should raise ValueError)
            with pytest.raises(ValueError):
                self.G.apply_schema_changes(add_node_attributes=node_attrs_to_add)
        finally:
            # Drop attributes to restore schema
            node_attrs_to_drop = {"Employee": ["name", "age"]}
            result = self.G.apply_schema_changes(
                drop_node_attributes=node_attrs_to_drop
            )
            assert result is True
            self._assert_schema_contains(
                node_attributes={"Employee": ["name", "age"]}, should_exist=False
            )

    def test_apply_schema_changes_add_and_drop_edge_attributes(self):
        """Test adding and dropping edge attributes."""
        edge_to_add: Dict[str, Any] = {
            "mentors": {
                "is_directed_edge": True,
                "from_node_type": "Employee",
                "to_node_type": "Employee",
            }
        }

        # Use try/finally to ensure cleanup
        try:
            # Ensure the edge exists first
            self.G.apply_schema_changes(add_edges=edge_to_add)

            # Add attributes to edge
            edge_attrs_to_add: Dict[str, Any] = {
                "mentors": {
                    "since": {"data_type": "DATETIME"},
                    "level": {"data_type": "STRING"},
                }
            }
            result = self.G.apply_schema_changes(add_edge_attributes=edge_attrs_to_add)
            assert result is True
            self._assert_schema_contains(
                edge_attributes={"mentors": ["since", "level"]}, should_exist=True
            )

            # Attempt to add attribute that already exists (should raise ValueError)
            with pytest.raises(ValueError):
                self.G.apply_schema_changes(add_edge_attributes=edge_attrs_to_add)
        finally:
            # Drop attributes and edge to restore schema
            edge_attrs_to_drop = {"mentors": ["since", "level"]}
            self.G.apply_schema_changes(drop_edge_attributes=edge_attrs_to_drop)
            self._assert_schema_contains(
                edge_attributes={"mentors": ["since", "level"]}, should_exist=False
            )
            self.G.apply_schema_changes(drop_edges=list(edge_to_add.keys()))

    def test_add_and_drop_node_type(self):
        """Test adding and dropping a single node type."""
        node_schema = {
            "primary_key": "id",
            "attributes": {"id": "STRING", "name": "STRING"},
        }
        node_name = "Department"

        # Use try/finally to ensure cleanup
        try:
            result = self.G.add_node_type(node_name, node_schema)
            assert result is True
            self._assert_schema_contains(
                nodes=[node_name],
                should_exist=True,
            )
        finally:
            result = self.G.drop_node_type(node_name)
            assert result is True
            self._assert_schema_contains(
                nodes=[node_name],
                should_exist=False,
            )

    def test_add_and_drop_node_types(self):
        """Test adding and dropping multiple node types."""
        nodes: Dict[str, Any] = {
            "Company": {
                "primary_key": "id",
                "attributes": {"id": "STRING", "name": "STRING"},
            },
            "Project": {
                "primary_key": "id",
                "attributes": {"id": "STRING", "name": "STRING"},
            },
        }

        # Use try/finally to ensure cleanup
        try:
            result = self.G.add_node_types(nodes)
            assert result is True
            self._assert_schema_contains(
                nodes=list(nodes.keys()),
                should_exist=True,
            )
        finally:
            result = self.G.drop_node_types(list(nodes.keys()))
            assert result is True
            self._assert_schema_contains(
                nodes=list(nodes.keys()),
                should_exist=False,
            )

    def test_add_and_drop_edge_type(self):
        """Test adding and dropping a single edge type using only Employee nodes."""
        edge_schema = {
            "is_directed_edge": True,
            "from_node_type": "Employee",
            "to_node_type": "Employee",
            "attributes": {"since": {"data_type": "DATETIME"}},
        }
        edge_name = "mentors"

        # Use try/finally to ensure cleanup
        try:
            result = self.G.add_edge_type(edge_name, edge_schema)
            assert result is True
            self._assert_schema_contains(
                edges=[edge_name],
                should_exist=True,
            )
        finally:
            result = self.G.drop_edge_type(edge_name)
            assert result is True
            self._assert_schema_contains(
                edges=[edge_name],
                should_exist=False,
            )

    def test_add_and_drop_edge_types(self):
        """Test adding and dropping multiple edge types using only Employee nodes."""
        edges: Dict[str, Any] = {
            "collaborates_with": {
                "is_directed_edge": True,
                "from_node_type": "Employee",
                "to_node_type": "Employee",
            },
            "reports_to": {
                "is_directed_edge": True,
                "from_node_type": "Employee",
                "to_node_type": "Employee",
            },
        }

        # Use try/finally to ensure cleanup
        try:
            result = self.G.add_edge_types(edges)
            assert result is True
            self._assert_schema_contains(
                edges=list(edges.keys()),
                should_exist=True,
            )
        finally:
            result = self.G.drop_edge_types(list(edges.keys()))
            assert result is True
            self._assert_schema_contains(
                edges=list(edges.keys()),
                should_exist=False,
            )

    def test_add_and_drop_node_attributes(self):
        """Test adding and dropping multiple attributes on a node type."""
        node_attrs: Dict[str, Dict[str, Any]] = {
            "Employee": {
                "name": {"data_type": "STRING"},
                "age": {"data_type": "INT"},
            }
        }

        # Use try/finally to ensure cleanup
        try:
            result = self.G.add_node_attributes(node_attrs)
            assert result is True
            self._assert_schema_contains(
                node_attributes={"Employee": ["name", "age"]},
                should_exist=True,
            )
        finally:
            result = self.G.drop_node_attributes({"Employee": ["name", "age"]})
            assert result is True
            self._assert_schema_contains(
                node_attributes={"Employee": ["name", "age"]},
                should_exist=False,
            )

    def test_add_and_drop_edge_attributes(self):
        """Test adding and dropping multiple attributes on an edge type."""
        # Ensure the edge exists first
        self.G.add_edge_type(
            "mentors",
            {
                "is_directed_edge": True,
                "from_node_type": "Employee",
                "to_node_type": "Employee",
            },
        )

        edge_attrs: Dict[str, Dict[str, Any]] = {
            "mentors": {
                "since": {"data_type": "DATETIME"},
                "level": {"data_type": "STRING"},
            }
        }

        # Use try/finally to ensure cleanup
        try:
            result = self.G.add_edge_attributes(edge_attrs)
            assert result is True
            self._assert_schema_contains(
                edge_attributes={"mentors": ["since", "level"]},
                should_exist=True,
            )
        finally:
            result = self.G.drop_edge_attributes({"mentors": ["since", "level"]})
            assert result is True
            self._assert_schema_contains(
                edge_attributes={"mentors": ["since", "level"]},
                should_exist=False,
            )
            # Clean up edge itself
            self.G.drop_edge_type("mentors")

    def _assert_schema_contains(
        self,
        nodes: Optional[List[str]] = None,
        edges: Optional[List[str]] = None,
        node_attributes: Optional[Dict[str, List[str]]] = None,
        edge_attributes: Optional[Dict[str, List[str]]] = None,
        should_exist: bool = True,
    ):
        """Private helper to assert that nodes/edges and their attributes exist
        (or not) in both current and fresh graph schema, and schemas are identical.
        """
        nodes = nodes or []
        edges = edges or []
        node_attributes = node_attributes or {}
        edge_attributes = edge_attributes or {}

        schema = self.G.get_schema(format="dict")
        assert isinstance(schema, dict)
        G_fresh = Graph.from_db(
            graph_name=self.G.name,
            tigergraph_connection_config=self.tigergraph_connection_config,
        )
        fresh_schema = G_fresh.get_schema(format="dict")
        assert isinstance(fresh_schema, dict)

        # Assert that schema and fresh_schema are identical
        assert schema == fresh_schema

        # Check node existence
        for node in nodes:
            if should_exist:
                assert node in schema.get("nodes", {})
                assert node in fresh_schema.get("nodes", {})
            else:
                assert node not in schema.get("nodes", {})
                assert node not in fresh_schema.get("nodes", {})

        # Check edge existence
        for edge in edges:
            if should_exist:
                assert edge in schema.get("edges", {})
                assert edge in fresh_schema.get("edges", {})
            else:
                assert edge not in schema.get("edges", {})
                assert edge not in fresh_schema.get("edges", {})

        # Check node attributes
        for node, attrs in node_attributes.items():
            node_dict = schema.get("nodes", {}).get(node, {})
            fresh_node_dict = fresh_schema.get("nodes", {}).get(node, {})
            for attr in attrs:
                if should_exist:
                    assert attr in node_dict.get("attributes", {})
                    assert attr in fresh_node_dict.get("attributes", {})
                else:
                    assert attr not in node_dict.get("attributes", {})
                    assert attr not in fresh_node_dict.get("attributes", {})

        # Check edge attributes
        for edge, attrs in edge_attributes.items():
            edge_dict = schema.get("edges", {}).get(edge, {})
            fresh_edge_dict = fresh_schema.get("edges", {}).get(edge, {})
            for attr in attrs:
                if should_exist:
                    assert attr in edge_dict.get("attributes", {})
                    assert attr in fresh_edge_dict.get("attributes", {})
                else:
                    assert attr not in edge_dict.get("attributes", {})
                    assert attr not in fresh_edge_dict.get("attributes", {})
