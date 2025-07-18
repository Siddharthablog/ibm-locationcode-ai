from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import re

app = FastAPI()

class TextInput(BaseModel):
    text: str

class Match(BaseModel):
    part_name: str
    location_code: str

class Output(BaseModel):
    original_text: str
    matches: List[Match]

@app.post("/find-location", response_model=Output)
async def find_location(input_text: TextInput):
    text = input_text.text.strip()
    matches = extract_part_locations(text)
    return {"original_text": text, "matches": matches}

def extract_part_locations(text: str) -> List[Match]:
    """
    Pair adjacent lines where a part name is followed by a physical location code (e.g., Un-A1).
    Handles broken tables in PDF where part and location appear on separate lines.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    results = []

    i = 0
    while i < len(lines) - 1:
        part = lines[i]
        next_line = lines[i + 1]

        if re.match(r"^Un-[A-Z0-9\-]+$", next_line):
            results.append(Match(part_name=part, location_code=next_line))
            i += 2  # move past the location line
        else:
            i += 1  # move to next line

    return results
