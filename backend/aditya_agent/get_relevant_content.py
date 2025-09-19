from google.cloud import storage
import json

def _read_json_from_gcs(gcs_path: str, project_id: str) -> dict | None:
    """
    Downloads and reads a JSON file from a GCS path.

    Args:
        gcs_path: The full GCS path (e.g., "gs://bucket-name/folder/file.json").
        project_id: The Google Cloud project ID.

    Returns:
        The content of the JSON file as a dictionary, or None if an error occurs.
    """
    try:
        # Initialize the client and parse the GCS path
        storage_client = storage.Client(project=project_id)
        bucket_name, blob_name = gcs_path.replace("gs://", "").split("/", 1)

        # Get the bucket and blob
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Download the file content as a string
        print(f"Reading JSON from: {gcs_path}")
        json_string = blob.download_as_text()

        # Parse the string into a Python dictionary
        data = json.loads(json_string)
        return data

    except Exception as e:
        print(f"Error reading or parsing JSON from GCS: {e}")
        return None
    
def get_section_by_number(gcs_path: str, project_id: str, heading_number: str) -> dict | None:
    """
    Finds a section in a TOC JSON file on GCS using its heading number.

    Args:
        gcs_path: The GCS path to the JSON file.
        project_id: The Google Cloud project ID.
        heading_number: The exact heading number to find (e.g., "3.1.1").

    Returns:
        The dictionary node for the section if found, otherwise None.
    """
    # First, read the JSON data from the GCS path
    toc_tree = _read_json_from_gcs(gcs_path, project_id)
    if not toc_tree:
        return None  # Stop if the file could not be read or is empty

    # --- The rest of the function is the same as your original ---
    def _find_node_recursive(data: dict, key: str):
        if key in data:
            return data[key]
        
        for node_key in data:
            if "subsections" in data[node_key] and data[node_key]["subsections"]:
                found = _find_node_recursive(data[node_key]["subsections"], key)
                if found:
                    return found
        return None

    return _find_node_recursive(toc_tree, heading_number)

def get_section_by_title(gcs_path: str, project_id: str, title_query: str) -> tuple[str, dict] | None:
    """
    Finds a section in a TOC JSON file on GCS using its title.

    Args:
        gcs_path: The GCS path to the JSON file.
        project_id: The Google Cloud project ID.
        title_query: The title to search for (case-insensitive).

    Returns:
        A tuple containing (heading_number, section_node) if found, otherwise None.
    """
    # First, read the JSON data from the GCS path
    toc_tree = _read_json_from_gcs(gcs_path, project_id)
    if not toc_tree:
        return None # Stop if the file could not be read or is empty

    # --- The rest of the function is the same as your original ---
    def _find_node_recursive(data: dict, title: str):
        for heading_num, node in data.items():
            if node.get("title", "").lower().strip() == title.lower().strip():
                return (heading_num, node)
            
            if "subsections" in node and node["subsections"]:
                found = _find_node_recursive(node["subsections"], title)
                if found:
                    return found
        return None

    return _find_node_recursive(toc_tree, title_query)