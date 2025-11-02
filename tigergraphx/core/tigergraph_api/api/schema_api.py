# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

from typing import Any, Dict
from .base_api import BaseAPI


class SchemaAPI(BaseAPI):
    def get_schema(self, graph_name: str) -> Dict:
        """
        Retrieves the schema for a specific graph.
        """
        result = self._request(endpoint_name="get_schema", graph_name=graph_name)
        if not isinstance(result, dict):
            raise TypeError(f"Expected dict, but got {type(result).__name__}: {result}")
        return result

    def create_empty_graph(self, graph_name: str) -> str:
        """
        Create an empty graph.
        """
        data = '{"VertexTypes":[], "EdgeTypes":[]}'

        result = self._request(
            endpoint_name="create_empty_graph", graph_name=graph_name, data=data
        )
        if not isinstance(result, str):
            raise TypeError(f"Expected str, but got {type(result).__name__}: {result}")
        return result

    def drop_graph(self, graph_name: str) -> str:
        """
        Drop a graph.
        """
        result = self._request(
            endpoint_name="drop_graph",
            graph_name=graph_name,
        )
        if not isinstance(result, str):
            raise TypeError(f"Expected str, but got {type(result).__name__}: {result}")
        return result

    def create_local_schema_change_job(
        self, graph_name: str, job_name: str, payload: Dict[str, Any]
    ) -> str:
        """
        Create a local schema change job
        """
        result = self._request(
            endpoint_name="create_local_schema_change_job",
            graph_name=graph_name,
            job_name=job_name,
            json=payload,
        )
        if not isinstance(result, str):
            raise TypeError(f"Expected str, but got {type(result).__name__}: {result}")
        return result

    def run_local_schema_change_job(self, graph_name: str, job_name: str) -> str:
        """
        Run a local schema change job
        """
        result = self._request(
            endpoint_name="run_local_schema_change_job",
            graph_name=graph_name,
            job_name=job_name,
        )
        if not isinstance(result, str):
            raise TypeError(f"Expected str, but got {type(result).__name__}: {result}")
        return result

    def drop_local_schema_change_job(self, graph_name: str, job_name: str) -> str:
        """
        Drop a local schema change job
        """
        result = self._request(
            endpoint_name="drop_local_schema_change_job",
            graph_name=graph_name,
            job_name=job_name,
        )
        if not isinstance(result, str):
            raise TypeError(f"Expected str, but got {type(result).__name__}: {result}")
        return result
