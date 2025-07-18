from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import re

app = FastAPI()

class LocationInput(BaseModel):
    text: str
    query: Optional[str] = None  # optional search term

class Match(BaseModel):
    part_name: str
    location_code: str

class Output(BaseModel):
    original_text: str
    matches: List[Match]

@app.post("/find-location", response_model=Output)
async def find_location(input_text: LocationInput):
    text = input_text.text.strip()
    all_matches = extract_part_locations(text)

    # If query is provided, filter results
    if input_text.query:
        query_lower = input_text.query.lower()
        filtered = [
            match for match in all_matches
            if query_lower in match.part_name.lower() or query_lower in match.location_code.lower()
        ]
        return {"original_text": text, "matches": filtered}

    # Otherwise return all matches
    return {"original_text": text, "matches": all_matches}

def extract_part_locations(text: str) -> List[Match]:
    """
    Extract part-location pairs from text where the format is:
    Line 1: part name
    Line 2: location code (e.g., Un-A1)
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    results = []

    i = 0
    while i < len(lines) - 1:
        part = lines[i]
        next_line = lines[i + 1]

        if re.match(r"^Un-[A-Z0-9\-]+$", next_line):
            results.append(Match(part_name=part, location_code=next_line))
            i += 2
        else:
            i += 1

    return results
