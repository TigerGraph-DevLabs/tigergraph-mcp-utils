import pytest
import time

from .base_graph_fixture import BaseGraphFixture

from tigergraphx.core import Graph
from tigergraphx.vector_search import TigerVectorManager


class TestTigerVector(BaseGraphFixture):
    def setup_graph(self):
        """Set up the graph and add nodes and edges."""
        graph_schema = {
            "graph_name": "TigerVector",
            "nodes": {
                "Entity": {
                    "primary_key": "id",
                    "attributes": {
                        "id": "STRING",
                        "entity_type": "STRING",
                        "description": "STRING",
                        "source_id": "STRING",
                    },
                    "vector_attributes": {"emb_description": 3},
                },
            },
            "edges": {
                "relationship": {
                    "is_directed_edge": True,
                    "from_node_type": "Entity",
                    "to_node_type": "Entity",
                    "attributes": {
                        "weight": "DOUBLE",
                        "description": "STRING",
                        "keywords": "STRING",
                        "source_id": "STRING",
                    },
                },
            },
        }
        self.G = Graph(
            graph_schema=graph_schema,
            tigergraph_connection_config=self.tigergraph_connection_config,
        )

    @pytest.fixture(autouse=True)
    def add_nodes_and_edges(self):
        """Add nodes and edges before each test case."""
        # Initialize the graph
        self.setup_graph()

        # Adding nodes and edges
        self.G.upsert(
            data=[
                {
                    "id": "Entity_1",
                    "entity_type": "Person",
                    "description": "Desc1",
                    "source_id": "Source1",
                    "emb_description": [-0.01773, -0.01019, -0.01657],
                },
            ],
            node_type="Entity",
        )
        self.G.add_nodes_from(
            [
                (
                    "Entity_2",
                    {
                        "entity_type": "Person",
                        "description": "Desc2",
                        "source_id": "Source2",
                        "emb_description": [-0.01926, 0.000496, 0.00671],
                    },
                ),
            ]
        )
        self.G.add_edge(
            "Entity_1",
            "Entity_2",
            "Entity",
            "relationship",
            "Entity",
            weight=1.0,
            description="Relates to",
            keywords="key1,key2",
            source_id="SourceRel",
        )
        time.sleep(3)

        yield  # The test case runs here

        self.G.clear()

    @pytest.fixture(scope="class", autouse=True)
    def drop_graph(self):
        """Drop the graph after all tests are done in the session."""
        yield
        self.setup_graph()
        self.G.drop_graph()

    def test_fetch_single_node_embedding(self):
        """
        Test fetching the embedding vector for a single node.
        """
        vector_attribute_name = "emb_description"
        result = self.G.fetch_node(
            "Entity_1", vector_attribute_name, node_type="Entity"
        )

        expected_embedding = [-0.01773, -0.01019, -0.01657]
        assert result == expected_embedding, (
            f"Expected {expected_embedding}, got {result}"
        )

    def test_fetch_multiple_nodes_embeddings(self):
        """
        Test fetching the embedding vectors for multiple nodes.
        """
        vector_attribute_name = "emb_description"
        result = self.G.fetch_nodes(
            ["Entity_1", "Entity_2"], vector_attribute_name, node_type="Entity"
        )

        expected_embeddings = {
            "Entity_1": [-0.01773, -0.01019, -0.01657],
            "Entity_2": [-0.01926, 0.000496, 0.00671],
        }
        assert result == expected_embeddings, (
            f"Expected {expected_embeddings}, got {result}"
        )

    def test_vector_search(self):
        assert self.G.has_node("Entity_1")
        assert self.G.has_node("Entity_2")
        assert self.G.has_edge(
            "Entity_1", "Entity_2", "Entity", "relationship", "Entity"
        )
        query_vector = [-0.01926, 0.000496, 0.00671]
        results = self.G.search(query_vector, "emb_description", limit=1)
        assert len(results) == 1
        results = self.G.search(query_vector, "emb_description", limit=2)
        assert len(results) == 2

    def test_tigervector_manager(self):
        config = {
            "type": "TigerVector",
            "graph_name": "TigerVector",
            "node_type": "Entity",
            "vector_attribute_name": "emb_description",
        }
        manager = TigerVectorManager(config, self.G)
        query_vector = [-0.01926, 0.000496, 0.00671]
        results = manager.query(query_vector, k=1)
        assert len(results) == 1
        results = manager.query(query_vector, k=2)
        assert len(results) == 2
