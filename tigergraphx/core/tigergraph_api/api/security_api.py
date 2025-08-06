# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

from typing import Any, Dict, Optional

from .base_api import BaseAPI


class SecurityAPI(BaseAPI):
    def create_token(
        self,
        secret_alias: str,
        graph_name: Optional[str] = None,
        lifetime_seconds: Optional[int] = None,
    ) -> str:
        payload: Dict[str, Any] = {
            "secret": secret_alias,
        }
        if graph_name:
            payload["graph"] = graph_name
        if lifetime_seconds:
            payload["lifetime"] = lifetime_seconds

        result = self._request(
            endpoint_name="create_token",
            json=payload,
        )
        if not isinstance(result, str):
            raise TypeError(f"Expected str, but got {type(result).__name__}: {result}")
        return result

    def drop_token(
        self,
        token: str,
    ) -> str:
        payload: Dict[str, Any] = {
            "tokens": token,
        }
        result = self._request(
            endpoint_name="drop_token",
            json=payload,
        )
        if not isinstance(result, str):
            raise TypeError(f"Expected str, but got {type(result).__name__}: {result}")
        return result
