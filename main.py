from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import re

app = FastAPI()

class LocationInput(BaseModel):
    text: str
    query: Optional[str] = None

class LocationMatch(BaseModel):
    part_name: str
    location_code: str

class LocationOutput(BaseModel):
    matches: List[LocationMatch]

@app.post("/find-location", response_model=LocationOutput)
async def find_location(data: LocationInput):
    part_location_map = extract_part_locations(data.text)
    matches = []

    if data.query:
        query_lower = data.query.lower()
        for part, code in part_location_map.items():
            if query_lower in part or query_lower in code.lower():
                matches.append({"part_name": part, "location_code": code})
    else:
        for part, code in part_location_map.items():
            matches.append({"part_name": part, "location_code": code})

    return {"matches": matches}

def extract_part_locations(text: str) -> dict:
    """
    Improved logic: Pair lines where a part name is followed by a location code.
    Handles PDF table layout where lines are broken.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    part_location_map = {}

    i = 0
    while i < len(lines) - 1:
        part = lines[i]
        next_line = lines[i + 1]

        if re.match(r"^Un-[A-Z0-9\-]+$", next_line):
            normalized_part = part.lower()
            part_location_map[normalized_part] = next_line
            i += 2  # Skip next line as it's already used
        else:
            i += 1

    return part_location_map
