"""
Models for the Walking AI Assistant application
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

class User(BaseModel):
    user_id: str
    name: Optional[str] = None
    preferred_walking_speed: Optional[float] = None
    preferred_max_distance: Optional[float] = None

class Location(BaseModel):
    latitude: float
    longitude: float
    name: Optional[str] = None
    notes: Optional[str] = None

class RouteRequest(BaseModel):
    user_id: str
    start_location: Location
    end_location: Optional[Location] = None
    max_distance_km: Optional[float] = None
    scenic: Optional[bool] = False

class WalkRecord(BaseModel):
    user_id: str
    start_location: Location
    end_location: Location
    distance_km: float
    duration_minutes: int


# File: llm_service.py
"""
LLM service for text generation
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from transformers import BitsAndBytesConfig

def setup_llm(model_name):
    """Set up the Local LLM"""
    print(f"Loading {model_name}...")
    print("Using device:", "cuda" if torch.cuda.is_available() else "cpu")

    # Define quantization config
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    # Load model and tokenizer
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=quant_config,
        device_map="auto",
        trust_remote_code=True
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    return model, tokenizer

def generate_text(model, tokenizer, prompt, max_length=512):
    """Generate text using the loaded LLM"""
    input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(model.device)
    
    # Generate with minimal parameters
    outputs = model.generate(
        input_ids,
        max_length=max_length,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.2,
        do_sample=True
    )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Remove the prompt from the response
    if response.startswith(prompt):
        response = response[len(prompt):]
    
    return response.strip()
