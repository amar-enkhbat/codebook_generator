from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()
sequence = [0] * 8  # Internal list of ints with length 8

class SequenceInput(BaseModel):
    values: List[int]

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
