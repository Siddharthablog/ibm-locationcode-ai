from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import re

app = FastAPI()

class LocationInput(BaseModel):
    text: str
    query: Optional[str] = None

class Answer(BaseModel):
    answer: str

# Define mapping from pdf for direct queries
MTM_FAN_LOCATION = {
    ("9824-22a", "fan 0"): "Un-A0",
    ("9824-42a", "fan 0"): "Un-A0",
    # Add more mappings as needed
}

def parse_mtm_and_part(query: str) -> Optional[tuple]:
    """
    Extract MTM and part info from user query using regex.
    Accepts queries like "In MTM 9824-22A, what is location code of Fan 0?"
    Returns lower-case mtm and part, or None.
    """
    mtm_match = re.search(r"mtm\s*(\d{4}-\d{2}[a-zA-Z])", query, re.I)
    part_match = re.search(r"fan\s*\d+", query, re.I) # Only for 'Fan X'; add more as needed
    if mtm_match and part_match:
        mtm = mtm_match.group(1).strip().lower()
        part = part_match.group(0).strip().lower()
        return (mtm, part)
    return None

@app.post("/find-location", response_model=Answer)
async def find_location(input_text: LocationInput):
    # Use the query field, or fallback to a default prompt
    query = input_text.query or ""
    mtm_part = parse_mtm_and_part(query)
    if mtm_part and mtm_part in MTM_FAN_LOCATION:
        location = MTM_FAN_LOCATION[mtm_part]
        return {"answer": f"Fan 0 location code is {location}"}
    
    # fallback: scan text for pattern
    lines = [line.strip() for line in input_text.text.splitlines() if line.strip()]
    last_fan_line = ""
    for idx, line in enumerate(lines):
        # Look for "Fan 0" in the text, then check next line for location code
        if re.fullmatch(r"Fan 0", line, re.I) and idx + 1 < len(lines):
            next_line = lines[idx + 1]
            if re.match(r"Un-[A-Z0-9\-]+", next_line):
                last_fan_line = next_line
                break

    if last_fan_line:
        return {"answer": f"Fan 0 location code is {last_fan_line}"}
    else:
        return {"answer": "Location not found for your query."}
