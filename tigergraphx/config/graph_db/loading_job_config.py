# Copyright 2025 TigerGraph Inc.
# Licensed under the Apache License, Version 2.0.
# See the LICENSE file or https://www.apache.org/licenses/LICENSE-2.0
#
# Permission is granted to use, copy, modify, and distribute this software
# under the License. The software is provided "AS IS", without warranty.

from enum import Enum
from typing import Optional, Dict, List
from pydantic import Field, model_validator

from tigergraphx.config import BaseConfig


class QuoteType(Enum):
    """
    Enumeration of quote types for CSV parsing.
    """

    DOUBLE = "DOUBLE"
    SINGLE = "SINGLE"


class CsvParsingOptions(BaseConfig):
    """
    Configuration options for CSV parsing.
    """

    separator: str = Field(
        default=",", description="The separator used in the CSV file."
    )
    header: bool = Field(
        default=True, description="Whether the CSV file contains a header row."
    )
    EOL: str = Field(
        default="\\n", description="The end-of-line character in the CSV file."
    )
    quote: Optional[QuoteType] = Field(
        default=QuoteType.DOUBLE, description="The type of quote used in the CSV file."
    )


class NodeMappingConfig(BaseConfig):
    """
    Configuration for mapping node attributes from a file to the target schema.
    """

    target_name: str = Field(description="The name of the target node type.")
    attribute_column_mappings: Dict[str, str | int | Dict] = Field(
        default={}, description="Mapping file columns to node attributes."
    )


class EdgeMappingConfig(BaseConfig):
    """
    Configuration for mapping edge attributes from a file to the target schema.
    """

    target_name: str = Field(description="The target edge type name.")
    source_node_column: str | int = Field(
        description="The column representing the source node in the file."
    )
    target_node_column: str | int = Field(
        description="The column representing the target node in the file."
    )
    attribute_column_mappings: Dict[str, str | int] = Field(
        default={}, description="Mappings between file columns and edge attributes."
    )


class FileConfig(BaseConfig):
    """
    Configuration for a single file used in a loading job.
    """

    file_alias: str = Field(description="An alias for the file, used as a reference.")
    file_path: Optional[str] = Field(
        default=None, description="The path to the file on disk."
    )
    csv_parsing_options: CsvParsingOptions = Field(
        default_factory=CsvParsingOptions,
        description="Options for parsing the CSV file.",
    )
    node_mappings: List[NodeMappingConfig] = Field(
        default=[], description="Node mappings defined for this file."
    )
    edge_mappings: List[EdgeMappingConfig] = Field(
        default=[], description="Edge mappings defined for this file."
    )

    @model_validator(mode="after")
    def validate_mappings(self) -> "FileConfig":
        """
        Ensure that at least one mapping (node or edge) exists.

        Returns:
            The validated file configuration.

        Raises:
            ValueError: If no node or edge mappings are provided.
        """
        n_node_mappings = len(self.node_mappings) if self.node_mappings else 0
        n_edge_mappings = len(self.edge_mappings) if self.edge_mappings else 0
        if n_node_mappings + n_edge_mappings == 0:
            raise ValueError(
                "FileConfig must contain at least one node or edge mapping in 'node_mappings' "
                "or 'edge_mappings'."
            )
        return self


class LoadingJobConfig(BaseConfig):
    """
    Configuration for a loading job consisting of multiple files.
    """

    loading_job_name: str = Field(description="The name of the loading job.")
    files: List[FileConfig] = Field(
        description="A list of files included in the loading job."
    )

    @model_validator(mode="after")
    def validate_file_aliases(self) -> "LoadingJobConfig":
        """
        Ensure that all file_alias values are unique.

        Returns:
            The validated loading job configuration.

        Raises:
            ValueError: If duplicate file_alias values are found.
        """
        file_aliases = [file.file_alias for file in self.files]
        duplicates = {alias for alias in file_aliases if file_aliases.count(alias) > 1}
        if duplicates:
            raise ValueError(
                f"Duplicate file_alias values found in files: {', '.join(duplicates)}"
            )
        return self
