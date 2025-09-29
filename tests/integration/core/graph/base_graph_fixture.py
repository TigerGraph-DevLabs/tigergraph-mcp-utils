import time
import yaml
from pathlib import Path
from typing import Any, Dict
import pytest


class BaseGraphFixture:
    tigergraph_connection_config: Dict[str, Any]

    @pytest.fixture(scope="class", autouse=True)
    def load_connection_config(self, request):
        """Load connection config from YAML and attach to class."""
        config_path = Path(__file__).parent.parent / "config" / "tigergraph_connection.yaml"
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        request.cls.tigergraph_connection_config = config

    @staticmethod
    def time_execution(func, func_name: str):
        start_time = time.perf_counter()
        result = func()
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"Time taken to execute {func_name}: {elapsed_time:.6f} seconds")
        return result
