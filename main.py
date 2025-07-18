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

MTM_SECTIONS = {
    "9824-22a": r"9824-22A or 9856-22H locations",
    "9824-42a": r"9824-42A or 9856-42H locations",
    "9043-mru": r"9043-MRU locations",
    "9080-heu": r"9080-HEU locations"
}

def parse_mtm(query):
    match = re.search(r"(9\d{3}-[0-9A-Za-z]{3})", query, re.I)
    return match.group(1).lower() if match else None

def parse_part(query):
    # Good for a wide variety (Fan 1, Power supply 2, NVMe U.2 drive 3, etc)
    match = re.search(
        r'(Fan \d+|Power supply \d+|Memory module \d+|NVMe U\.2 drive \d+|System backplane|Drive backplane \d+|eBMC card( assembly)?|Control panel display|Trusted platform module card|Processor( module)? \d+|Voltage regulator module( for .*?)?|Control panel|Time-of-day battery)', 
        query, re.I)
    if match:
        return match.group(0).strip()
    return None

def is_list_all_query(query):
    return bool(re.search(r'\b(list|all|show|every|display)\b.*location codes?', query, re.I))

def extract_fru_table_lines(text, mtm):
    """Find and return all lines in the FRU table for the given MTM."""
    section_title = MTM_SECTIONS.get(mtm, "")
    lines = text.splitlines()
    start_idx = -1
    # 1. Find start of correct section
    for idx, line in enumerate(lines):
        if re.search(section_title, line, re.I):
            start_idx = idx
            break
    if start_idx == -1:
        return None
    # 2. Find next "Table X. FRU location"
    table_idx = -1
    for idx in range(start_idx, len(lines)):
        if re.match(r"Table\s+\d+\.\s*FRU location", lines[idx], re.I):
            table_idx = idx
            break
    if table_idx == -1:
        return None
    # 3. Accumulate lines until the next table/section or many blanks
    table_lines = []
    for line in lines[table_idx + 1:]:
        if re.match(r"^Table\s+\d+\.", line):  # next table
            break
        if re.match(r".+\slocations?", line) and not re.match(section_title, line, re.I):
            break
        if not line.strip():
            if table_lines and table_lines[-1] == "":
                break  # two blanks = end
            table_lines.append("")
        else:
            table_lines.append(line)
    return table_lines

def extract_part_locations_from_lines(lines):
    """Parse table lines for (part, code) pairs using FRU table rules."""
    results = []
    for line in lines:
        # At least two columns, split by 2+ spaces or tab. Ignore lines that aren't fru rows.
        if not line.strip(): continue
        cols = re.split(r'\s{2,}|\t', line.strip())
        if len(cols) < 2: continue
        part, code = cols[0].strip(), cols[1].strip()
        if re.match(r"Un-[A-Z0-9\-]+", code):
            results.append(PartLocation(part=part, code=code))
    return results

@app.post("/find-location", response_model=Output)
async def find_location(input_data: QueryInput):
    text, query = input_data.text, input_data.query
    mtm = parse_mtm(query)

    if not mtm or mtm not in MTM_SECTIONS:
        return Output(
            original_query=query,
            answer=f"Could not recognize requested MTM/model in your query. Please specify a query such as 'What is the location code for Fan 1 in MTM 9824-22A?' or 'List all location codes of the MTM 9043-MRU'."
        )
    fru_table_lines = extract_fru_table_lines(text, mtm)
    if not fru_table_lines:
        return Output(
            original_query=query,
            answer=f"Could not find the FRU location table for model {mtm.upper()} in the provided text."
        )

    # "List all" location codes for this MTM
    if is_list_all_query(query):
        fru_rows = extract_part_locations_from_lines(fru_table_lines)
        if not fru_rows:
            return Output(
                original_query=query,
                answer=f"No location codes found in the FRU table for {mtm.upper()}."
            )
        nl = "\n"
        answer = f"Here are all location codes for MTM {mtm.upper()}:{nl}" + nl.join(f"- {loc.part}: {loc.code}" for loc in fru_rows)
        return Output(
            original_query=query,
            locations=fru_rows,
            answer=answer
        )

    # Specific part query
    part = parse_part(query)
    if part:
        fru_rows = extract_part_locations_from_lines(fru_table_lines)
        for loc in fru_rows:
            # Fuzzy: exact match OR part is substring, ignoring case and whitespace
            qnorm = re.sub(r'\s+', '', part).lower()
            lnorm = re.sub(r'\s+', '', loc.part).lower()
            if qnorm == lnorm or qnorm in lnorm or lnorm in qnorm:
                return Output(
                    original_query=query,
                    locations=[loc],
                    answer=f"{loc.part} location code is {loc.code}"
                )
        return Output(
            original_query=query,
            answer=f"Location code not found for '{part}' in MTM {mtm.upper()}."
        )

    return Output(
        original_query=query,
        answer="Could not extract part name from your query."
    )
