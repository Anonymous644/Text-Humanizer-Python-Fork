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
    synonym_probability: Optional[float] = 0.2
    transition_probability: Optional[float] = 0.2

class HumanizeResponse(BaseModel):
    original_text: str
    humanized_text: str
    original_word_count: int
    humanized_word_count: int
    original_sentence_count: int
    humanized_sentence_count: int

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
    Humanize AI-generated text while preserving citations.
    
    - **text**: The text to humanize
    - **synonym_probability**: Probability of replacing words with synonyms (0.0-1.0)
    - **transition_probability**: Probability of adding academic transitions (0.0-1.0)
    """
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Text input cannot be empty")
    
    if not (0.0 <= data.synonym_probability <= 1.0):
        raise HTTPException(status_code=400, detail="synonym_probability must be between 0.0 and 1.0")
    
    if not (0.0 <= data.transition_probability <= 1.0):
        raise HTTPException(status_code=400, detail="transition_probability must be between 0.0 and 1.0")
    
    try:
        result = humanize_text_minimal(
            data.text,
            p_syn=data.synonym_probability,
            p_trans=data.transition_probability
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
