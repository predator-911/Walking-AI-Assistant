"""
Language Model service for text generation
"""
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Tuple
import torch

def setup_llm(model_name: str) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
    """
    Initialize the language model and tokenizer
    
    Args:
        model_name (str): Name of the Hugging Face model to load
        
    Returns:
        Tuple containing the model and tokenizer
    """
    try:
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Load model
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",  # Automatically map to available devices
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        
        # Set model to evaluation mode
        model.eval()
        
        return model, tokenizer
    except Exception as e:
        raise Exception(f"Failed to load model {model_name}: {str(e)}")

def generate_text(model: AutoModelForCausalLM, tokenizer: AutoTokenizer, 
                 prompt: str, max_length: int = 1024) -> str:
    """
    Generate text using the language model
    
    Args:
        model: Loaded language model
        tokenizer: Corresponding tokenizer
        prompt (str): Input prompt for text generation
        max_length (int): Maximum length of generated text
        
    Returns:
        str: Generated text
    """
    try:
        # Encode the prompt
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        # Generate text
        outputs = model.generate(
            **inputs,
            max_length=max_length,
            num_return_sequences=1,
            temperature=0.7,  # Moderate creativity
            top_p=0.9,       # Nucleus sampling
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
        
        # Decode and clean the output
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Remove the prompt from the output if present
        if generated_text.startswith(prompt):
            generated_text = generated_text[len(prompt):].strip()
            
        return generated_text
    except Exception as e:
        return f"Error generating text: {str(e)}"
