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
    # Extract part-location pairs from the text
    part_location_map = extract_part_locations(data.text)

    matches = []

    if data.query:
        query_lower = data.query.lower()
        for part, code in part_location_map.items():
            if query_lower in part:
                matches.append({"part_name": part, "location_code": code})
    else:
        for part, code in part_location_map.items():
            matches.append({"part_name": part, "location_code": code})

    return {"matches": matches}

def extract_part_locations(text: str) -> dict:
    """
    Extract part names and physical location codes from table-like text.
    Returns a dictionary: { "fan 1": "Un-A1", ... }
    """
    pattern = r"([A-Za-z0-9()\- ,./]+?)\s+(Un-[A-Z0-9\-]+)"
    matches = re.findall(pattern, text)

    part_location_map = {}
    for part, code in matches:
        normalized_part = part.strip().lower()
        part_location_map[normalized_part] = code.strip()

    return part_location_map
