from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()
sequence = [0] * 8  # Internal list of ints with length 8
description = '' 

class SequenceInput(BaseModel):
    values: List[int]

class DescriptionInput(BaseModel):
    value: str

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

@app.post("/update_sequence")
def update_sequence(input_data: SequenceInput):
    global sequence
    if len(input_data.values) == 8:
        sequence = input_data.values
        return {"message": "Sequence updated", "sequence": sequence}
    return {"error": "Input must be a list of 8 integers"}

@app.get("/get_sequence")
def get_sequence():
    return {"sequence": sequence}

@app.post("/update_description")
def update_text(input_data: DescriptionInput):
    global description
    description = input_data.value
    return {"message": "Description updated", "text": description}

@app.get("/get_description")
def get_text():
    return {"description": description}