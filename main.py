from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import re

app = FastAPI()

class TextInput(BaseModel):
    text: str

class PartLocation(BaseModel):
    part_name: str
    location_code: str

class Output(BaseModel):
    original_text: str
    parts: List[PartLocation]

@app.post("/find-parts", response_model=Output)
async def find_parts(input_text: TextInput):
    text = input_text.text.strip()
    parts = []

    # A simple, flexible regex to find: part name [some gap] location code
    pattern = re.compile(
        r"(?P<name>[A-Z].*?)\s+(?P<location>Un(?:-[A-Z0-9]+)+)",
        re.MULTILINE
    )

    for match in pattern.finditer(text):
        name = match.group("name").strip()
        code = match.group("location").strip()

        # Optional: filter out rows that look like noise
        if len(code) < 20 and len(name) < 100:
            parts.append(PartLocation(part_name=name, location_code=code))

    return {
        "original_text": text,
        "parts": parts
    }
