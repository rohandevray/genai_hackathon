def retrieve_content(gcs_file_path:str , heading_number : str , heading_title : str):
    """
    Retrieves specific sections from a PDF stored in Google Cloud Storage (GCS).

    This tool processes a PDF document from a given GCS path and extracts content
    based on either a heading number or a heading title. At least one of the
    heading identifiers must be provided.

    Args:
        gcs_file_path (str): The full GCS URI for the PDF file (e.g., 'gs://my-bucket/report.pdf').
        heading_number (Optional[str]): The chapter or section number to retrieve (e.g., '3.1', '5').
        heading_title (Optional[str]): The exact title of the heading to find and retrieve.

    Prints: The relevant section extracted from the pdf 
    """
    import os
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\adini\AppData\Roaming\gcloud\application_default_credentials.json"
    from toc_extraction import extract_toc_pdf
    

    source_bucket = gcs_file_path.removeprefix("gs://").split('/')[0]
    source_blob = gcs_file_path.removeprefix("gs://").split('/', 1)[1]
    file = gcs_file_path.split('/')[-1]
    file_name = file.split('.')[0]
    print(file_name)
    result1 = extract_toc_pdf(
        source_bucket=source_bucket,
        source_blob=source_blob,
        dest_bucket="genai_ex_documents",
        dest_blob=f"content_pages/{file_name}_toc.pdf",
        verbose=True
    )


    # print("Saved file:", result["gs_uri"])
    # print("Public link:", result[" public_url"])
    # print(result["from_toc"])
    # print(result["toc_pages"])

    # 
    # print(result1["toc_pages"])
    # print(result["toc_pages"])


 

    import json
    from generate_tree_structure import generate_toc_tree_json # Assumes the function is in 'toc_parser.py'


    pdf_path = result1["gs_uri"]

    USE_FLAG = result1["from_toc"]


    print(f"Calling API to process: {pdf_path}...")

    result2 = generate_toc_tree_json(
        pdf_gcs_path=pdf_path,
        use_flag=USE_FLAG
    )
    # print("...Processing complete!")


    # print("\n-------------------- RESULTS --------------------")

    # Access and print each value from the result dictionary
    # print(f"Is TOC Numbered?: {result['is_numbered']}")
    # print(f"Last TOC Page (0-indexed): {result['last_toc_page']}")
    # print(f"Stop Heading Found: {result['stop_heading']}")

    # toc_content = result['json']

    # if isinstance(toc_content, str):
    #     # If it's a string, it's likely an error message
    #     print(f"Content: {toc_content}")
    # else:
    #     # If it's a dict or list, pretty-print it for readability
    #     print("Content (TOC Tree):")
    #     print(json.dumps(toc_content, indent=2))

    # print("---------------------------------------------")





    if USE_FLAG:
        start_page = result1["toc_pages"][result2["last_toc_page"]]+1
    else:
        start_page = result2["last_toc_page"]+1
    print(start_page)  





    import importlib
    import populate_json_content  # import the whole module

    importlib.reload(populate_json_content)  # reloads the module

        
    print("Starting content population...")
    populated_json = populate_json_content.populate_content(
        toc_json=result2["json"],
        pdf_gcs_path="genai_ex_documents/main_docs/g20_pub.pdf", 
        start_page=start_page,
        stop_heading=result2["stop_heading"],
        is_numbered=result2["is_numbered"]
    )
    print("\n...Population complete!")
    
    # --- 3. Print the final, populated JSON ---
    print("\n--- Final Populated JSON ---")
    print(json.dumps(populated_json, indent=2))
        
        
        
    import save_json
    importlib.reload(save_json) 

    json_location = save_json.save_json_to_gcs(populated_json,"gs://genai_ex_documents/Json Files/",file_name,"big-depth-471018-r6")
    from get_relevant_content import get_section_by_number,get_section_by_title




    section_data_by_number = get_section_by_number(json_location,"big-depth-471018-r6", heading_number)
    if section_data_by_number:
        print(json.dumps(section_data_by_number, indent=2))
    else:
        print("Section not found.")

    section_data_by_title = get_section_by_title(json_location,"big-depth-471018-r6", heading_title)
    if section_data_by_title:
        # The function returns a tuple: (heading_number, node_data)
        number, data = section_data_by_title
        print(f"Found Heading Number: {number}")
        print("Section Data:")
        print(json.dumps(data, indent=2))
    else:
        print("Section not found.")