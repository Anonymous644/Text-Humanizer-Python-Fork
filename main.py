# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
import uvicorn

from utils.ai_detection_utils import classify_text_hf
from utils.text_humanizer import humanize_text_minimal

app = FastAPI(
    title="Text Humanizer & AI Detection API",
    description="Backend API for humanizing AI text and detecting AI-generated content",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class TextInput(BaseModel):
    text: str
    
class HumanizeInput(BaseModel):
    text: str
    style: Optional[str] = 'balanced'  # Style profile
    # Optional overrides
    synonym_probability: Optional[float] = None
    transition_probability: Optional[float] = None
    hedging_probability: Optional[float] = None
    sentence_combine_probability: Optional[float] = None

class HumanizeResponse(BaseModel):
    original_text: str
    humanized_text: str
    original_word_count: int
    humanized_word_count: int
    original_sentence_count: int
    humanized_sentence_count: int
    style_used: str

class DetectResponse(BaseModel):
    text: str
    classification_results: Dict[str, str]
    percentages: Dict[str, float]
    summary: Dict[str, float]

@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "message": "Text Humanizer & AI Detection API",
        "version": "1.0.0",
        "endpoints": {
            "/humanize": "POST - Humanize AI-generated text",
            "/detect": "POST - Detect AI-generated content in text",
            "/docs": "GET - Interactive API documentation"
        }
    }

@app.post("/humanize", response_model=HumanizeResponse)
def humanize_text_endpoint(data: HumanizeInput):
    """
    Humanize AI-generated text with style profiles.
    
    - **text**: The text to humanize
    - **style**: Style profile - 'academic', 'formal', 'casual', 'technical', 'creative', 'balanced' (default)
    - **synonym_probability**: (Optional override) Probability of replacing words with synonyms (0.0-1.0)
    - **transition_probability**: (Optional override) Probability of adding transitions (0.0-1.0)
    - **hedging_probability**: (Optional override) Probability of adding hedging language (0.0-1.0)
    - **sentence_combine_probability**: (Optional override) Probability of combining short sentences (0.0-1.0)
    
    **Style Profiles** (all do maximum humanization, differ in HOW):
    - **academic**: Formal words, academic transitions, more hedging
    - **formal**: Professional tone, sophisticated vocabulary
    - **casual**: Simpler words, casual transitions, contractions, more combining
    - **technical**: Conservative changes, protects technical terms
    - **creative**: Varied vocabulary, diverse transitions
    - **balanced**: Default, moderate in all aspects
    """
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Text input cannot be empty")
    
    # Validate style
    valid_styles = ['academic', 'formal', 'casual', 'technical', 'creative', 'balanced']
    if data.style not in valid_styles:
        raise HTTPException(status_code=400, detail=f"style must be one of: {', '.join(valid_styles)}")
    
    # Build overrides dict (only include non-None values)
    overrides = {}
    if data.synonym_probability is not None:
        if not (0.0 <= data.synonym_probability <= 1.0):
            raise HTTPException(status_code=400, detail="synonym_probability must be between 0.0 and 1.0")
        overrides['synonym_probability'] = data.synonym_probability
    
    if data.transition_probability is not None:
        if not (0.0 <= data.transition_probability <= 1.0):
            raise HTTPException(status_code=400, detail="transition_probability must be between 0.0 and 1.0")
        overrides['transition_probability'] = data.transition_probability
    
    if data.hedging_probability is not None:
        if not (0.0 <= data.hedging_probability <= 1.0):
            raise HTTPException(status_code=400, detail="hedging_probability must be between 0.0 and 1.0")
        overrides['hedging_probability'] = data.hedging_probability
    
    if data.sentence_combine_probability is not None:
        if not (0.0 <= data.sentence_combine_probability <= 1.0):
            raise HTTPException(status_code=400, detail="sentence_combine_probability must be between 0.0 and 1.0")
        overrides['sentence_combine_probability'] = data.sentence_combine_probability
    
    try:
        result = humanize_text_minimal(
            data.text,
            style=data.style,
            **overrides
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing text: {str(e)}")

@app.post("/detect", response_model=DetectResponse)
def detect_ai_text_endpoint(data: TextInput):
    """
    Detect AI-generated content in text.
    
    - **text**: The text to analyze for AI detection
    
    Returns classification for each sentence and overall percentages.
    """
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Text input cannot be empty")
    
    try:
        classification_map, percentages = classify_text_hf(data.text)
        
        return {
            "text": data.text,
            "classification_results": classification_map,
            "percentages": percentages,
            "summary": percentages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing text: {str(e)}")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "text-humanizer-api"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
