#!/usr/bin/env python3
"""
Real mode test script for API search capabilities using MCP.
Tests searching for Discord messaging and Spotify track-related workflows.
"""

import json
import os
import subprocess
import sys
import time


def run_search_test(description, keywords, expected_term, timeout=10):
    """Run a search test against the MCP server.

    Args:
        description: The capability description to search for
        keywords: List of keywords to include in the search
        expected_term: Term expected to be found in the response
        timeout: Timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    print(f"\n==== TESTING SEARCH: {description} ====")

    # Format the keywords as a JSON array
    keywords_json = json.dumps(keywords)

    # Build the JSON request
    request = f'{{"type":"search_apis","data":{{"capability_description":"{description}","keywords":{keywords_json}}}}}'

    # Construct the pipeline command
    cmd = f"echo '{request}' | {sys.executable} -m mcp.main serve --transport stdio"

    # Run the command with timeout
    try:
        print(f"Running search for: {description}")
        print(f"Keywords: {', '.join(keywords)}")
        print("Command:", cmd)
        print(f"\nExecuting (timeout: {timeout}s)...\n")

        # Use timeout to ensure it doesn't hang
        result = subprocess.run(cmd, shell=True, timeout=timeout, text=True, capture_output=True)

        # Print output header lines and the JSON response separately
        if result.stdout:
            # Split the output into lines
            lines = result.stdout.splitlines()

            # Print the header lines (non-JSON)
            print("\nServer startup logs:")
            for line in lines:
                if not line.strip().startswith("{"):
                    print(f"  {line}")

            # Find and parse the JSON response
            json_response = None
            for line in lines:
                if line.strip().startswith("{"):
                    json_response = line
                    break

            if json_response:
                try:
                    # Try to parse and pretty-print the JSON
                    data = json.loads(json_response)
                    print("\nJSON Response:")
                    print(
                        json.dumps(data, indent=2)[:1000] + "..."
                        if len(json.dumps(data, indent=2)) > 1000
                        else json.dumps(data, indent=2)
                    )

                    # Check if we got the expected matches
                    if "result" in data and "matches" in data["result"]:
                        matches = data["result"]["matches"]

                        # Look for APIs with the expected term
                        matching_apis = [
                            api
                            for api in matches
                            if expected_term.lower() in json.dumps(api).lower()
                        ]

                        if matching_apis:
                            print(f"\n✅ Successfully found {expected_term} results in response!")

                            # Print information about matching APIs
                            print(f"\nFound {len(matching_apis)} relevant APIs:")
                            for api in matching_apis:
                                print(
                                    f"- {api.get('api_id', 'Unknown')}: {api.get('api_name', 'No name')}"
                                )

                                # Show workflows
                                if "workflows" in api:
                                    print(f"  Has {len(api['workflows'])} workflows:")
                                    for workflow in api["workflows"]:
                                        workflow_id = workflow.get("workflow_id", "")
                                        match_score = workflow.get("match_score", 0)
                                        print(f"  - {workflow_id} (match: {match_score:.2f})")

                            return True
                        else:
                            print(f"\n❌ No {expected_term} results found in response.")
                    else:
                        print("\n❌ Invalid response format or no matches found.")
                except json.JSONDecodeError as e:
                    print(f"\n❌ Failed to parse JSON response: {e}")
                    print(f"Raw JSON: {json_response}")
            else:
                print("\n❌ No JSON response found in output.")
        else:
            print("\n❌ No output received from command.")

        # Print errors
        if result.stderr:
            print("\nSTDERR:")
            for line in result.stderr.splitlines():
                print(f"  {line}")

        print(f"\nCommand exited with code: {result.returncode}")

    except subprocess.TimeoutExpired:
        print(f"\n⚠️ Command timed out after {timeout} seconds")
    except Exception as e:
        print(f"\n❌ Error running command: {e}")

    return False


def run_selection_test(project_dir, api_id, api_name, workflows, timeout=15):
    """Run a test to create a selection set, update it, and generate a config.

    Args:
        project_dir: The project directory to use
        api_id: The API ID to include in the selection
        api_name: The API name
        workflows: List of workflow IDs to include
        timeout: Timeout in seconds

    Returns:
        Tuple of (success, selection_id, config_path)
    """
    print(f"\n==== TESTING SELECTION & CONFIG GENERATION FOR {api_name} ====")

    # Make sure the project directory exists and is absolute
    project_dir = os.path.abspath(project_dir)
    os.makedirs(project_dir, exist_ok=True)
    print(f"Project directory: {project_dir}")

    # Ensure .jentic/selection_sets directory exists (this is where selection sets are stored)
    selection_sets_dir = os.path.join(project_dir, ".jentic", "selection_sets")
    os.makedirs(selection_sets_dir, exist_ok=True)
    print(f"Selection sets directory: {selection_sets_dir}")

    # Step 1: Create a selection set
    print("\n1. CREATING SELECTION SET...")

    create_request = (
        f'{{"type":"create_selection_set","data":{{"project_directory":"{project_dir}"}}}}'
    )
    create_cmd = f"echo '{create_request}' | {sys.executable} -m mcp.main serve --transport stdio"

    try:
        # Create the selection set
        result = subprocess.run(
            create_cmd, shell=True, timeout=timeout, text=True, capture_output=True
        )

        # Find the JSON response
        json_response = None
        selection_id = None

        for line in result.stdout.splitlines():
            if line.strip().startswith("{"):
                json_response = line.strip()
                break

        if json_response:
            data = json.loads(json_response)
            if "result" in data and "selection_id" in data["result"]:
                selection_id = data["result"]["selection_id"]
                print(f"✅ Selection set created successfully: {selection_id}")
            else:
                print("❌ Failed to get selection ID from response")
                print(f"Response: {data}")
                return False, None, None
        else:
            print("❌ No JSON response received for create_selection_set")
            print(f"STDOUT: {result.stdout}")
            return False, None, None

        # Step 2: Update the selection set
        print(f"\n2. UPDATING SELECTION SET ({selection_id})...")

        # Create the update request - include project_directory both at root level AND in generation_config
        update_data = {
            "selection_id": selection_id,
            "project_directory": project_dir,  # Critical for selection set lookup!
            "apis_to_add": [
                {
                    "api_id": api_id,
                    "api_name": api_name,
                    "include_all_endpoints": False,
                    "selected_workflows": workflows,
                    "selected_endpoints": [],  # Workflows define which endpoints are needed
                }
            ],
            "generation_config": {
                "project_directory": project_dir,
                "framework": "direct",
                "language": "python",
                "include_examples": True,
                "optimization_level": "balanced",
            },
        }

        update_request = f'{{"type":"update_selection_set","data":{json.dumps(update_data)}}}'
        update_cmd = (
            f"echo '{update_request}' | {sys.executable} -m mcp.main serve --transport stdio"
        )

        # Update the selection set
        result = subprocess.run(
            update_cmd, shell=True, timeout=timeout, text=True, capture_output=True
        )

        # Find the JSON response
        json_response = None
        update_success = False

        for line in result.stdout.splitlines():
            if line.strip().startswith("{"):
                json_response = line.strip()
                break

        if json_response:
            data = json.loads(json_response)
            if "result" in data and data["result"].get("success") is True:
                update_success = True
                print(f"✅ Selection set updated successfully with {api_name} workflows")
            else:
                print("❌ Failed to update selection set")
                print(f"Response: {data}")
                return False, selection_id, None
        else:
            print("❌ No JSON response received for update_selection_set")
            print(f"STDOUT: {result.stdout}")
            return False, selection_id, None

        # Step 3: Generate config
        print(f"\n3. GENERATING CONFIG FROM SELECTION ({selection_id})...")

        generate_data = {
            "selection_id": selection_id,
            "project_directory": project_dir,  # Critical for selection set lookup
        }

        generate_request = f'{{"type":"generate_config","data":{json.dumps(generate_data)}}}'
        generate_cmd = (
            f"echo '{generate_request}' | {sys.executable} -m mcp.main serve --transport stdio"
        )

        # Generate the config
        result = subprocess.run(
            generate_cmd, shell=True, timeout=timeout, text=True, capture_output=True
        )

        # Find the JSON response
        json_response = None
        config_path = None
        docs_path = None

        for line in result.stdout.splitlines():
            if line.strip().startswith("{"):
                json_response = line.strip()
                break

        if json_response:
            data = json.loads(json_response)
            if "result" in data and data["result"].get("success") is True:
                config_path = data["result"].get("config_path")
                docs_path = data["result"].get("documentation_path")

                # Print config details
                print("✅ Config generated successfully!")
                print(f"   Config file: {config_path}")
                print(f"   Documentation: {docs_path}")

                # Check that the files were actually created
                if os.path.exists(config_path):
                    print(f"   Config file exists: {os.path.getsize(config_path)} bytes")

                    # Print a preview of the config
                    print("\n   Config preview:")
                    with open(config_path) as f:
                        content = f.read()
                        print(f"   {content[:300]}...")
                else:
                    print(f"❌ Config file not found at {config_path}")

                if os.path.exists(docs_path):
                    print(f"   Documentation file exists: {os.path.getsize(docs_path)} bytes")
                else:
                    print(f"❌ Documentation file not found at {docs_path}")

                return True, selection_id, config_path
            else:
                print("❌ Failed to generate config")
                print(f"Response: {data}")
                return False, selection_id, None
        else:
            print("❌ No JSON response received for generate_config")
            print(f"STDOUT: {result.stdout}")
            return False, selection_id, None

    except subprocess.TimeoutExpired:
        print(f"⚠️ Command timed out after {timeout} seconds")
    except Exception as e:
        print(f"❌ Error running selection test: {e}")

    return False, None, None


def run_combined_selection_test(project_dir, apis, timeout=30):
    """Run a test to create a single selection set with multiple APIs.

    Args:
        project_dir: The project directory to use
        apis: List of API configurations, each with id, name, and workflows
        timeout: Timeout in seconds

    Returns:
        Tuple of (success, selection_id, config_path)
    """
    print("\n==== TESTING COMBINED SELECTION WITH MULTIPLE APIS ====")

    # Make sure the project directory exists and is absolute
    project_dir = os.path.abspath(project_dir)
    os.makedirs(project_dir, exist_ok=True)
    print(f"Project directory: {project_dir}")

    # Ensure .jentic/selection_sets directory exists (this is where selection sets are stored)
    selection_sets_dir = os.path.join(project_dir, ".jentic", "selection_sets")
    os.makedirs(selection_sets_dir, exist_ok=True)
    print(f"Selection sets directory: {selection_sets_dir}")

    # Step 1: Create a selection set
    print("\n1. CREATING COMBINED SELECTION SET...")

    create_request = (
        f'{{"type":"create_selection_set","data":{{"project_directory":"{project_dir}"}}}}'
    )
    create_cmd = f"echo '{create_request}' | {sys.executable} -m mcp.main serve --transport stdio"

    try:
        # Create the selection set
        result = subprocess.run(
            create_cmd, shell=True, timeout=timeout, text=True, capture_output=True
        )

        # Find the JSON response
        json_response = None
        selection_id = None

        for line in result.stdout.splitlines():
            if line.strip().startswith("{"):
                json_response = line.strip()
                break

        if json_response:
            data = json.loads(json_response)
            if "result" in data and "selection_id" in data["result"]:
                selection_id = data["result"]["selection_id"]
                print(f"✅ Combined selection set created successfully: {selection_id}")
            else:
                print("❌ Failed to get selection ID from response")
                print(f"Response: {data}")
                return False, None, None
        else:
            print("❌ No JSON response received for create_selection_set")
            print(f"STDOUT: {result.stdout}")
            return False, None, None

        # Step 2: Update the selection set with each API
        for i, api in enumerate(apis):
            print(f"\n2.{i+1}. ADDING API: {api['name']} to selection set...")

            # Create the update request - include project_directory
            update_data = {
                "selection_id": selection_id,
                "project_directory": project_dir,  # Critical for selection set lookup!
                "apis_to_add": [
                    {
                        "api_id": api["id"],
                        "api_name": api["name"],
                        "include_all_endpoints": False,
                        "selected_workflows": api["workflows"],
                        "selected_endpoints": [],  # Workflows define which endpoints are needed
                    }
                ],
                "generation_config": {
                    "project_directory": project_dir,
                    "framework": "direct",
                    "language": "python",
                    "include_examples": True,
                    "optimization_level": "balanced",
                },
            }

            update_request = f'{{"type":"update_selection_set","data":{json.dumps(update_data)}}}'
            update_cmd = (
                f"echo '{update_request}' | {sys.executable} -m mcp.main serve --transport stdio"
            )

            # Update the selection set
            result = subprocess.run(
                update_cmd, shell=True, timeout=timeout, text=True, capture_output=True
            )

            # Find the JSON response
            json_response = None
            update_success = False

            for line in result.stdout.splitlines():
                if line.strip().startswith("{"):
                    json_response = line.strip()
                    break

            if json_response:
                data = json.loads(json_response)
                if "result" in data and data["result"].get("success") is True:
                    update_success = True
                    print(f"✅ Selection set updated successfully with {api['name']}")
                else:
                    print(f"❌ Failed to update selection set with {api['name']}")
                    print(f"Response: {data}")
                    return False, selection_id, None
            else:
                print("❌ No JSON response received for update_selection_set")
                print(f"STDOUT: {result.stdout}")
                return False, selection_id, None

        # Step 3: Generate config from the combined selection set
        print(f"\n3. GENERATING CONFIG FROM COMBINED SELECTION ({selection_id})...")

        generate_data = {
            "selection_id": selection_id,
            "project_directory": project_dir,  # Critical for selection set lookup
        }

        generate_request = f'{{"type":"generate_config","data":{json.dumps(generate_data)}}}'
        generate_cmd = (
            f"echo '{generate_request}' | {sys.executable} -m mcp.main serve --transport stdio"
        )

        # Generate the config
        result = subprocess.run(
            generate_cmd, shell=True, timeout=timeout, text=True, capture_output=True
        )

        # Find the JSON response
        json_response = None
        config_path = None
        docs_path = None

        for line in result.stdout.splitlines():
            if line.strip().startswith("{"):
                json_response = line.strip()
                break

        if json_response:
            data = json.loads(json_response)
            if "result" in data and data["result"].get("success") is True:
                config_path = data["result"].get("config_path")
                docs_path = data["result"].get("documentation_path")

                # Print config details
                print("✅ Combined config generated successfully!")
                print(f"   Config file: {config_path}")
                print(f"   Documentation: {docs_path}")

                # Check that the files were actually created
                if os.path.exists(config_path):
                    print(f"   Config file exists: {os.path.getsize(config_path)} bytes")

                    # Print a preview of the config
                    print("\n   Config preview:")
                    with open(config_path) as f:
                        content = f.read()
                        print(f"   {content[:300]}...")

                        # Check if the config contains all APIs
                        all_apis_included = True
                        for api in apis:
                            if api["id"] not in content:
                                all_apis_included = False
                                print(
                                    f"   ⚠️ Warning: API {api['id']} ({api['name']}) not found in config"
                                )

                        if all_apis_included:
                            print(f"   ✓ All {len(apis)} APIs are included in the config!")
                else:
                    print(f"❌ Config file not found at {config_path}")

                if os.path.exists(docs_path):
                    print(f"   Documentation file exists: {os.path.getsize(docs_path)} bytes")
                else:
                    print(f"❌ Documentation file not found at {docs_path}")

                return True, selection_id, config_path
            else:
                print("❌ Failed to generate config")
                print(f"Response: {data}")
                return False, selection_id, None
        else:
            print("❌ No JSON response received for generate_config")
            print(f"STDOUT: {result.stdout}")
            return False, selection_id, None

    except subprocess.TimeoutExpired:
        print(f"⚠️ Command timed out after {timeout} seconds")
    except Exception as e:
        print(f"❌ Error running selection test: {e}")

    return False, None, None


def main():
    """Run tests for API search, selection, and config generation."""
    print("\n===== REAL MODE MCP API INTEGRATION TESTS =====")

    # Create a timestamp for unique test directory
    timestamp = int(time.time())
    integration_test_dir = os.path.abspath(
        os.path.join(os.getcwd(), ".test_output", "integration_test")
    )

    # Clean up previous test output to avoid interference
    if os.path.exists(integration_test_dir):
        print(f"Removing previous test directory: {integration_test_dir}")
        import shutil

        shutil.rmtree(integration_test_dir)

    # Create test output directory
    os.makedirs(integration_test_dir, exist_ok=True)
    print(f"Test output directory: {integration_test_dir}")

    # Track test results
    results = {}
    combined_result = None

    # Test 1: Discord messaging
    results["discord"] = run_search_test(
        "send a message to a channel on discord using a bot",
        ["discord", "message", "channel", "bot"],
        "discord",
    )

    # Test 2: Spotify tracks
    results["spotify"] = run_search_test(
        "get lists of tracks and play tracks from spotify",
        ["spotify", "tracks", "music", "play"],
        "spotify",
    )

    # If search tests were successful, run the combined selection test
    if results["discord"] and results["spotify"]:
        # Define the APIs to include
        apis = [
            {
                "id": "1f91556fe059ac592214c39b0f8c24c1",
                "name": "Discord API",
                "workflows": ["postChannelMessage"],
            },
            {
                "id": "b61b046fe20a652703c63f3d23cbccf7",
                "name": "Spotify API",
                "workflows": ["searchTracks", "getTrackDetails"],
            },
        ]

        # Run the combined selection test
        combined_result = run_combined_selection_test(integration_test_dir, apis, timeout=30)

    # Print summary
    print("\n===== TEST RESULTS SUMMARY =====")

    # Search tests summary
    print("\nAPI SEARCH TESTS:")
    for test, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {test.upper()} Search: {status}")

    # Combined selection test summary
    print("\nCOMBINED SELECTION & CONFIG TEST:")
    if combined_result and isinstance(combined_result, tuple) and len(combined_result) >= 1:
        combined_success = combined_result[0]
        status = "✅ PASSED" if combined_success else "❌ FAILED"
        print(f"  Combined Selection with Multiple APIs: {status}")
    else:
        combined_success = False
        print("  Combined Selection with Multiple APIs: ❌ NOT RUN")

    # Overall results
    search_success = all(results.values())

    print(f"\nSearch Tests: {'✅ ALL PASSED' if search_success else '❌ SOME FAILED'}")
    print(f"Combined Selection Test: {'✅ PASSED' if combined_success else '❌ FAILED'}")

    print(f"\nTest output directory: {integration_test_dir}")
    print("Note: The generated files are preserved in this directory for inspection.")

    # List the config file if it was created
    if (
        combined_result
        and isinstance(combined_result, tuple)
        and len(combined_result) >= 3
        and combined_result[2]
    ):
        config_path = combined_result[2]
        print("\nGenerated config file:")
        print(f"  {config_path}")

    # Print the selection_sets directory location
    selection_sets_dir = os.path.join(integration_test_dir, ".jentic", "selection_sets")
    if os.path.exists(selection_sets_dir):
        print(f"\nSelection sets directory: {selection_sets_dir}")

    print("\nTests completed\n")

    # Exit with status code based on test results
    sys.exit(0 if search_success and combined_success else 1)


if __name__ == "__main__":
    main()
