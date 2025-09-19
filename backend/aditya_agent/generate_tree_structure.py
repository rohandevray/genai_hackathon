import json
import vertexai
from vertexai.generative_models import GenerativeModel, Part

# Initialize Vertex AI
vertexai.init(
    project="big-depth-471018-r6",
    location="us-central1"
)

def generate_toc_tree_json(pdf_gcs_path: str, use_flag: bool) -> dict:
    """
    Generates a hierarchical JSON structure from a TOC PDF using Gemini.
    The model also identifies the heading that marks the end of the main content.

    Args:
        pdf_gcs_path (str): GCS path to the PDF (e.g., gs://bucket_name/path/to.pdf).
        use_flag (bool): Boolean flag to decide which prompt style to use.

    Returns:
        dict: {
            "json": dict | list | str (TOC data or error string),
            "is_numbered": bool,
            "last_toc_page": int,
            "stop_heading": str | None
        }
    """

    model = GenerativeModel("gemini-2.5-pro")

    # --- Prompt when use_flag = True ---
    prompt_case_true = """
    You are given a PDF document where most, if not all, pages are expected to be from a Table of Contents (TOC).

    Instructions:
    1.  **Analyze Pages**: Go through each provided page to build the TOC. While all pages are likely part of the TOC, in the rare case a page is not, identify the last valid TOC page.
    2.  **Detect Numbering**: Determine if the main TOC entries are numbered (e.g., "1. Chapter One") or un-numbered. Ignore preliminary un-numbered headings like "Foreword" if the rest of the TOC is numbered.
    3.  **Build JSON**: Construct a JSON object that includes the TOC structure, the numbering flag, and the 0-based index of the last valid TOC page you find.
    4.  **Identify Stop Heading**: After building the TOC, identify the title of the first major heading that appears AFTER the content of the final TOC entry (e.g., 'Appendix', 'References', 'Acknowledgements'). This will be the signal to stop content extraction.
    5.  **Error Handling**: If no valid TOC pages are found, return exactly: "Error : Table of Contents Not Found -1"

    JSON Output Schema:
    Your entire response MUST be a single JSON object with the following keys:
    {
      "toc_tree": <TOC data based on numbering>,
      "is_numbered": <boolean>,
      "last_toc_page": <integer>,
      "stop_heading": "<The first heading after the main content>"
    }

    ---
    ### Example Output for a Numbered TOC:
    {
      "1": {
        "title": "Introduction",
        "content": "",
        "subsections": {
          "1.1": { "title": "Project Background", "content": "", "subsections": {} },
          "1.2": { "title": "Goals and Objectives", "content": "", "subsections": {} }
        }
      },
      "2": {
        "title": "Literature Review",
        "content": "",
        "subsections": {
          "2.1": { "title": "Historical Context", "content": "", "subsections": {} }
        }
      }
    }

    ### Example Output for an Un-numbered TOC:
    [
      {
        "title": "Introduction",
        "content": "",
        "subsections": [
          { "title": "The Problem Statement", "content": "", "subsections": [] },
          { "title": "Our Approach", "content": "", "subsections": [] }
        ]
      },
      {
        "title": "Core Concepts",
        "content": "",
        "subsections": []
      }
    ]
    ---

    General Rules:
    - The "last_toc_page" value must be the 0-based index of the final page identified as part of the TOC.
    - The "content" field in the tree must always be an empty string "".
    - The "stop_heading" should be the full title of the boundary heading. If no such heading exists (i.e., the document ends), return null for this value.
    - Your response must be strictly valid JSON or the exact error string.
    """

    # --- Prompt when use_flag = False ---
    prompt_case_false = """
    You are given the starting pages of a document. Your task is to identify the Table of Contents (TOC) pages and extract their structure.

    Instructions:
    1.  **Identify TOC Pages**: Find all pages that constitute the Table of Contents.
    2.  **Detect Numbering**: Determine if the main TOC entries are numbered (e.g., "1. Chapter One") or un-numbered. Ignore preliminary un-numbered headings like "Foreword" if the rest of the TOC is numbered.
    3.  **Build JSON**: Construct a JSON object that includes the TOC structure, the numbering flag, and the 0-based index of the last page of the TOC.
    4.  **Identify Stop Heading**: After building the TOC, identify the title of the first major heading that appears AFTER the content of the final TOC entry (e.g., 'Appendix', 'References', 'Acknowledgements'). This will be the signal to stop content extraction.
    5.  **Error Handling**: If no TOC pages are found, return exactly: "Error : Table of Contents Not Found -2"

    JSON Output Schema:
    Your entire response MUST be a single JSON object with the following keys:
    {
      "toc_tree": <TOC data based on numbering>,
      "is_numbered": <boolean>,
      "last_toc_page": <integer>,
      "stop_heading": "<The first heading after the main content>"
    }

    ---
    ### Example Output for a Numbered TOC:
    {
      "1": {
        "title": "Introduction",
        "content": "",
        "subsections": {
          "1.1": { "title": "Project Background", "content": "", "subsections": {} },
          "1.2": { "title": "Goals and Objectives", "content": "", "subsections": {} }
        }
      },
      "2": {
        "title": "Literature Review",
        "content": "",
        "subsections": {
          "2.1": { "title": "Historical Context", "content": "", "subsections": {} }
        }
      }
    }

    ### Example Output for an Un-numbered TOC:
    [
      {
        "title": "Introduction",
        "content": "",
        "subsections": [
          { "title": "The Problem Statement", "content": "", "subsections": [] },
          { "title": "Our Approach", "content": "", "subsections": [] }
        ]
      },
      {
        "title": "Core Concepts",
        "content": "",
        "subsections": []
      }
    ]
    ---

    General Rules:
    - The "last_toc_page" value must be the 0-based index of the final page of the TOC.
    - The "content" field in the tree must always be an empty string "".
    - The "stop_heading" should be the full title of the boundary heading. If no such heading exists (i.e., the document ends), return null for this value.
    - Your response must be strictly valid JSON or the exact error string.
    """

    # Select prompt
    prompt = prompt_case_true if use_flag else prompt_case_false

    # Attach PDF from GCS
    pdf_file = Part.from_uri(pdf_gcs_path, mime_type="application/pdf")

    # Call Gemini
    response = model.generate_content(
        [prompt, pdf_file],
        generation_config={"response_mime_type": "application/json"}
    )

    raw_text = response.text.strip()
    
    # --- Default return structure ---
    result = {
        "json": "Error: Processing failed unexpectedly.",
        "is_numbered": False,
        "last_toc_page": -1,
        "stop_heading": None
    }

    # --- Handle explicit error string from LLM ---
    if raw_text.startswith("Error :"):
        result["json"] = raw_text
        return result

    # --- Parse the JSON response ---
    try:
        parsed_json = json.loads(raw_text)

        # Extract all values from the expected JSON structure.
        result["json"] = parsed_json.get("toc_tree", {})
        result["is_numbered"] = parsed_json.get("is_numbered", False)
        result["last_toc_page"] = parsed_json.get("last_toc_page", -1)
        result["stop_heading"] = parsed_json.get("stop_heading") # Returns None if key is missing or value is null

        return result

    except json.JSONDecodeError:
        # Handle cases where the response is not valid JSON
        result["json"] = "Error: Failed to decode JSON from model response."
        print(f"DEBUG: Invalid JSON received: {raw_text}")
        return result