import pytest
from pathlib import Path
import yaml

from tigergraphx.core.tigergraph_api import TigerGraphAPI


class TestDatabaseAPIs:
    @pytest.fixture(autouse=True)
    def init(self):
        config_path = (
            Path(__file__).parent.parent / "config" / "tigergraph_connection.yaml"
        )
        with open(config_path, "r") as f:
            self.tigergraph_connection_config = yaml.safe_load(f)

        # Initialize the TigerGraphAPI
        self.api = TigerGraphAPI(self.tigergraph_connection_config)

    # ------------------------------ Admin ------------------------------
    def test_ping(self):
        """
        Integration test for the TigerGraph ping endpoint.
        """
        result = self.api.ping()

        assert isinstance(result, str), "Response should be a str."
        assert result == "pong", "Response should be 'pong'."

    def test_get_version(self):
        """
        Integration test for the TigerGraph get_version endpoint.
        """
        result = self.api.get_version()

        assert isinstance(result, str), "Response should be a str."
        assert result.startswith("3.") or result.startswith("4."), (
            f"Unexpected version format: {result}"
        )

    # ------------------------------ GSQL ------------------------------
    def test_gsql(self):
        """
        Integration test for the TigerGraph gsql endpoint.
        """
        result = self.api.gsql("ls")

        assert isinstance(result, str), "Response should be a string."
        assert "Global vertices, edges, and all graphs" in result

    # ------------------------------ Data Source ------------------------------
    def test_data_source_CRUD(self):
        data_source_name = "data_source_test"
        data_source_type = "s3"

        # Create initial data source
        result = self.api.create_data_source(
            name=data_source_name,
            data_source_type=data_source_type,
        )
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert f"Data source {data_source_name} is created" in result, (
            f"Unexpected response: {result}"
        )

        try:
            # Get data source
            result = self.api.get_data_source(data_source_name)
            assert isinstance(result, dict), f"Expected dict, got {type(result)}"
            assert result.get("name") == data_source_name, (
                f"Expected name '{data_source_name}', got {result.get('name')}"
            )
            assert result.get("type") == data_source_type.upper(), (
                f"Expected type '{data_source_type}', got {result.get('type')}"
            )

            # Get all data sources
            all_sources = self.api.get_all_data_sources()
            assert isinstance(all_sources, list), (
                f"Expected list, got {type(all_sources)}"
            )
            assert any(ds["name"] == data_source_name for ds in all_sources), (
                "Created data source not found in list"
            )

            # Update the data source
            result = self.api.update_data_source(
                name=data_source_name,
                data_source_type=data_source_type,
                access_key="aaaaaaaaaaaaaaaaaaaa",
                secret_key="",
            )
            assert isinstance(result, str)
            assert (
                f"Data source {data_source_name} is created" in result
                or "updated" in result.lower()
            )

        finally:
            # Drop data source
            drop_result = self.api.drop_all_data_sources()
            assert isinstance(drop_result, str), (
                f"Expected str, got {type(drop_result)}"
            )
            assert "All data sources is dropped successfully." in drop_result, (
                f"Unexpected drop response: {drop_result}"
            )

    @pytest.mark.skip(
        reason="""
    Skipped by default. To enable this test, manually configure the data source by setting 
    values for data_source_type, access_key, secret_key, extra_config, and sample_path 
    (the path to the file to sample).
    """
    )
    def test_preview_sample_data(self):
        data_source_name = "data_source_1"
        data_source_type = "s3"
        access_key = ""
        secret_key = ""
        extra_config = {
            "file.reader.settings.fs.s3a.aws.credentials.provider": "org.apache.hadoop.fs.s3a.AnonymousAWSCredentialsProvider"
        }
        sample_path = "s3a://<YOUR_FILE_PATH>"

        # Create data source
        result = self.api.create_data_source(
            name=data_source_name,
            data_source_type=data_source_type,
            access_key=access_key,
            secret_key=secret_key,
            extra_config=extra_config,
        )
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert f"Data source {data_source_name} is created" in result, (
            f"Unexpected response: {result}"
        )

        try:
            # Preview sample data
            preview_result = self.api.preview_sample_data(
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
            assert isinstance(preview_result, dict), (
                f"Expected dict, got {type(preview_result)}"
            )
            assert "data" in preview_result, "Key 'data' not found in preview result"
            assert isinstance(preview_result["data"], list), (
                f"Expected 'data' to be list, got {type(preview_result['data'])}"
            )
            assert len(preview_result["data"]) <= 5, (
                f"Preview data has more rows than expected: {len(preview_result['data'])}"
            )

        finally:
            # Drop data source
            drop_result = self.api.drop_data_source(name=data_source_name)
            assert isinstance(drop_result, str), (
                f"Expected str, got {type(drop_result)}"
            )
            assert f"Data source {data_source_name} is dropped" in drop_result, (
                f"Unexpected drop response: {drop_result}"
            )
