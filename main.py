from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import re

app = FastAPI()

class TextInput(BaseModel):
    text: str
    query: Optional[str] = None  # support filtering

class PartLocation(BaseModel):
    part_name: str
    location_code: str

class Output(BaseModel):
    query: Optional[str]
    matches: List[PartLocation]

@app.post("/find-parts", response_model=Output)
async def find_parts(input_text: TextInput):
    text = input_text.text.strip()
    query = input_text.query.strip().lower() if input_text.query else None
    parts = []

    # Basic pattern to extract part name and location
    pattern = re.compile(
        r"(?P<name>[A-Z][^\n\r]{1,100}?)\s+(?P<location>Un(?:-[A-Z0-9]+)+)",
        re.MULTILINE
    )

    for match in pattern.finditer(text):
        name = match.group("name").strip()
        code = match.group("location").strip()

        if query:
            if query in name.lower() or query in code.lower():
                parts.append(PartLocation(part_name=name, location_code=code))
        else:
            parts.append(PartLocation(part_name=name, location_code=code))

    return {
        "query": query,
        "matches": parts
    }
