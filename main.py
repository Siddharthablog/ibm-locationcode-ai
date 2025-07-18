from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import re

app = FastAPI()

class QueryInput(BaseModel):
    text: str               # Raw extracted PDF text
    query: str              # User's question, e.g. "What is the location code for Fan 1 in MTM 9824-22A?"

class QAEntry(BaseModel):
    part: str
    code: str

class Output(BaseModel):
    original_query: str
    match: Optional[QAEntry]
    answer: str

# Map Model to Table headers for extraction
MTM_TABLE_HEADERS = {
    "9824-22a": "Table 3. FRU location",
    "9824-42a": "Table 4. FRU location",
    "9043-mru": "Table 5. FRU location",
    # Add other MTM:table pairs for your supported hardware here
}

def parse_query(query: str):
    """Extract mtm & part name from natural query string."""
    mtm = None
    part = None
    mtm_match = re.search(r"(?:MTM\s*)?(\d{4}-[0-9a-zA-Z]+)", query, re.I)
    if mtm_match:
        mtm = mtm_match.group(1).strip().lower()
    # Example: "Fan 0", "Power supply 2", "Memory module 5", etc — tune this regex for your needs
    part_match = re.search(r"(Fan \d+|Power supply \d+|NVMe U\.2 drive \d+|Memory module \d+|System backplane|Drive backplane \d+|eBMC card|Control panel display|Trusted platform module card)", query, re.I)
    if part_match:
        part = part_match.group(0).strip()
    return mtm, part

def extract_table(text: str, header: str):
    """Given raw PDF text and a table header, extract the relevant FRU location table."""
    lines = text.splitlines()
    in_table = False
    table_lines = []
    for i, line in enumerate(lines):
        if header in line:
            in_table = True
            continue
        if in_table:
            # End when another Table or chapter starts
            if (line.strip().startswith("Table ") and header not in line) or re.match(r'^\s*[A-Z]', line) and len(line.strip().split()) < 6:
                break
            if line.strip() != "":
                table_lines.append(line)
    return table_lines

def find_part_code(table_lines: List[str], part: str):
    """Search for the part in the table and return its code."""
    for line in table_lines:
        # Split by multiple spaces or tabs
        cols = re.split(r'\s{2,}|\t', line.strip())
        if len(cols) >= 2:
            part_name = cols[0].strip().lower().replace('\u200b', '')
            code = cols[1].strip()
            # Fuzzy match: ignore case/extra whitespace
            if part_name.startswith(part.lower()):
                return part_name, code
    return None, None

@app.post("/find-location", response_model=Output)
async def find_location(input_data: QueryInput):
    text = input_data.text
    query = input_data.query

    mtm, part = parse_query(query)

    if not mtm or not part:
        return {
            "original_query": query,
            "match": None,
            "answer": "Could not extract model (MTM) and part name from your query. Please specify a valid question, e.g. 'What is the location code for Fan 1 in MTM 9824-22A?'"
        }

    table_header = MTM_TABLE_HEADERS.get(mtm)
    if not table_header:
        return {
            "original_query": query,
            "match": None,
            "answer": f"Model {mtm.upper()} not supported or not found in tool's mapping."
        }

    table_lines = extract_table(text, table_header)
    if not table_lines:
        return {
            "original_query": query,
            "match": None,
            "answer": f"Could not locate the FRU table for model {mtm.upper()} in the provided document."
        }

    part_name, code = find_part_code(table_lines, part)
    if code:
        return {
            "original_query": query,
            "match": {"part": part_name, "code": code},
            "answer": f"{part} location code is {code}"
        }
    else:
        return {
            "original_query": query,
            "match": None,
            "answer": f"Location code not found for '{part}' in MTM {mtm.upper()}."
        }
