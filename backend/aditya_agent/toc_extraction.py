import fitz  # PyMuPDF
import re
from io import BytesIO
from pathlib import PurePosixPath
from google.cloud import storage


def get_unique_blob_name(bucket, dest_blob):
    """Return a unique blob name by appending '_copy' if needed."""
    blob = bucket.blob(dest_blob)

    if not blob.exists():
        return dest_blob, blob

    # Split into folder + filename + extension
    path = PurePosixPath(dest_blob)
    folder = "" if str(path.parent) == "." else str(path.parent)
    stem = path.stem
    suffix = path.suffix or ".pdf"

    counter = 1
    new_name = f"{stem}_copy{suffix}"
    candidate = f"{folder}/{new_name}" if folder else new_name
    blob = bucket.blob(candidate)

    # Keep incrementing until a free name is found
    while blob.exists():
        counter += 1
        new_name = f"{stem}_copy{counter}{suffix}"
        candidate = f"{folder}/{new_name}" if folder else new_name
        blob = bucket.blob(candidate)

    return candidate, blob


def extract_toc_pdf(
    source_bucket: str,
    source_blob: str,
    dest_bucket: str,
    dest_blob: str,
    fallback_pages: int = 10,
    min_matches_first_page: int = 5,
    min_matches_next_page: int = 1,
    overwrite: bool = False,
    project_id: str | None = None,
    verbose: bool = False
) -> dict:
    """
    Extract ToC (or fallback) pages from a PDF in GCS, save the new PDF
    to the specified destination bucket and blob path, and return metadata.

    Returns:
        dict with bucket, blob_path, gs_uri, public_url, and from_toc.
    """

    # --- Init GCS client ---
    client = storage.Client(project=project_id)
    src_bucket = client.bucket(source_bucket)
    dst_bucket = client.bucket(dest_bucket)

    # --- Download source PDF into memory ---
    if verbose:
        print(f"Downloading gs://{source_bucket}/{source_blob} into memory...")
    pdf_bytes = src_bucket.blob(source_blob).download_as_bytes()
    doc = fitz.open("pdf", pdf_bytes)

    # --- TOC detection logic ---
    def find_toc_pages(doc) -> list[int]:
        keywords = [
            "contents", "table of contents", "index",
            "list of contents", "detailed contents",
            "content page", "summary of contents"
        ]
        patterns = [
            re.compile(r'^\s*\d+(\.\d+)*\s+.+\.{2,}\s*\d+\s*$'),
            re.compile(r'^\s*\d+(\.\d+)*\s+.+\.{2,}\d+\s*$'),
            re.compile(r'^\s*\d+(\.\d+)*\s+.+\s*\.{2,}\s*\d+\s*$'),
            re.compile(r'^\s*\d+(\.\d+)*\s+.+\s\d+\s*$'),
            re.compile(r'^\s*\d+(\.\d+)*\s+.+\s{2,}\d+\s*$'),
            re.compile(r'^\s*\d+(\.\d+)*\s+.+(?:\.\s*)+\d+\s*$'),
            re.compile(r'^\s*[A-Za-z].+\s*\.{2,}\s*[a-zA-Z0-9]+\s*$'),
            re.compile(r'^\s*\d+(\.\d+)*\s+.+\.{2,}\s*[ivxlcdmIVXLCDM]+\s*$'),
            re.compile(r'^\s*\d+(\.\d+)*\s+.+\s*\(\s*\d+\s*\)\s*$'),
            re.compile(r'^\s*\d+(\.\d+)*\s+.+\.{2,}\s*\d+(?:[-–]\d+)\s*$'),
            re.compile(r'^\s*[•\-\*]\s*.+\.{2,}\s*\d+\s*$'),
            re.compile(r'^\s*[A-Z]\.\s+.+\.{2,}\s*\d+\s*$'),
            re.compile(r'^\s*[A-Za-z].+\s{2,}\d+\s*$'),
        ]

        toc_page_numbers = []
        first_found = False

        for page_num in range(doc.page_count):
            text = doc[page_num].get_text(sort=True)
            lines = text.strip().split("\n")
            matches = sum(1 for line in lines if any(p.search(line) for p in patterns))

            if not first_found:
                if any(kw in text.lower() for kw in keywords) and matches >= min_matches_first_page:
                    first_found = True
                    toc_page_numbers.append(page_num + 1)
            else:
                if matches >= min_matches_next_page:
                    toc_page_numbers.append(page_num + 1)
                else:
                    break
        return toc_page_numbers

    # --- Find pages ---
    toc_pages=[]
    toc_pages = find_toc_pages(doc)
    if toc_pages:
        pages_to_extract = [p - 1 for p in toc_pages]  # convert to 0-based
        from_toc = True
        toc_pages = pages_to_extract
    else:
        pages_to_extract = list(range(min(fallback_pages, doc.page_count)))
        from_toc = False
    if verbose:
        print(f"Extracting pages: {pages_to_extract}")

    # --- Build new PDF in memory ---
    new_doc = fitz.open()
    for p in pages_to_extract:
        new_doc.insert_pdf(doc, from_page=p, to_page=p)
    output_buffer = BytesIO()
    new_doc.save(output_buffer)
    new_doc.close()
    doc.close()
    output_buffer.seek(0)

    # --- Handle existing destination file ---
    blob = dst_bucket.blob(dest_blob)
    if blob.exists() and not overwrite:
        dest_blob, blob = get_unique_blob_name(dst_bucket, dest_blob)
        print(f"File already exists. Saving instead as: gs://{dest_bucket}/{dest_blob}")

    # --- Upload to destination ---
    if verbose:
        print(f"Uploading extracted PDF to gs://{dest_bucket}/{dest_blob}")
    blob.upload_from_file(output_buffer, content_type="application/pdf")

    return {
        "bucket": dest_bucket,
        "blob_path": dest_blob,
        "gs_uri": f"gs://{dest_bucket}/{dest_blob}",
        "public_url": f"https://storage.googleapis.com/{dest_bucket}/{dest_blob}",
        "from_toc": from_toc,
        "toc_pages":toc_pages
    }

