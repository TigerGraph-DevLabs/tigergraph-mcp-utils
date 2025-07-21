import pytest
import yaml
from pathlib import Path

from tigergraphx import Graph, TigerGraphDatabase
from tigergraphx.core.tigergraph_api import TigerGraphAPIError


class TestTigerGraphDatabase:
    @pytest.fixture(autouse=True)
    def setup_database(self):
        config_path = (
            Path(__file__).parent.parent / "config" / "tigergraph_connection.yaml"
        )
        with open(config_path, "r") as f:
            self.tigergraph_connection_config = yaml.safe_load(f)

        self.db = TigerGraphDatabase(
            tigergraph_connection_config=self.tigergraph_connection_config
        )

    def test_ping(self):
        result = self.db.ping()
        assert isinstance(result, str)
        assert result == "pong"

    def test_gsql(self):
        result = self.db.gsql("ls")
        assert isinstance(result, str)
        assert "Global vertices, edges, and all graphs" in result

    def test_list_metadata(self):
        result = self.db.list_metadata()
        assert isinstance(result, str)
        assert "Global vertices, edges, and all graphs" in result
        graph_name = "TestListMetadata"
        graph_schema = {
            "graph_name": graph_name,
            "nodes": {
                "Person": {
                    "primary_key": "name",
                    "attributes": {
                        "name": "STRING",
                        "age": "UINT",
                        "gender": "STRING",
                    },
                },
            },
            "edges": {
                "Friendship": {
                    "is_directed_edge": False,
                    "from_node_type": "Person",
                    "to_node_type": "Person",
                    "attributes": {
                        "closeness": "DOUBLE",
                    },
                },
            },
        }
        G = Graph(
            graph_schema=graph_schema,
            tigergraph_connection_config=self.tigergraph_connection_config,
        )
        try:
            result = self.db.list_metadata(graph_name=graph_name)
            assert isinstance(result, str)
            assert "VERTEX Person" in result
            assert "UNDIRECTED EDGE Friendship" in result
            assert f"Graph {graph_name}(Person:v, Friendship:e)" in result
        finally:
            G.drop_graph()

    def test_data_source_CRUD(self):
        data_source_name = "db_data_source_test"
        data_source_type = "s3"

        result = self.db.create_data_source(
            name=data_source_name, data_source_type=data_source_type
        )
        assert isinstance(result, str)
        assert f"Data source {data_source_name} is created" in result

        try:
            result = self.db.get_data_source(name=data_source_name)
            assert isinstance(result, dict)
            assert result.get("name") == data_source_name
            assert result.get("type") == data_source_type.upper()

            all_sources = self.db.get_all_data_sources()
            assert isinstance(all_sources, list)
            assert any(ds["name"] == data_source_name for ds in all_sources)

            result = self.db.update_data_source(
                name=data_source_name,
                data_source_type=data_source_type,
                access_key="dummy-access-key",
                secret_key="",
            )
            assert isinstance(result, str)
            assert (
                f"Data source {data_source_name} is created" in result
                or "updated" in result.lower()
            )

        finally:
            drop_result = self.db.drop_all_data_sources()
            assert isinstance(drop_result, str)
            assert "All data sources is dropped successfully." in drop_result

    def test_data_source_all(self):
        data_source_name = "db_data_source_test"
        data_source_type = "s3"

        # Create data source
        create_result = self.db.create_data_source(
            name=data_source_name, data_source_type=data_source_type
        )
        assert isinstance(create_result, str), (
            "create_data_source() should return a string"
        )
        assert f"Data source {data_source_name} is created" in create_result, (
            "Unexpected create message"
        )

        try:
            # Retrieve all data sources and validate presence
            all_sources = self.db.get_all_data_sources()
            assert isinstance(all_sources, list), (
                "get_all_data_sources() should return a list"
            )
            assert any(
                isinstance(ds, dict) and ds.get("name") == data_source_name
                for ds in all_sources
            ), f"{data_source_name} should exist in data sources"
        finally:
            # Drop all data sources
            drop_result = self.db.drop_all_data_sources()
            assert isinstance(drop_result, str), (
                "drop_all_data_sources() should return a string"
            )
            assert "All data sources is dropped successfully." in drop_result, (
                "Unexpected drop message"
            )

        # Verify get_all_data_sources works for empty state
        empty_sources = self.db.get_all_data_sources()
        assert isinstance(empty_sources, list), (
            "get_all_data_sources() should return a list even when empty"
        )
        assert len(empty_sources) == 0, (
            "Data sources should be empty after drop_all_data_sources"
        )

    def test_get_data_source_not_found(self):
        data_source_name = "nonexistent_datasource"
        with pytest.raises(
            TigerGraphAPIError, match=f"Datasource {data_source_name} not found"
        ):
            self.db.get_data_source(data_source_name)

    @pytest.mark.skip(
        reason="""
    Skipped by default. To enable this test, manually configure the data source by setting 
    values for data_source_type, access_key, secret_key, extra_config, and sample_path 
    (the path to the file to sample).
    """
    )
    def test_preview_sample_data(self):
        data_source_name = "sample_ds"
        data_source_type = "s3"
        access_key = ""
        secret_key = ""
        extra_config = {
            "file.reader.settings.fs.s3a.aws.credentials.provider": "org.apache.hadoop.fs.s3a.AnonymousAWSCredentialsProvider"
        }
        sample_path = "s3a://<YOUR_FILE_PATH>"

        result = self.db.create_data_source(
            name=data_source_name,
            data_source_type=data_source_type,
            access_key=access_key,
            secret_key=secret_key,
            extra_config=extra_config,
        )
        assert f"Data source {data_source_name} is created" in result

        try:
            preview_result = self.db.preview_sample_data(
                path=sample_path,
                data_source_type=data_source_type,
                data_source=data_source_name,
                data_format="csv",
                size=5,
                has_header=True,
                separator=",",
                eol="\\n",
                quote='"',
            )
            assert isinstance(preview_result, dict)
            assert "data" in preview_result
            assert isinstance(preview_result["data"], list)
            assert len(preview_result["data"]) <= 5

        finally:
            drop_result = self.db.drop_data_source(name=data_source_name)
            assert isinstance(drop_result, str)
            assert f"Data source {data_source_name} is dropped" in drop_result
