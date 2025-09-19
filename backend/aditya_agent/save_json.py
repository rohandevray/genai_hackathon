import os
import json
from google.cloud import storage

def save_json_to_gcs(data: dict, destination_gcs_path: str, file_name: str, project_id: str):
    """
    Saves a dictionary as a JSON file to a specific GCS location.

    If a file with the same name already exists, it appends a number
    (e.g., file_name_json_1.json, file_name_json_2.json) to find a unique name.

    Args:
        data: The dictionary (JSON object) to save.
        destination_gcs_path: The GCS folder path (e.g., "gs://bucket-name/folder/").
        file_name: The base name for the output file (e.g., "my_document").
        project_id: The Google Cloud project ID.
        
    Returns:
        The GCS path of the saved file as a string, or None if an error occurred.
    """
    try:
        # Ensure the destination path ends with a slash for proper joining
        if not destination_gcs_path.endswith('/'):
            destination_gcs_path += '/'
            
        bucket_name, directory = destination_gcs_path.replace("gs://", "").split("/", 1)
        
        # Initialize client with project ID and get bucket
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)

        # --- NEW: Logic to find a unique filename ---
        base_name_part = f"{file_name}_json"
        extension = ".json"
        
        # 1. Start with the original proposed filename
        output_filename = f"{base_name_part}{extension}"
        output_blob_name = os.path.join(directory, output_filename)
        
        counter = 1
        # 2. Loop as long as a file with the current name exists
        while bucket.blob(output_blob_name).exists():
            print(f"File 'gs://{bucket_name}/{output_blob_name}' already exists. Saving with different name.")
            # 3. Create a new filename with a counter
            new_filename = f"{base_name_part}_{counter}{extension}"
            output_blob_name = os.path.join(directory, new_filename)
            counter += 1
        # --- End of new logic ---

        print(f"Attempting to save JSON to: gs://{bucket_name}/{output_blob_name}")
        json_loc = f'gs://{bucket_name}/{output_blob_name}'
        
        # Create a new blob for the final unique name and upload the data
        blob = bucket.blob(output_blob_name)
        json_data = json.dumps(data, indent=2)
        blob.upload_from_string(json_data, content_type="application/json")
        
        print(f"Successfully saved JSON to GCS at: {json_loc}")
        return json_loc
        
    except Exception as e:
        print(f"Error saving JSON to GCS: {e}")
        return None