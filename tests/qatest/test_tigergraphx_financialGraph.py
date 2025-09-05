import pytest
from pytest import param 
import os
from pathlib import Path
from dotenv import dotenv_values
import datetime
import yaml
import logging
import allure # Import allure

from tigergraphx.config import TigerGraphConnectionConfig, GraphSchema
from tigergraphx import Graph
from tigergraphx.core.tigergraph_api import TigerGraphAPI
from tigergraphx.core.tigergraph_api.api.base_api import TigerGraphAPIError

logger = logging.getLogger(__name__)

TEST_GRAPH_NAME = "financialGraph"

try:
    # Define the path to the YAML configuration file
    YAML_PATH = Path(__file__).parent / "config" / "tigergraphx_financialGraph.yaml"
    if not YAML_PATH.is_file():
        # If the primary YAML file is not found, raise an error immediately
        raise FileNotFoundError(f"Critical: YAML data file not found at {YAML_PATH}")

    # Load the YAML data
    with open(YAML_PATH, 'r', encoding='utf-8') as f:
        ALL_YAML_DATA = yaml.safe_load(f)
    logger.info(f"Successfully loaded all YAML data from {YAML_PATH.name} at module level.")
except Exception as e:
    # Catch any other exceptions during loading or parsing
    logger.error(f"FATAL: Failed to load or parse YAML data from {YAML_PATH}: {e}", exc_info=True)
    ALL_YAML_DATA = None


def get_test_data(test_name, *keys):
    data = ALL_YAML_DATA
    if data is None:
        return None
    
    test_section = data.get(test_name, {})
    current_level = test_section
    for key in keys:
        if not isinstance(current_level, dict):
            return None 
        current_level = current_level.get(key)
        if current_level is None:
            return None
    return current_level

class TestTigerGraphXGraphAPI:
    """Tests for the high-level tigergraphx.Graph API interacting with a real TigerGraph instance."""

    # --- 1. Extract Top-Level Data Sections from YAML --- 
    schema_dict = ALL_YAML_DATA.get("schema", {}) if ALL_YAML_DATA else {}
    
    # Get data sections specific to test functions
    add_account_data_section = get_test_data("test_add_account_nodes_from_data")
    add_single_node_data_section = get_test_data("test_add_single_node_explicitly")
    get_single_node_data_section = get_test_data("test_get_single_node_data")
    get_single_edge_data_section = get_test_data("test_get_single_edge_data")
    node_degrees_data_section = get_test_data("test_node_degrees")
    load_all_data_section = get_test_data("test_load_all_data_programmatically")
    number_of_nodes_data_section = get_test_data("test_number_of_nodes")

    # --- 2. Initialize Parameter Lists --- 
    add_account_nodes_params = []
    add_single_node_params = []
    get_single_node_data_params = []
    get_single_edge_data_params = []
    degree_test_params = []
    load_all_data_params = []
    number_of_nodes_params = []

    # --- 3. Populate Parameter Lists (Assuming YAML structure is always correct) --- 

    # Populate params for: test_add_account_nodes_from_data
    for case in add_account_data_section.get("cases", []):
        add_account_nodes_params.append(
            param(
                case.get("accounts_to_add"), 
                case.get("verify_nodes"), 
                id=case.get("id")
            )
        )

    # Populate params for: test_add_single_node_explicitly
    for case in add_single_node_data_section.get("cases", []):
        node_to_add = case.get("node_to_add")
        add_single_node_params.append(
             param(
                 node_to_add['id'], 
                 node_to_add['type'], 
                 node_to_add['attrs'], 
                 id=case.get("id")
             )
        )

    # Populate params for: test_get_single_node_data
    for case in get_single_node_data_section.get("cases", []):
        node_to_get = case.get("node_to_add")
        get_single_node_data_params.append(
             param(
                 node_to_get['id'], 
                 node_to_get['type'], 
                 node_to_get['attrs'], 
                 id=case.get("id")
             )
        )
    
    # Populate params for: test_get_single_edge_data
    for case in get_single_edge_data_section.get("cases", []):
        get_single_edge_data_params.append(
            param(
                case.get("prerequisite_nodes"), 
                case.get("edge_to_add"), 
                id=case.get("id")
            )
        )
    
    # Populate params for: test_node_degrees
    # Note: Using the existing 'degree_checks' key which is already a list
    for check in node_degrees_data_section.get("degree_checks", []):
        degree_test_params.append(
             param(
                 check["node_id"], 
                 check["node_type"], 
                 check.get("edge_types"), 
                 check["expected_degree"], 
                 id=check.get("description", f"Degree_{check['node_id']}")
             )
        )
    
    # Populate params for: test_load_all_data_programmatically
    for case in load_all_data_section.get("cases", []):
        load_all_data_params.append(
            param(
                case.get("nodes_to_load"), 
                case.get("edges_to_load"), 
                case.get("verify_points"), 
                id=case.get("id")
            )
        )

    # Populate params for: test_number_of_nodes
    for case in number_of_nodes_data_section.get("cases", []):
        number_of_nodes_params.append(
            param(
                case.get("node_type"),
                case.get("expected_count"),
                id=case.get("id")
            )
        )

    # -----------------------------------------------------------------------------

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """
        Sets up the Graph instance using class-level schema. Cleans up afterwards.
        """
        logger.info("Setting up QA test: Initializing tigergraphx.Graph...")
        if ALL_YAML_DATA is None:
            pytest.fail("Critical: YAML data failed to load at module level.")
        if not TestTigerGraphXGraphAPI.schema_dict:
             pytest.fail("Critical: Schema dictionary is empty. Check YAML structure.")

        try:
            # --- Connection Config ---
            dotenv_path = Path('.') / '.env'
            if not dotenv_path.is_file():
                 pytest.fail(".env file not found in project root.")
            config_values_from_env = dotenv_values(dotenv_path=dotenv_path)
            config_mapped = {
                "host": config_values_from_env.get("TIGERGRAPH_HOST"),
                "username": config_values_from_env.get("TIGERGRAPH_USERNAME"),
                "password": config_values_from_env.get("TIGERGRAPH_PASSWORD"),
            }
            config_mapped = {k: v for k, v in config_mapped.items() if v is not None}
            self.config = TigerGraphConnectionConfig(**config_mapped)

            # --- Schema from Class ---
            self.schema = GraphSchema(**TestTigerGraphXGraphAPI.schema_dict)

            # --- Initialize Graph ---
            logger.info(f"Initializing Graph object for graph: {self.schema.graph_name}")
            self.G = Graph(
                graph_schema=self.schema,
                tigergraph_connection_config=self.config,
                drop_existing_graph=True,
                mode="normal"
            )
            logger.info(f"Graph object for '{self.G.name}' initialized.")
            assert hasattr(self.G, '_context') and self.G._context.tigergraph_api is not None

        except Exception as e:
            pytest.fail(f"Failed during setup_teardown: {e}")

        yield 

        # --- Teardown ---
        logger.info(f"\nTearing down QA test: Dropping graph '{self.schema.graph_name}'...")
        try:
            if hasattr(self, 'G'):
                self.G.drop_graph()
                logger.info(f"Graph '{self.schema.graph_name}' dropped successfully.")
        except Exception as e:
            logger.warning(f"Warning: Error dropping graph during teardown: {e}")

    @allure.title("Verify Graph Schema Creation")
    @allure.description(
        "TestType: Positive\n"
        "Target: Check if Graph initialization correctly creates the schema in TigerGraph.\n"
        "Description: Verify graph name, node types, and edge types match the definition after G = Graph().\n"
        "Date: 2025-05-06\n"
        "Link: https://graphsql.atlassian.net/browse/TCE-6585"
    )
    def test_graph_creation_via_init(self):
        """Test schema creation during Graph initialization."""
        logger.info("Running test_graph_creation_via_init...")
        assert hasattr(self, 'G'), "Graph object 'G' not initialized in setup"
        try:
            retrieved_schema = self.G._context.tigergraph_api.get_schema(self.G.name)
            assert retrieved_schema.get("GraphName") == self.G.name
            logger.info(f"- Graph name '{self.G.name}' verified.")
            
            retrieved_nodes = {vt['Name'] for vt in retrieved_schema.get("VertexTypes", [])}
            expected_nodes = set(self.schema.nodes.keys())
            assert expected_nodes.issubset(retrieved_nodes), f"Expected node types {expected_nodes}, but found {retrieved_nodes}"
            logger.info(f"- Node types {expected_nodes} verified.")
            
            # Check edge types
            retrieved_edges = {et['Name'] for et in retrieved_schema.get("EdgeTypes", [])}
            expected_edges = set(self.schema.edges.keys())
            assert expected_edges.issubset(retrieved_edges), f"Expected edge types {expected_edges}, but found {retrieved_edges}"
            logger.info(f"- Edge types {expected_edges} verified.")
            logger.info(f"Schema for graph '{self.G.name}' verified successfully.")
        except Exception as e:
            pytest.fail(f"Failed to verify graph schema existence: {e}")

    @allure.title("Add Multiple Account Nodes from Data")
    @allure.description(
        "TestType: Positive\n"
        "Target: Verify adding multiple nodes of the same type using add_nodes_from.\n"
        "Description: Adds multiple Account nodes based on parametrized data and verifies their attributes.\n"
        "Date: 2025-05-06\n"
        "Link: https://graphsql.atlassian.net/browse/TCE-6585"
    )
    @pytest.mark.parametrize("accounts_to_add, nodes_to_verify", add_account_nodes_params)
    def test_add_account_nodes_from_data(self, accounts_to_add, nodes_to_verify):
        """Test adding multiple Account nodes using parametrized data."""
        logger.info("Running test_add_account_nodes_from_data (parametrized)...")
        assert hasattr(self, 'G'), "Graph object 'G' not initialized"
        if accounts_to_add is None or nodes_to_verify is None:
             pytest.fail("Parametrized data is missing for test_add_account_nodes_from_data")

        try:
            logger.info(f"Adding {len(accounts_to_add)} Account nodes...")
            # Convert dict format from YAML to tuple format for add_nodes_from if necessary
            nodes_for_api = [(item[0], item[1]) for item in accounts_to_add]
            self.G.add_nodes_from(nodes_for_adding=nodes_for_api, node_type="Account")

            logger.info("Verifying added nodes...")
            for verification_case in nodes_to_verify:
                node_id = verification_case['node_id']
                expected_attrs = verification_case['expected_attrs']
                logger.debug(f"Verifying node: {node_id}")
                node_data = self.G.get_node_data(node_id=node_id, node_type="Account")
                assert node_data is not None, f"Node {node_id} not found after adding."
                for attr, expected_value in expected_attrs.items():
                     assert node_data.get(attr) == expected_value, \
                         f"Node {node_id} attribute '{attr}' mismatch. Expected {expected_value}, got {node_data.get(attr)}"
            logger.info("All specified Account nodes verified successfully.")

        except Exception as e:
            pytest.fail(f"Failed during add_nodes_from or verification: {e}")

    @allure.title("Add and Remove a Single Node Explicitly")
    @allure.description(
        "TestType: Positive\n"
        "Target: Verify adding a single node with add_node and removing it with remove_node.\n"
        "Description: Adds a node, verifies its attributes, removes it, and verifies removal using has_node and get_node_data.\n"
        "Date: 2025-05-06\n"
        "Link: https://graphsql.atlassian.net/browse/TCE-6585"
    )
    @pytest.mark.parametrize("node_id, node_type, node_attrs", add_single_node_params)
    def test_add_single_node_explicitly(self, node_id, node_type, node_attrs):
        """Test adding and removing a single node using parametrized data."""
        logger.info(f"Running test_add_single_node_explicitly for node {node_id}...")
        assert hasattr(self, 'G'), "Graph object 'G' not initialized"
        if node_id is None or node_type is None or node_attrs is None:
             pytest.fail("Parametrized data is missing for test_add_single_node_explicitly")

        # --- Add ---
        try:
            logger.info(f"Adding single node: ID={node_id}, Type={node_type}, Attrs={node_attrs}")
            self.G.add_node(node_id=node_id, node_type=node_type, **node_attrs)
        except Exception as e:
             pytest.fail(f"G.add_node failed: {e}")

        # --- Verify Add ---
        try:
            retrieved_data = self.G.get_node_data(node_id=node_id, node_type=node_type)
            assert retrieved_data is not None, f"Node {node_id} not found after add."
            assert retrieved_data == node_attrs, "Retrieved attributes don't match added attributes."
            logger.info(f"Node {node_id} added and verified.")
        except Exception as e:
             pytest.fail(f"Verification after add failed: {e}")

        # --- Remove ---
        try:
            logger.info(f"Removing node {node_id}...")
            remove_result = self.G.remove_node(node_id=node_id, node_type=node_type)
            assert remove_result is True, "G.remove_node did not return True."
        except Exception as e:
            pytest.fail(f"G.remove_node failed: {e}")

        # --- Verify Remove ---
        try:
            assert self.G.has_node(node_id=node_id, node_type=node_type) is False, f"Node {node_id} still exists after removal."
            logger.info(f"Node {node_id} successfully verified as removed via has_node.")
            # Optional: Verify retrieval error
            # Replace pytest.raises with a check for None return value
            retrieved_after_remove = self.G.get_node_data(node_id=node_id, node_type=node_type)
            assert retrieved_after_remove is None, f"G.get_node_data for removed node {node_id} should return None, but got {retrieved_after_remove}"
            logger.info(f"Node {node_id} retrieval correctly returned None after removal.")
        except Exception as e:
             pytest.fail(f"Verification after remove failed: {e}")

    @allure.title("Get Single Node Data")
    @allure.description(
        "TestType: Positive\n"
        "Target: Verify retrieving data for a single node using get_node_data.\n"
        "Description: Adds a node and then verifies its attributes by retrieving it with get_node_data.\n"
        "Date: 2025-05-06\n"
        "Link: https://graphsql.atlassian.net/browse/TCE-6585"
    )
    @pytest.mark.parametrize("node_id, node_type, node_attrs", get_single_node_data_params)
    def test_get_single_node_data(self, node_id, node_type, node_attrs):
        """Test G.get_node_data using parametrized data."""
        logger.info(f"Running test_get_single_node_data for node {node_id}...")
        assert hasattr(self, 'G'), "Graph object 'G' not initialized"
        if node_id is None or node_type is None or node_attrs is None:
             pytest.fail("Parametrized data is missing for test_get_single_node_data")

        # --- Add the node first ---
        try:
            logger.info(f"Adding node {node_id} for get_node_data test...")
            self.G.add_node(node_id=node_id, node_type=node_type, **node_attrs)
        except Exception as e:
             pytest.fail(f"Setup failed: G.add_node for get_node_data test failed: {e}")

        # --- Verification using get_node_data ---
        try:
            logger.info(f"Calling G.get_node_data for {node_id}...")
            retrieved_data = self.G.get_node_data(node_id=node_id, node_type=node_type)
            assert retrieved_data is not None, f"G.get_node_data returned None."
            assert retrieved_data == node_attrs, "Retrieved data does not match added attributes."
            logger.info(f"G.get_node_data verified successfully for {node_id}.")
        except Exception as e:
            pytest.fail(f"G.get_node_data call or verification failed: {e}")

    @allure.title("Add and Get Single Edge Data")
    @allure.description(
        "TestType: Positive\n"
        "Target: Verify adding and retrieving data for a single edge.\n"
        "Description: Adds prerequisite nodes, adds a single edge using add_edge, verifies its data with get_edge_data and existence with has_edge.\n"
        "Date: 2025-05-06\n"
        "Link: https://graphsql.atlassian.net/browse/TCE-6585"
    )
    @pytest.mark.parametrize("prereq_nodes_data, edge_to_add_data", get_single_edge_data_params)
    def test_get_single_edge_data(self, prereq_nodes_data, edge_to_add_data):
        """Test adding/verifying a single edge using parametrized data."""
        logger.info("Running test_get_single_edge_data (parametrized)...")
        assert hasattr(self, 'G'), "Graph object 'G' not initialized"
        if prereq_nodes_data is None or edge_to_add_data is None:
             pytest.fail("Parametrized data is missing for test_get_single_edge_data")

        src_id = edge_to_add_data['src_id']
        tgt_id = edge_to_add_data['tgt_id']
        src_type = edge_to_add_data['src_type']
        tgt_type = edge_to_add_data['tgt_type']
        edge_type = edge_to_add_data['edge_type']
        edge_attrs = edge_to_add_data['attrs']

        # --- Add Prerequisite Nodes ---
        try:
            logger.info("Adding prerequisite nodes for edge test...")
            for node_type, nodes_list in prereq_nodes_data.items():
                if nodes_list: 
                     nodes_for_api = [(item[0], item[1]) for item in nodes_list]
                     self.G.add_nodes_from(nodes_for_adding=nodes_for_api, node_type=node_type)
            logger.info("Prerequisite nodes added.")
        except Exception as e:
             pytest.fail(f"Failed to add prerequisite nodes: {e}")

        # --- Add the Edge ---
        try:
            logger.info(f"Adding edge: {src_id} -> {tgt_id} ({edge_type})")
            self.G.add_edge(
                src_node_id=src_id, tgt_node_id=tgt_id,
                src_node_type=src_type, edge_type=edge_type, tgt_node_type=tgt_type,
                **edge_attrs
            )
        except Exception as e:
             pytest.fail(f"G.add_edge failed: {e}")

        # --- Verify Edge Data ---
        try:
            logger.info("Verifying edge using G.get_edge_data...")
            retrieved_edge_data = self.G.get_edge_data(
                 src_node_id=src_id, tgt_node_id=tgt_id,
                 src_node_type=src_type, edge_type=edge_type, tgt_node_type=tgt_type
            )
            assert retrieved_edge_data is not None
            # If edge has attributes, compare them. Otherwise, expect empty dict.
            expected_edge_data = edge_attrs if edge_attrs else {}
            assert retrieved_edge_data == expected_edge_data, \
                f"Edge data mismatch. Expected {expected_edge_data}, got {retrieved_edge_data}"
            logger.info("G.get_edge_data verified.")
        except Exception as e:
             pytest.fail(f"G.get_edge_data call or verification failed: {e}")

        # --- Verify Edge Existence ---
        try:
            logger.info("Verifying edge using G.has_edge...")
            edge_exists = self.G.has_edge(
                 src_node_id=src_id, tgt_node_id=tgt_id,
                 src_node_type=src_type, edge_type=edge_type, tgt_node_type=tgt_type
            )
            assert edge_exists is True
            logger.info("G.has_edge verified.")
        except Exception as e:
            pytest.fail(f"G.has_edge call failed unexpectedly: {e}")

    @allure.title("Verify Node Degrees")
    @allure.description(
        "TestType: Positive\n"
        "Target: Verify the correctness of the G.degree() method.\n"
        "Description: Checks the degree of specific nodes (total or for specific edge types) against expected values after loading the full dataset.\n"
        "Date: 2025-05-06\n"
        "Link: https://graphsql.atlassian.net/browse/TCE-6585"
    )
    @pytest.mark.parametrize("node_id, node_type, edge_types, expected_degree", degree_test_params)
    def test_node_degrees(self, node_id, node_type, edge_types, expected_degree):
        """Test G.degree() using parametrized check cases after loading full dataset."""
        logger.info(f"Running degree check for: Node={node_id}, Type={node_type}, Edges={edge_types}")
        assert hasattr(self, 'G'), "Graph object 'G' not initialized"

        # --- Load Full Dataset (needed for degree checks) ---
        nodes_to_load = get_test_data("test_node_degrees", "nodes_to_load")
        edges_to_load = get_test_data("test_node_degrees", "edges_to_load")

        if nodes_to_load is None or edges_to_load is None:
             pytest.fail("Data for loading nodes/edges for degree test is missing in YAML.")

        try:
            logger.info("Loading full dataset for degree test...")
            for n_type, nodes in nodes_to_load.items():
                 if nodes: self.G.add_nodes_from([(n[0], n[1]) for n in nodes], node_type=n_type)
            for e_type, edges in edges_to_load.items():
                 if edges:
                     # Need to know src/tgt types for add_edges_from
                     # This info should ideally be in the schema or YAML structure
                     # Assuming we can infer from edge type based on schema:
                     schema_edge = self.schema.edges.get(e_type)
                     if not schema_edge: pytest.fail(f"Cannot determine src/tgt types for edge type '{e_type}'")
                     src_t = schema_edge.from_node_type
                     tgt_t = schema_edge.to_node_type
                     # Handle edge attributes correctly (3rd element in tuple)
                     edges_for_api = [(e[0], e[1], e[2] if len(e)>2 else {}) for e in edges]
                     self.G.add_edges_from(edges_for_api, edge_type=e_type, src_node_type=src_t, tgt_node_type=tgt_t)
            logger.info("Full dataset loaded.")
        except Exception as e:
            pytest.fail(f"Failed during data loading for degree test: {e}")

        # --- Verify Data Loading using has_node / has_edge --- 
        logger.info("Verifying data loading using has_node/has_edge before checking degree...")
        try:
            # 1. Verify nodes existence
            logger.info("--- Verifying Node Existence ---")
            node_missing = False
            for n_type_verify, nodes_verify in nodes_to_load.items(): # Use different var names
                if nodes_verify:
                    for node_data_verify in nodes_verify:
                        node_id_verify = str(node_data_verify[0]) # Use different var name
                        logger.debug(f"Checking node: ID={node_id_verify}, Type={n_type_verify}")
                        if not self.G.has_node(node_id=node_id_verify, node_type=n_type_verify):
                             logger.error(f"FAILED: Node {node_id_verify} ({n_type_verify}) not found after loading.")
                             node_missing = True
                        # else: logger.debug("OK") # Optional: log success too
            if node_missing:
                 pytest.fail("One or more nodes failed existence check after loading.")
            else:
                 logger.info("All nodes checked exist.")
            logger.info("--- Node Existence Verified ---")

            # 2. Verify edges existence (checks each edge instance from YAML)
            logger.info("--- Verifying Edge Existence ---")
            edge_missing = False
            for e_type_verify, edges_verify in edges_to_load.items(): # Use different var names
                if edges_verify:
                     schema_edge = self.schema.edges.get(e_type_verify)
                     src_t = schema_edge.from_node_type
                     tgt_t = schema_edge.to_node_type
                     for edge_data_verify in edges_verify: # Use different var name
                         src_id_verify = str(edge_data_verify[0]) # Use different var name
                         tgt_id_verify = str(edge_data_verify[1]) # Use different var name
                         # Include discriminator info in log if present (for transfer edges)
                         edge_desc = f"{src_id_verify}({src_t}) -[{e_type_verify}]-> {tgt_id_verify}({tgt_t})"
                         if e_type_verify == 'transfer' and len(edge_data_verify) > 2 and 'transaction_id' in edge_data_verify[2]:
                             edge_desc += f" (tx: {edge_data_verify[2]['transaction_id']})"
                         logger.debug(f"Checking edge: {edge_desc}")
                         # Note: We rely on has_edge implementation here.
                         # If it doesn't check discriminators, this might pass even if only one multi-edge exists.
                         if not self.G.has_edge(src_node_id=src_id_verify, tgt_node_id=tgt_id_verify, src_node_type=src_t, edge_type=e_type_verify, tgt_node_type=tgt_t):
                             logger.error(f"FAILED: Edge {edge_desc} not found after loading.")
                             edge_missing = True
                         # else: logger.debug("OK") # Optional: log success too
            if edge_missing:
                 pytest.fail("One or more edges failed existence check after loading.")
            else:
                 logger.info("All edges checked exist (via has_edge)." )
            logger.info("--- Edge Existence Verified ---")

        except Exception as ve:
            logger.error(f"Verification of data loading failed unexpectedly: {ve}", exc_info=True)
            pytest.fail(f"Verification of data loading failed: {ve}")
        # --- End Verify Data Loading ---

        # --- Verify Degree ---
        try:
            # IMPORTANT: Use the original node_id and node_type parameters passed to the function
            logger.info(f"Calculating degree for {node_id} ({node_type})..." ) 
            actual_degree = self.G.degree(node_id=node_id, node_type=node_type, edge_types=edge_types)
            assert actual_degree == expected_degree, \
                f"Degree mismatch for {node_id}. Expected {expected_degree}, Got {actual_degree}"
            logger.info(f"Degree verified for {node_id}: {actual_degree}")
        except Exception as e:
            pytest.fail(f"G.degree() call or verification failed for {node_id}: {e}")

    @allure.title("Verify Bulk Data Loading and Graph State")
    @allure.description(
        "TestType: Positive\n"
        "Target: Verify the process of loading nodes/edges programmatically and check graph state afterwards.\n"
        "Description: Loads the full dataset using add_nodes_from/add_edges_from and performs verification checks.\n"
        "Date: 2025-05-06\n"
        "Link: https://graphsql.atlassian.net/browse/TCE-6585"
    )
    @pytest.mark.parametrize("nodes_to_load, edges_to_load, verification_points", load_all_data_params)
    def test_load_all_data_programmatically(self, nodes_to_load, edges_to_load, verification_points):
        """Test loading all nodes/edges using parametrized data and verify."""
        logger.info("Running test_load_all_data_programmatically (parametrized)...")
        assert hasattr(self, 'G'), "Graph object 'G' not initialized"
        if nodes_to_load is None or edges_to_load is None or verification_points is None:
             pytest.fail("Parametrized data is missing for test_load_all_data_programmatically")

        # --- Load Nodes & Edges ---
        try:
            logger.info("Loading all nodes...")
            for n_type, nodes in nodes_to_load.items():
                 if nodes: self.G.add_nodes_from([(n[0], n[1]) for n in nodes], node_type=n_type)
            logger.info("Loading all edges...")
            for e_type, edges in edges_to_load.items():
                 if edges:
                     schema_edge = self.schema.edges.get(e_type)
                     if not schema_edge: pytest.fail(f"Cannot determine src/tgt types for edge type '{e_type}'")
                     src_t = schema_edge.from_node_type
                     tgt_t = schema_edge.to_node_type
                     # Handle edge attributes correctly (3rd element in tuple)
                     edges_for_api = [(e[0], e[1], e[2] if len(e)>2 else {}) for e in edges]
                     self.G.add_edges_from(edges_for_api, edge_type=e_type, src_node_type=src_t, tgt_node_type=tgt_t)
            logger.info("All data loaded programmatically.")
        except Exception as e:
             pytest.fail(f"Failed during bulk data loading: {e}")

        # --- Verification ---
        logger.info("Performing verification...")
        try:
            for point in verification_points:
                verify_type = point.get("type")
                if verify_type == "node":
                    node_id = point["node_id"]
                    node_type = point["node_type"]
                    expected_attrs = point["expected_attrs"]
                    logger.debug(f"Verifying node {node_id}...")
                    node_data = self.G.get_node_data(node_id=node_id, node_type=node_type)
                    assert node_data is not None
                    for attr, val in expected_attrs.items():
                         assert node_data.get(attr) == val, f"Node {node_id} attr {attr} mismatch"
                elif verify_type == "edge_count":
                     # Example: Verify edge count using underlying API 
                     logger.debug(f"Verifying edge count for {point['edge_type']}...")
                     edges = self.G._context.tigergraph_api.retrieve_a_edge(
                         self.G.name, point['src_type'], point['src_id'],
                         point['edge_type'], point['tgt_type'], point['tgt_id']
                     )
                     assert len(edges) == point['expected_count'], \
                         f"Edge count mismatch for {point['src_id']}->{point['tgt_id']}. Expected {point['expected_count']}, Got {len(edges)}"
                # Add more verification types if needed
            logger.info("Data loading and verification successful.")
        except Exception as e:
            pytest.fail(f"Failed during verification phase: {e}")

    @allure.title("Verify Number of Nodes")
    @allure.description(
        "TestType: Positive\n"
        "Target: Verify the correctness of the G.number_of_nodes() method.\n"
        "Description: Loads the full dataset and checks the total node count and counts for specific types.\n"
        "Date: 2025-05-06\n"
        "Link: https://graphsql.atlassian.net/browse/TCE-6585"
    )
    @pytest.mark.parametrize("node_type, expected_count", number_of_nodes_params)
    def test_number_of_nodes(self, node_type, expected_count):
        """Test G.number_of_nodes() with and without type filter."""
        logger.info(f"Running number_of_nodes check: Type={node_type}, Expected={expected_count}")
        assert hasattr(self, 'G'), "Graph object 'G' not initialized"

        # --- Load Full Dataset (needed for counting) --- 
        # Access class attribute correctly AND navigate the 'cases' list structure
        load_all_case_data = TestTigerGraphXGraphAPI.load_all_data_section.get("cases", [])[0] # Get the first case
        nodes_to_load = load_all_case_data.get("nodes_to_load")
        edges_to_load = load_all_case_data.get("edges_to_load") 
        if nodes_to_load is None or edges_to_load is None:
             pytest.fail("Data for loading nodes/edges for number_of_nodes test is missing.")
        
        try:
            logger.info("Loading full dataset for number_of_nodes test...")
            # Load Nodes
            for n_type, nodes in nodes_to_load.items():
                 if nodes: self.G.add_nodes_from([(n[0], n[1]) for n in nodes], node_type=n_type)
            # Load Edges (Optional for node count, but good for consistency if reusing data)
            for e_type, edges in edges_to_load.items():
                 if edges:
                     schema_edge = self.schema.edges.get(e_type)
                     if not schema_edge: pytest.fail(f"Cannot determine src/tgt types for edge type '{e_type}'")
                     src_t = schema_edge.from_node_type
                     tgt_t = schema_edge.to_node_type
                     edges_for_api = [(e[0], e[1], e[2] if len(e)>2 else {}) for e in edges]
                     self.G.add_edges_from(edges_for_api, edge_type=e_type, src_node_type=src_t, tgt_node_type=tgt_t)
            logger.info("Full dataset loaded for node count test.")
        except Exception as e:
            pytest.fail(f"Failed during data loading for number_of_nodes test: {e}")
        # ---

        # --- Verify Node Count --- 
        try:
            logger.info(f"Calling G.number_of_nodes(node_type={node_type})...")
            actual_count = self.G.number_of_nodes(node_type=node_type)
            assert actual_count == expected_count, \
                f"Node count mismatch. Expected {expected_count}, Got {actual_count} for type '{node_type}'"
            logger.info(f"Node count verified: {actual_count} for type '{node_type}'.")
        except Exception as e:
             pytest.fail(f"G.number_of_nodes() call or verification failed: {e}")

    @allure.title("Verify Number of Edges")
    @allure.description(
        "TestType: Positive\n"
        "Target: Verify the correctness of the G.number_of_edges() method.\n"
        "Description: Loads the full dataset and checks the total edge count, counts for specific types, and error handling for invalid types.\n"
        "Date: 2025-05-06\n"
        "Link: https://graphsql.atlassian.net/browse/TCE-6585"
    )
    def test_number_of_edges(self):
        """Tests the number_of_edges method with data loading."""
        logger.info("Running full test_number_of_edges with data loading...")
        assert hasattr(self, 'G'), "Graph object 'G' not initialized"
        G = self.G # Use the graph instance from setup

        # --- Load Full Dataset (Required for accurate counts) ---
        # Use data defined for the full load test case in YAML
        load_all_case_data = TestTigerGraphXGraphAPI.load_all_data_section.get("cases", [{}])[0]
        nodes_to_load = load_all_case_data.get("nodes_to_load")
        edges_to_load_raw = load_all_case_data.get("edges_to_load") # This is a dict {edge_type: list_of_edges}

        if not nodes_to_load or not edges_to_load_raw:
             pytest.fail("Data for loading nodes/edges for number_of_edges test is missing in YAML under test_load_all_data_programmatically.")

        all_edges_list_for_count = [] # Keep a flat list for total count verification
        try:
            logger.info("Loading full dataset for number_of_edges test...")
            # Load Nodes first to ensure they exist for edges
            for n_type, nodes in nodes_to_load.items():
                 if nodes: G.add_nodes_from([(n[0], n[1]) for n in nodes], node_type=n_type)

            # Load Edges and populate the flat list for counting
            for e_type, edges in edges_to_load_raw.items():
                 if edges:
                     schema_edge = self.schema.edges.get(e_type)
                     if not schema_edge: pytest.fail(f"Cannot determine src/tgt types for edge type '{e_type}' from schema.")
                     src_t = schema_edge.from_node_type
                     tgt_t = schema_edge.to_node_type
                     # Prepare edges: (src_id, tgt_id, attrs) - Ensure IDs are strings
                     edges_for_api = [(str(e[0]), str(e[1]), e[2] if len(e)>2 else {}) for e in edges]
                     G.add_edges_from(edges_for_api, edge_type=e_type, src_node_type=src_t, tgt_node_type=tgt_t)
                     all_edges_list_for_count.extend(edges) # Add original edge definition to flat list

            logger.info(f"Full dataset loaded: {len(nodes_to_load)} node types, {len(all_edges_list_for_count)} total edges planned.")
        except Exception as e:
            logger.error(f"Error during data loading: {e}", exc_info=True)
            pytest.fail(f"Failed during data loading for number_of_edges test: {e}")
        # ---

        # 1. Check total number of edges
        expected_total_edges = len(all_edges_list_for_count)
        try:
            actual_total_edges = G.number_of_edges()
            logger.info(f"Verifying total edge count: Expected={expected_total_edges}, Actual={actual_total_edges}")
            assert actual_total_edges == expected_total_edges, f"Total edge count mismatch. Expected {expected_total_edges}, got {actual_total_edges}."
        except Exception as e:
             logger.error(f"Error calling G.number_of_edges() for total count: {e}", exc_info=True)
             pytest.fail(f"G.number_of_edges() for total count failed: {e}")

        # 2. Check count for specific edge types loaded
        expected_counts_by_type = {e_type: len(edges) for e_type, edges in edges_to_load_raw.items() if edges}
        logger.info(f"Verifying counts by type: Expected={expected_counts_by_type}")
        for edge_type, expected_count in expected_counts_by_type.items():
            try:
                actual_count = G.number_of_edges(edge_type=edge_type)
                logger.debug(f"Checking type '{edge_type}': Expected={expected_count}, Actual={actual_count}")
                assert actual_count == expected_count, f"Edge count mismatch for type '{edge_type}'. Expected {expected_count}, got {actual_count}."
            except Exception as e:
                logger.error(f"Error calling G.number_of_edges(edge_type='{edge_type}'): {e}", exc_info=True)
                pytest.fail(f"G.number_of_edges(edge_type='{edge_type}') failed: {e}")

        invalid_edge_type = "non_existent_edge_type"
        logger.info(f"Verifying error handling for invalid edge type: {invalid_edge_type}")
        try:
            with pytest.raises(ValueError) as excinfo:
                G.number_of_edges(edge_type=invalid_edge_type)
            assert f"Edge type '{invalid_edge_type}' is not defined" in str(excinfo.value)
            logger.info("ValueError raised as expected for invalid edge type.")
        except Exception as e:
             logger.error(f"Error during invalid edge type check: {e}", exc_info=True)
             pytest.fail(f"Check for invalid edge type failed unexpectedly: {e}")
