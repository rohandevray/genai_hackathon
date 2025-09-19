import re
import json
import io
import os
import fitz  # PyMuPDF, install with: pip install PyMuPDF
from collections import Counter
from google.cloud import storage # Install with: pip install google-cloud-storage4
import vertexai
from vertexai.generative_models import GenerativeModel
vertexai.init(
    project="big-depth-471018-r6",
location="us-central1"
)

def _is_conclusive_heading_llm(line_text: str) -> bool:
    """Uses an LLM to determine if a line is a conclusive heading."""
    try:
        model = GenerativeModel("gemini-2.5-pro")
        prompt = f"""
        Analyze the following line of text from a document:
        Line: "{line_text}"

        Is this line a standalone heading for a final, conclusive section of a document (like an appendix, bibliography, or index), or is it more likely a regular sentence that happens to contain a conclusive word?

        Respond with only "true" if it is a heading, and "false" if it is not.
        """
        response = model.generate_content(prompt)
        # Normalize the LLM's response to a boolean
        return response.text.strip().lower() == "true"
    except Exception as e:
        print(f"LLM verification call failed: {e}")
        return False # Fail safely, assume it's not a heading on error

def _get_pdf_document_from_gcs(pdf_gcs_path: str) -> fitz.Document | None:
    """Downloads a PDF from GCS and returns it as a PyMuPDF Document object."""
    try:
        bucket_name, blob_name = pdf_gcs_path.replace("gs://", "").split("/", 1)
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or "big-depth-471018-r6"
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        pdf_bytes = blob.download_as_bytes()
        return fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        print(f"Error processing PDF from GCS: {e}")
        return None

def _detect_headers_and_footers(document: fitz.Document, start_page: int) -> set[str]:
    """Detects repeated lines in the top/bottom margins of the first few content pages."""
    line_counts = Counter()
    # Scan the first 5 pages of the main content area
    num_pages_to_scan = min(5, document.page_count - start_page)
    if num_pages_to_scan <= 1:
        return set()

    for page_num in range(start_page, start_page + num_pages_to_scan):
        page = document.load_page(page_num)
        lines = [line.strip() for line in page.get_text("text").split('\n') if line.strip()]
        
        if len(lines) > 6: # Ensure page has enough content to have distinct headers/footers
            # Get top and bottom 3 lines
            header_candidates = lines[:3]
            footer_candidates = lines[-3:]
            
            for line in header_candidates + footer_candidates:
                line_counts[line] += 1
    
    # A line is a header/footer if it's repeated on more than one scanned page
    headers_footers = {line for line, count in line_counts.items() if count > 1}
    print(f"Detected headers/footers: {headers_footers}")
    return headers_footers


def _flatten_toc_recursive(toc_data: dict, flat_list: list):
    """Recursively flattens the nested TOC dictionary into a list."""
    for heading, details in toc_data.items():
        flat_list.append({"number": heading, "title": details["title"], "node": details})
        if "subsections" in details and details["subsections"]:
            _flatten_toc_recursive(details["subsections"], flat_list)

def populate_content(toc_json: dict, pdf_gcs_path: str, start_page: int, stop_heading: str, is_numbered: bool) -> dict:
    """Populates the 'content' field for each entry in a numbered TOC JSON using robust heading detection."""
    if not is_numbered:
        print("Content population is only supported for numbered TOCs.")
        return toc_json

    ordered_toc = []
    _flatten_toc_recursive(toc_json, ordered_toc)
    if not ordered_toc:
        return toc_json

    document = _get_pdf_document_from_gcs(pdf_gcs_path)
    if not document:
        return toc_json

    # Detect headers and footers before processing content
    headers_footers = _detect_headers_and_footers(document, start_page)

    # Extract all text lines from the relevant pages
    document_lines = []
    # print(document.page_count)
    if start_page < document.page_count:
        for page_num in range(start_page, document.page_count):
            page = document.load_page(page_num)
            document_lines.extend(page.get_text("text").split('\n'))

    doc_lines_count = len(document_lines)
    line_idx = 0
    
    CONCLUSIVE_KEYWORDS = ['appendix', 'conclusion', 'references', 'bibliography', 'index', 'annex', 'glossary', 'acknowledgements']

    def _verify_heading(start_idx: int, heading_num: str, heading_title: str) -> tuple[bool, int]:
        """Verifies if a heading exists at a given index using iterative title aggregation."""
        if start_idx >= doc_lines_count:
            return (False, -1)
        
        line = document_lines[start_idx]

        if not line.strip().lower().startswith(heading_num.lower()):
            return (False, -1)
        
        normalized_title = "".join(heading_title.lower().split())
        aggregated_title_lines = []
        last_line_idx = start_idx
        
        for i in range(4): # Look ahead up to 4 lines
            current_idx = start_idx + i
            if current_idx >= doc_lines_count:
                break
            line_text = document_lines[current_idx].strip()
            if i == 0 and line_text.lower() == heading_num.lower():
                pass
            elif i == 0:
                text_part = re.sub(r'^\s*' + re.escape(heading_num) + r'\s*[:.]?\s*', '', line_text, flags=re.IGNORECASE)
                aggregated_title_lines.append(text_part)
            else:
                if not line_text:
                    continue
                aggregated_title_lines.append(line_text)

            last_line_idx = current_idx
            built_title_str = "".join(" ".join(aggregated_title_lines).lower().split())

            if normalized_title in built_title_str:
                return (True, last_line_idx + 1)
        
        return (False, -1)

    def _check_stop_heading(start_idx: int) -> bool:
        """Checks for the stop heading using iterative, multi-line matching."""
        if not stop_heading:
            return False
        
        normalized_stop_title = "".join(stop_heading.lower().split())
        aggregated_lines = []
        for i in range(3): # Look ahead up to 3 lines
            current_idx = start_idx + i
            if current_idx >= doc_lines_count:
                break
            
            line_text = document_lines[current_idx].strip()
            if line_text:
                aggregated_lines.append(line_text)
            
            built_str = "".join(" ".join(aggregated_lines).lower().split())
            if normalized_stop_title in built_str:
                return True
        return False

    # Iterate through each section in the flattened TOC list
    for i, current_section in enumerate(ordered_toc):
        found_heading = False
        # print(doc_lines_count)
        while line_idx < doc_lines_count:
            # print(current_section["number"],current_section["title"])
            is_match, content_start_idx = _verify_heading(line_idx, current_section["number"], current_section["title"])
            # print(is_match)
            if is_match:
                # print("Yes")
                found_heading = True
                line_idx = content_start_idx
                break
            line_idx += 1
        
        if not found_heading:
            continue

        content_lines = []
        next_section = ordered_toc[i + 1] if i + 1 < len(ordered_toc) else None
        
        while line_idx < doc_lines_count:
            stop = False
            current_line_text = document_lines[line_idx]

            if next_section:
                is_next_match, _ = _verify_heading(line_idx, next_section["number"], next_section["title"])
                if is_next_match:
                    stop = True
            else: # This is the last section, use primary and fallback stop logic
                if _check_stop_heading(line_idx):
                    stop = True
                else:
                    normalized_line = current_line_text.strip().lower()
                    if normalized_line:
                        for keyword in CONCLUSIVE_KEYWORDS:
                            if keyword in normalized_line:
                                if _is_conclusive_heading_llm(current_line_text):
                                    stop = True
                                    break # Exit keyword loop
            if stop:
                break
            
            # Filter out headers and footers before appending
            if current_line_text.strip() not in headers_footers:
                content_lines.append(current_line_text)
            
            line_idx += 1
            
        current_section["node"]["content"] = "\n".join(content_lines).strip()

    return toc_json









