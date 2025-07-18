from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import re

app = FastAPI()

class QueryInput(BaseModel):
    text: str
    query: str

class PartLocation(BaseModel):
    part: str
    code: str

class Output(BaseModel):
    original_query: str
    locations: Optional[List[PartLocation]] = None
    answer: str

# Table keywords for known MTMs. Header detection is fuzzy for resilience.
MTM_TABLE_HEADERS = {
    "9824-22a": "FRU location",
    "9824-42a": "FRU location",
    "9043-mru": "FRU location",
    "9080-heu": "FRU location"
}

def parse_mtm(query: str) -> Optional[str]:
    match = re.search(r'(?:MTM\s*)?(\d{4}-[0-9a-zA-Z]+)', query, re.I)
    return match.group(1).strip().lower() if match else None

def parse_part(query: str) -> Optional[str]:
    # Match "Fan 1", "Power supply 0", "Memory module 17", etc.
    match = re.search(
        r'(Fan \d+|Power supply \d+|Memory module \d+|NVMe U\.2 drive \d+|System backplane|Drive backplane|eBMC card|Control panel display|Trusted platform module card|Time-of-day battery|Processor|Voltage regulator)', 
        query, re.I)
    if match:
        return match.group(0).strip()
    return None

def is_list_all_query(query: str) -> Optional[str]:
    # Detect various forms of "list all location codes of the MTM <model>"
    match = re.search(r'\b(?:list|show|all)\b.*location codes?.*(?:mtm\s*)?(\d{4}-[0-9a-zA-Z]+)', query, re.I)
    if match:
        return match.group(1).strip().lower()
    return None

def find_fru_table_lines(pdf_text: str, mtm: str) -> List[str]:
    # Find the right "Table X. FRU location" section for the MTM
    section_titles = {
        "9824-22a": r"9824-22A.*locations",
        "9824-42a": r"9824-42A.*locations",
        "9043-mru": r"9043-MRU.*locations",
        "9080-heu": r"9080-HEU.*locations"
    }
    target_section = section_titles.get(mtm)
    if not target_section:
        return []

    # Find start of target section
    lines = pdf_text.splitlines()
    section_start_idx = -1
    for idx, line in enumerate(lines):
        if re.search(target_section, line, re.I):
            section_start_idx = idx
            break
    if section_start_idx == -1:
        return []

    # Find the "FRU location" table in this section
    table_start = -1
    for i in range(section_start_idx, len(lines)):
        if re.search(r'Table.*FRU location', lines[i], re.I):
            table_start = i+1
            break
    if table_start == -1:
        return []

    # Table runs until a blank line more than 2x in a row or Table <n>. again or a new section
    table_lines = []
    blank_lines = 0
    for line in lines[table_start:]:
        if re.match(r'\s*Table.*FRU location', line):
            break
        if line.strip() == "":
            blank_lines += 1
            if blank_lines >= 2:
                break
            continue
        blank_lines = 0
        table_lines.append(line)
    return table_lines

def extract_part_locations_from_lines(lines: List[str]) -> List[PartLocation]:
    results = []
    for line in lines:
        # Split by 2+ spaces or tab
        cols = re.split(r'\s{2,}|\t', line.strip())
        if len(cols) >= 2:
            part = cols[0].strip()
            code = cols[1].strip()
            if re.match(r"Un-[A-Z0-9\-]+", code):
                results.append(PartLocation(part=part, code=code))
    return results

@app.post("/find-location", response_model=Output)
async def find_location(input_data: QueryInput):
    text, query = input_data.text, input_data.query

    # LIST ALL location codes for a given MTM
    mtm_list = is_list_all_query(query)
    if mtm_list:
        table_lines = find_fru_table_lines(text, mtm_list)
        if not table_lines:
            return {
                "original_query": query,
                "locations": None,
                "answer": f"No FRU location table found for {mtm_list.upper()}."
            }
        locations = extract_part_locations_from_lines(table_lines)
        if not locations:
            return {
                "original_query": query,
                "locations": None,
                "answer": f"No parts found in the FRU table for {mtm_list.upper()}."
            }
        answer = f"Here are all location codes for MTM {mtm_list.upper()}:\n"
        for loc in locations:
            answer += f"- {loc.part}: {loc.code}\n"
        return {
            "original_query": query,
            "locations": locations,
            "answer": answer.strip()
        }

    # SINGLE PART lookup: e.g. "What is the location code for Fan 1 in MTM 9824-22A?"
    mtm = parse_mtm(query)
    part = parse_part(query)
    if mtm and part:
        table_lines = find_fru_table_lines(text, mtm)
        locations = extract_part_locations_from_lines(table_lines)
        for loc in locations:
            # Fuzzy match: ignore case, allow partial
            if part.lower() == loc.part.lower():
                return {
                    "original_query": query,
                    "locations": [loc],
                    "answer": f"{part} location code is {loc.code}"
                }
        return {
            "original_query": query,
            "locations": None,
            "answer": f"Location code not found for '{part}' in MTM {mtm.upper()}."
        }

    return {
        "original_query": query,
        "locations": None,
        "answer": "Could not extract model (MTM) and part name from your query. For all codes: 'List all location codes of the MTM 9043-MRU'. For a single part: 'What is the location code for Fan 1 in MTM 9824-22A?'."
    }
