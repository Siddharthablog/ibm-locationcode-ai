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
    locations: Optional[List[PartLocation]]
    answer: str

MTM_TABLE_HEADERS = {
    "9824-22a": "Table 3. FRU location",
    "9824-42a": "Table 4. FRU location",
    "9043-mru": "Table 5. FRU location",
    # More models if needed
}

def parse_query_for_list_all(query):
    # Detect if the user is asking for "list all location codes" for a model.
    match = re.search(r'\blist (?:all )?location codes?.*mtm\s*(\d{4}-[0-9a-zA-Z]+)', query, re.I)
    if match:
        return match.group(1).strip().lower()
    # Also allow: "Give me all location codes for 9043-MRU"
    match = re.search(r'(?:all )?location codes.*(?:for )?(?:mtm\s*)?(\d{4}-[0-9a-zA-Z]+)', query, re.I)
    if match:
        return match.group(1).strip().lower()
    return None

def extract_fru_table(text, table_header):
    lines = text.splitlines()
    in_table = False
    table_lines = []
    for i, line in enumerate(lines):
        if table_header in line:
            in_table = True
            continue
        if in_table:
            # End at a new "Table X." line, next chapter, or blank section
            if (line.strip().startswith("Table ") and table_header not in line) or (
                line.strip().startswith("Finding parts, locations")
            ):
                break
            if line.strip():
                table_lines.append(line)
    return table_lines

def extract_part_locations_from_lines(lines):
    # Look for lines with: part name, then location code, with / without other columns
    results = []
    for line in lines:
        # Expect two columns minimum: failing item name, physical location code
        cols = re.split(r'\s{2,}|\t', line.strip())
        if len(cols) >= 2:
            part = cols[0].strip()
            code = cols[1].strip()
            # Only accept reasonable location codes (start with Un-)
            if re.match(r"Un-[A-Z0-9\-]+", code):
                results.append(PartLocation(part=part, code=code))
    return results

@app.post("/find-location", response_model=Output)
async def find_location(input_data: QueryInput):
    text = input_data.text
    query = input_data.query

    # 1. List all location codes for a model
    mtm = parse_query_for_list_all(query)
    if mtm:
        table_header = MTM_TABLE_HEADERS.get(mtm)
        if not table_header:
            return {"original_query": query, "locations": None, "answer": f"Model {mtm.upper()} not supported."}
        table_lines = extract_fru_table(text, table_header)
        if not table_lines:
            return {"original_query": query, "locations": None, "answer": f"No FRU location table found for {mtm.upper()}."}
        locations = extract_part_locations_from_lines(table_lines)
        if locations:
            answer = "Here are all location codes for MTM " + mtm.upper() + ":\n"
            for loc in locations:
                answer += f"- {loc.part}: {loc.code}\n"
            return {"original_query": query, "locations": locations, "answer": answer.strip()}
        else:
            return {"original_query": query, "locations": None, "answer": f"No location codes found in the {mtm.upper()} table."}

    return {"original_query": query, "locations": None, "answer": "Please specify a valid query, e.g. 'List all location codes of the MTM 9043-MRU'."}
