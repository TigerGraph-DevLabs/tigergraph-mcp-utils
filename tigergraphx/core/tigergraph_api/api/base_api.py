# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

from typing import Any, Dict, List, Literal, Optional
from requests.sessions import Session
from requests.exceptions import (
    RequestException,
    ConnectionError,
    HTTPError,
    Timeout,
    TooManyRedirects,
    URLRequired,
    InvalidURL,
    MissingSchema,
    InvalidSchema,
    ChunkedEncodingError,
    ContentDecodingError,
)
import logging

from ..endpoint_handler.endpoint_registry import EndpointRegistry

from tigergraphx.config import TigerGraphConnectionConfig

logger = logging.getLogger(__name__)


class BaseAPI:
    def __init__(
        self,
        config: TigerGraphConnectionConfig,
        endpoint_registry: EndpointRegistry,
        session: Session,
        version: Literal["3.x", "4.x"] = "4.x",
    ):
        """
        Initializes the BaseAPI with a shared session and endpoint registry.
        """
        self.config = config
        self.endpoint_registry = endpoint_registry
        self.session = session
        self.version: Literal["3.x", "4.x"] = version

    def _request(
        self,
        endpoint_name: str,
        params: Optional[Dict] = None,
        data: Optional[Dict | str] = None,
        json: Optional[Dict] = None,
        **path_kwargs,
    ) -> Dict | List | str:
        """
        Sends an HTTP request using resolved endpoint details.
        Raises exceptions on failure.
        """
        try:
            # Resolve endpoint details
            endpoint = self.endpoint_registry.get_endpoint(
                endpoint_name, self.version, **path_kwargs
            )
            base_url = f"{str(self.config.host).rstrip('/')}"
            url = (
                f"{base_url}:{getattr(self.config, endpoint['port'])}{endpoint['path']}"
            )

            # Get Content-Type from endpoint config (default to application/json)
            content_type = endpoint.get("content_type", "application/json")
            headers = {**self.session.headers, "Content-Type": content_type}

            logger.debug(
                f"method: {endpoint['method']}, url: {url}; params: {params}; "
                f"data: {data}; json: {json}; headers: {headers}"
            )

            # Make the request
            response = self.session.request(
                method=endpoint["method"],
                url=url,
                params=params,
                data=data,
                json=json,
                headers=headers,
            )

            # Get Content-Type
            content_type = response.headers.get("Content-Type", "")

            # Handle JSON responses first
            if "application/json" in content_type:
                try:
                    response_json = response.json()
                except ValueError:
                    # Server lied about Content-Type, fallback to plain text
                    self._raise_for_status(response)
                    return response.text.strip()

                # Check if TigerGraph API returned an error
                if response_json.get("error", False) or response_json.get(
                    "isDraft", False
                ):
                    raise TigerGraphAPIError(
                        response_json.get("message", "Unknown error"),
                        status_code=response.status_code,
                        response=response,
                    )

                self._raise_for_status(response)

                results = response_json.get("results")
                if results is not None:
                    return results

                # Check for drop-specific keys if no results
                if "dropped" in response_json or "failedToDrop" in response_json:
                    return {
                        "dropped": response_json.get("dropped", []),
                        "failedToDrop": response_json.get("failedToDrop", []),
                    }

                # Check for token-specific keys if no results
                if "token" in response_json:
                    return response_json.get("token", "")

                # Fallback to message
                return response_json.get("message", None)

            # Handle text/plain responses
            elif "text/plain" in content_type or content_type == "":
                self._raise_for_status(response)
                return response.text.strip()

            # Handle unknown Content-Type
            else:
                self._raise_for_status(response)
                raise TigerGraphAPIError(
                    f"Unsupported content type: {content_type}",
                    status_code=response.status_code,
                    response=response,
                )

        except HTTPError as e:
            raise RuntimeError(f"HTTP request failed: {str(e)}") from e
        except ConnectionError as e:
            raise ConnectionError(f"Failed to connect to TigerGraph: {str(e)}") from e
        except Timeout as e:
            raise TimeoutError(f"Request timed out: {str(e)}") from e
        except TooManyRedirects as e:
            raise RuntimeError(f"Too many redirects: {str(e)}") from e
        except (URLRequired, InvalidURL, MissingSchema, InvalidSchema) as e:
            raise ValueError("Invalid request URL") from e
        except (ChunkedEncodingError, ContentDecodingError) as e:
            raise RuntimeError(f"Failed to decode response: {str(e)}") from e
        except RequestException as e:
            raise RuntimeError(f"Request error: {str(e)}") from e
        except TigerGraphAPIError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error: {type(e).__name__} - {str(e)}"
            ) from e

    def _raise_for_status(self, response):
        """
        Raises HTTPError with detailed messages based on the status code.
        """
        status_code = response.status_code
        reason = response.reason or "Unknown Error"
        url = response.url

        # Decode reason if it's in bytes (to avoid encoding issues)
        if isinstance(reason, bytes):
            try:
                reason = reason.decode("utf-8")
            except UnicodeDecodeError:
                reason = reason.decode("iso-8859-1")

        # Custom error messages for common status codes
        error_messages = {
            400: "400 Bad Request: The request was invalid. Check syntax or parameters.",
            401: "401 Unauthorized: Authentication failed. Verify credentials, API key, or token.",
            403: "403 Forbidden: You lack permission to access this resource.",
            404: "404 Not Found: The requested resource does not exist. Check the URL.",
            405: "405 Method Not Allowed: The HTTP method used is not supported by this endpoint.",
            408: "408 Request Timeout: The request took too long to process. Try again later.",
            409: "409 Conflict: Request conflicts with the current state of the server.",
            429: "429 Too Many Requests: API rate limit exceeded. Slow down your requests.",
            500: "500 Internal Server Error: The server encountered an error processing the request.",
            502: "502 Bad Gateway: Received an invalid response from an upstream server.",
            503: "503 Service Unavailable: The API is temporarily unavailable or overloaded.",
            504: "504 Gateway Timeout: The server took too long to respond.",
        }

        # Generate error message
        error_msg = error_messages.get(status_code, f"{status_code} Error: {reason}")
        full_error_msg = f"{error_msg} URL: {url}."

        if 400 <= status_code < 600:
            raise HTTPError(full_error_msg, response=response)


class TigerGraphAPIError(Exception):
    """
    Exception raised for errors returned by the TigerGraph API.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
    ):
        """
        Initializes the TigerGraphAPIError with the provided details.
        """
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.__str__())

    def __str__(self) -> str:
        """
        Returns a formatted string representation of the error.
        """
        return (
            f"[HTTP {self.status_code}] {self.message}"
            if self.status_code
            else self.message
        )

    def get_response_text(self) -> Optional[str]:
        """
        Returns the response text if available.
        """
        return self.response.text if self.response else None
