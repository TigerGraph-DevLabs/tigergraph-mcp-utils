import pytest
from pathlib import Path
import yaml

from tigergraphx.core.tigergraph_api import TigerGraphAPI


class TestGraphSchemaAPIs:
    def setup_graph(self):
        """Set up the graph and add nodes and edges."""
        # Load config from YAML
        config_path = (
            Path(__file__).parent.parent / "config" / "tigergraph_connection.yaml"
        )
        with open(config_path, "r") as f:
            self.tigergraph_connection_config = yaml.safe_load(f)

    @pytest.fixture(autouse=True)
    def init(self):
        """Add nodes and edges before each test case."""
        # Initialize the graph
        self.setup_graph()

        # Initialize the TigerGraphAPI
        self.api = TigerGraphAPI(self.tigergraph_connection_config)

        yield  # The test case runs here

    # ------------------------------ Schema ------------------------------
    def test_create_and_drop_graph(self):
        graph_name = "TestSchemaGraph"

        # Precheck: drop graph if it already exists
        try:
            schema = self.api.get_schema(graph_name)
            if schema and schema.get("GraphName") == graph_name:
                drop_result = self.api.drop_graph(graph_name=graph_name)
                assert isinstance(drop_result, str), "Drop response should be a string."
                assert "Successfully dropped graph" in drop_result
        except Exception:
            # If get_schema fails (e.g., graph doesn't exist), ignore
            pass

        # Create new graph
        result = self.api.create_empty_graph(graph_name=graph_name)
        assert isinstance(result, str), "Create response should be a string."
        assert "Successfully created graph" in result

        # Drop the graph
        result = self.api.drop_graph(graph_name=graph_name)
        assert isinstance(result, str), "Drop response should be a string."
        assert "Successfully dropped graph" in result

    def test_local_schema_change_job(self):
        graph_name = "TestSchemaChangeGraph"
        job_name_prefix = "test_job"

        # Precheck: drop graph if it already exists
        try:
            schema = self.api.get_schema(graph_name)
            if schema and schema.get("GraphName") == graph_name:
                drop_result = self.api.drop_graph(graph_name=graph_name)
                assert isinstance(drop_result, str), "Drop response should be a string."
                assert "Successfully dropped graph" in drop_result
        except Exception:
            # Graph does not exist
            pass

        # Step 1: Create an empty graph
        result = self.api.create_empty_graph(graph_name=graph_name)
        assert isinstance(result, str), "Create response should be a string."
        assert "Successfully created graph" in result

        try:
            # Step 2: Add schema (nodes and edges)
            add_job_name = f"{job_name_prefix}_add"
            add_payload = {
                "addVertexTypes": [
                    {
                        "Name": "Person",
                        "PrimaryId": {
                            "AttributeName": "id",
                            "AttributeType": {"Name": "STRING"},
                        },
                        "Attributes": [
                            {
                                "AttributeName": "name",
                                "AttributeType": {"Name": "STRING"},
                            }
                        ],
                        "Config": {
                            "STATS": "OUTDEGREE_BY_EDGETYPE",
                            "PRIMARY_ID_AS_ATTRIBUTE": "true",
                        },
                    },
                    {
                        "Name": "Company",
                        "PrimaryId": {
                            "AttributeName": "id",
                            "AttributeType": {"Name": "STRING"},
                        },
                        "Attributes": [],
                        "Config": {
                            "STATS": "OUTDEGREE_BY_EDGETYPE",
                            "PRIMARY_ID_AS_ATTRIBUTE": "true",
                        },
                    },
                ],
                "addEdgeTypes": [
                    {
                        "Name": "works_at",
                        "IsDirected": True,
                        "FromVertexTypeName": "Person",
                        "ToVertexTypeName": "Company",
                        "Attributes": [
                            {
                                "AttributeName": "since",
                                "AttributeType": {"Name": "DATETIME"},
                                "IsDiscriminator": True
                            },
                            {
                                "AttributeName": "country",
                                "AttributeType": {"Name": "STRING"},
                            }
                        ],
                        "Config": {
                            "REVERSE_EDGE": "reverse_works_at",
                        },
                    }
                ],
            }
            result = self.api.create_local_schema_change_job(
                graph_name=graph_name, job_name=add_job_name, payload=add_payload
            )
            assert isinstance(result, str), (
                "Create schema change job response should be a string."
            )
            assert "Successfully created schema change job" in result
            try:
                result = self.api.run_local_schema_change_job(
                    graph_name=graph_name, job_name=add_job_name
                )
                assert isinstance(result, str), (
                    "Run schema change job response should be a string."
                )
                assert "Schema change job run successfully!" in result
            finally:
                result = self.api.drop_local_schema_change_job(
                    graph_name=graph_name, job_name=add_job_name
                )
                assert isinstance(result, str), (
                    "Drop schema change job response should be a string."
                )
                assert "Successfully dropped schema change jobs" in result

            # Step 3: Modify schema (add attributes)
            modify_job_name = f"{job_name_prefix}_modify"
            modify_payload = {
                "alterEdgeTypes": [
                    {
                        "name": "works_at",
                        "addAttributes": [
                            {
                                "AttributeName": "city",
                                "AttributeType": {"Name": "STRING"},
                            }
                        ],
                        "dropAttributes": ["country"],
                    }
                ],
                "alterVertexTypes": [
                    {
                        "name": "Person",
                        "addAttributes": [
                            {
                                "AttributeName": "age",
                                "AttributeType": {"Name": "UINT"},
                                "DefaultValue": "0",
                            }
                        ],
                        "dropAttributes": ["name"],
                    }
                ],
            }
            result = self.api.create_local_schema_change_job(
                graph_name=graph_name, job_name=modify_job_name, payload=modify_payload
            )
            assert isinstance(result, str), (
                "Create schema change job response should be a string."
            )
            assert "Successfully created schema change job" in result
            try:
                result = self.api.run_local_schema_change_job(
                    graph_name=graph_name, job_name=modify_job_name
                )
                assert isinstance(result, str), (
                    "Run schema change job response should be a string."
                )
                assert "Schema change job run successfully!" in result
            finally:
                result = self.api.drop_local_schema_change_job(
                    graph_name=graph_name, job_name=modify_job_name
                )
                assert isinstance(result, str), (
                    "Drop schema change job response should be a string."
                )
                assert "Successfully dropped schema change jobs" in result

            # Step 4: Delete schema elements
            delete_job_name = f"{job_name_prefix}_delete"
            delete_payload = {
                "dropEdgeTypes": ["works_at"],
                "dropVertexTypes": ["Company"],
            }
            result = self.api.create_local_schema_change_job(
                graph_name=graph_name,
                job_name=delete_job_name,
                payload=delete_payload,
            )
            assert isinstance(result, str), (
                "Create schema change job response should be a string."
            )
            assert "Successfully created schema change job" in result
            try:
                result = self.api.run_local_schema_change_job(
                    graph_name=graph_name, job_name=delete_job_name
                )
                assert isinstance(result, str), (
                    "Run schema change job response should be a string."
                )
                assert "Schema change job run successfully!" in result
            finally:
                result = self.api.drop_local_schema_change_job(
                    graph_name=graph_name, job_name=delete_job_name
                )
                assert isinstance(result, str), (
                    "Drop schema change job response should be a string."
                )
                assert "Successfully dropped schema change jobs" in result

        finally:
            # Step 5: Drop the graph
            result = self.api.drop_graph(graph_name=graph_name)
            assert isinstance(result, str), "Drop response should be a string."
            assert "Successfully dropped graph" in result
