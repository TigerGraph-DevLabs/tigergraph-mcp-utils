# Changelog

---

Note: version releases in the 0.x.y range may include both bug fixes and new features, not strictly limited to patches.

## 0.2.15
- chore: upgrade dependencies to patched versions to fix security vulnerabilities

## 0.2.14
- feat: add API to fetch query info and Graph method to check query installation

## 0.2.13
- feat: rename parameter `secret` to `secret_alias` in `create_token` method for clarity
- feat: add strict type checks for column_name formatting and raise errors on invalid inputs

## 0.2.12
- feat: add validation for reserved keywords in graph schema

## 0.2.11
- fix: resolve type error in get_all_data_sources when no data sources exist
- fix: add GSQL version fallback for cases requiring token-based auth
- feat: add methods for creating/showing/dropping secrets and creating/dropping tokens
- feat: return GSQL response from load_data for better visibility and debugging

## 0.2.10
- test: mock AdminAPI.get_version to prevent real HTTP calls during Graph initialization
- feat: add method list_metadata to class TigerGraphDatabase

## 0.2.9
- fix: ensure primary keys are compared as strings in neighbor ID tracking in the method bfs
- feat: add TigerGraphDatabase abstraction class for database operations
- feat: store TigerGraph version in TigerGraphAPI and enforce minimum version check in VectorManager
- docs: add MkDocs documentation for class TigerGraphDatabase

## 0.2.8
- feat: add get_edges method to Graph class

## 0.2.7
- feat: add support for previewing sample data and managing data sources (create, update, drop, get)

## 0.2.6
- feat: add Graph methods for creating, installing, and dropping queries
- feat: add TigerGraph API support for creating, installing and dropping queries

## 0.2.5
- fix: resolve incorrect edge count when edge_type is specified

## 0.2.4
- fix: handle multi-edge support in add_edges_from using discriminator logic

## 0.2.3
- feat: add support for output_type="List" in get_nodes, get_neighbors, and bfs

## 0.2.2
- feat: run RESTful APIs directly within TigerGraphX instead of using pyTigerGraph

## 0.2.1
- feat: add simple GraphRAG
- fix: correct the image link
- docs: add documentation for Supporting Simple GraphRAG

## 0.2.0
- docs: add copywrie to all Python files; add document LICENSE
- perf: importing fewer classes in `tigergraphx/__init__.py`
- feat: add support for TigerGraph APIs (ping, gsql, get_schema)
- feat: add support for TigerGraph APIs (run_interpreted_query)
- test: add unit test cases to class TigerGraphConnectionConfig
- fix: get_schema_from_db should consider vector attributes
- fix: add multi-edge support in `get_edge_data`
- feat: add method `bfs`
- feat: integrate Ragas for GraphRAG evaluation
- feat: add Ragas-based evaluation for LightRAG
- feat: add Ragas-based evaluation for MSFT GraphRAG
- perf: replace mkdocs-jupyter with jupyter nbconvert for faster ipynb-to-md conversion
- docs: add more examples in "TigerGraphX Quick Start: Using TigerGraph as Graph Database"
- docs: add more examples in "TigerGraphX Quick Start: Using TigerGraph as Vector Database"
- docs: add more examples in "TigerGraphX Quick Start: Using TigerGraph for Graph and Vector Database"
- docs: add evaluation section to LightRAG
- docs: add evaluation content to MSFT GraphRAG
- docs: add examples for query operations APIs
- docs: add BFS example by using method get_neighbors
- docs: add examples for vector operations APIs

## 0.1.12
- docs: add CHANGELOG.md
- fix: improve error messages and logging for schema creation
- feat: add aliases to TigerGraphConnectionConfig for environment variables
- fix: correct the order of attributes when getting schema from TigerGraph
- fix: consider the discriminators in multi-edges when getting schema from TigerGraph
- fix: improve error messages and logging for data loading
- fix: support for integer node IDs
- fix: add alias to `get_nodes` and `get_neighbors` methods
- docs: add filtering on multiple attributes in the `get_nodes` example
- fix: return empty DataFrame when the result is empty for `get_nodes` and `get_neighbors` methods
- fix: check the existence of the edge types for the method `degree`, `get_node_edges` and `get_neighbors`
- fix: convert the types of `edge_types` and `target_node_types` to `Set` in the `get_neighbors` method
- fix: ensure undirected edges are counted once in `number_of_edges` method
- docs: rewrite API Reference Introduction
- docs: add examples for schema operation APIs
- docs: add examples for data loading operation APIs
- docs: add examples for node operations APIs
- docs: add examples for edge operations APIs
- docs: add examples for statistics operations APIs

---

## 0.1.11
- Initial release.
