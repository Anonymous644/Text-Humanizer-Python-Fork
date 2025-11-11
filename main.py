# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, Any
import uvicorn

from utils.ai_detection_utils import classify_text_hf, classify_text_ensemble
from utils.text_humanizer import humanize_text_minimal
from utils.model_loaders import get_available_detectors

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

class DetectInput(BaseModel):
    text: str
    detector_model: Optional[str] = 'gpt2'  # 'gpt2', 'chatgpt', or 'ensemble'
    threshold: Optional[float] = 0.8
    
class HumanizeInput(BaseModel):
    text: str
    style: Optional[str] = 'balanced'  # Style profile
    # Optional overrides for probabilities
    synonym_probability: Optional[float] = None
    transition_probability: Optional[float] = None
    hedging_probability: Optional[float] = None
    sentence_combine_probability: Optional[float] = None
    # NEW: Optional overrides for human-like features
    human_imperfections: Optional[bool] = None
    style_variation: Optional[float] = None
    sentence_restructure: Optional[float] = None

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
    summary: Dict[str, Any]  # Allow mixed types (float and str)

@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "message": "Text Humanizer & AI Detection API",
        "version": "2.0.0",
        "endpoints": {
            "/humanize": "POST - Humanize AI-generated text with style profiles",
            "/detect": "POST - Detect AI-generated content (choose detector model)",
            "/detectors": "GET - List available AI detector models",
            "/health": "GET - Health check",
            "/docs": "GET - Interactive API documentation"
        }
    }

@app.get("/detectors")
def list_detectors():
    """List available AI detector models and their characteristics"""
    return {
        "available_models": get_available_detectors(),
        "default": "gpt2",
        "recommendation": {
            "for_modern_ai": "chatgpt",
            "for_speed": "gpt2",
            "for_older_ai": "gpt2"
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
    - **human_imperfections**: (Optional override) Add natural human errors/patterns (true/false)
    - **style_variation**: (Optional override) Vary formality within text (0.0-1.0)
    - **sentence_restructure**: (Optional override) Probability of restructuring sentences (0.0-1.0)
    
    **Style Profiles** (all do maximum humanization, differ in HOW):
    - **academic**: Formal words, academic transitions, more hedging, NO imperfections
    - **formal**: Professional tone, sophisticated vocabulary, NO imperfections
    - **casual**: Simpler words, casual transitions, contractions, WITH imperfections
    - **technical**: Conservative changes, protects technical terms, NO imperfections
    - **creative**: Varied vocabulary, diverse transitions, WITH imperfections
    - **balanced**: Default, moderate in all aspects, WITH imperfections
    
    **NEW Human-like Features:**
    - **Minor errors**: Occasional double spaces, inconsistent Oxford commas, natural fillers
    - **Varied structures**: Move prepositional phrases, reorder clauses
    - **Style inconsistency**: Mix formal/casual words within same text (like humans do!)
    - **Sentence variety**: Different lengths and structures throughout
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
    
    # NEW: Human-like feature overrides
    if data.human_imperfections is not None:
        overrides['human_imperfections'] = data.human_imperfections
    
    if data.style_variation is not None:
        if not (0.0 <= data.style_variation <= 1.0):
            raise HTTPException(status_code=400, detail="style_variation must be between 0.0 and 1.0")
        overrides['style_variation'] = data.style_variation
    
    if data.sentence_restructure is not None:
        if not (0.0 <= data.sentence_restructure <= 1.0):
            raise HTTPException(status_code=400, detail="sentence_restructure must be between 0.0 and 1.0")
        overrides['sentence_restructure'] = data.sentence_restructure
    
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
def detect_ai_text_endpoint(data: DetectInput):
    """
    Detect AI-generated content in text with model selection.
    
    - **text**: The text to analyze
    - **detector_model**: Choose detector - 'gpt2' (fast), 'chatgpt' (modern AI), or 'ensemble' (most accurate)
    - **threshold**: Confidence threshold (0.0-1.0, default 0.8) - try 0.5-0.6 for more sensitivity
    
    **Model Comparison:**
    - **gpt2** (roberta-base-openai-detector):
      - Fast, smaller memory (~500MB)
      - Best for: GPT-2, GPT-3, older AI content
      - Proven accuracy in practice
    
    - **chatgpt** (Hello-SimpleAI/chatgpt-detector-roberta):
      - Trained on ChatGPT outputs (~600MB)
      - May need threshold adjustment (try 0.5-0.6)
      - Variable performance - test first!
    
    - **ensemble** (RECOMMENDED):
      - Uses BOTH models and votes
      - Highest accuracy, catches what either model misses
      - Slower but most reliable (~1.1GB memory)
    
    Returns classification for each sentence and overall percentages.
    """
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Text input cannot be empty")
    
    # Validate detector model
    valid_models = ['gpt2', 'chatgpt', 'ensemble']
    if data.detector_model not in valid_models:
        raise HTTPException(status_code=400, detail=f"detector_model must be one of: {', '.join(valid_models)}")
    
    # Validate threshold
    if not (0.0 <= data.threshold <= 1.0):
        raise HTTPException(status_code=400, detail="threshold must be between 0.0 and 1.0")
    
    try:
        # Use ensemble if requested
        if data.detector_model == 'ensemble':
            classification_map, percentages = classify_text_ensemble(
                data.text,
                threshold=data.threshold
            )
        else:
            classification_map, percentages = classify_text_hf(
                data.text, 
                threshold=data.threshold,
                detector_model=data.detector_model
            )
        
        # Calculate overall AI percentage
        ai_percentage = percentages.get("AI-generated", 0) + percentages.get("AI-generated & AI-refined", 0)
        human_percentage = percentages.get("Human-written", 0) + percentages.get("Human-written & AI-refined", 0)
        uncertain = percentages.get("Uncertain (models disagree)", 0)
        
        return {
            "text": data.text,
            "classification_results": classification_map,
            "percentages": percentages,
            "summary": {
                "total_ai_percentage": round(ai_percentage, 2),
                "total_human_percentage": round(human_percentage, 2),
                "detector_model_used": data.detector_model,
                "threshold_used": data.threshold
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing text: {str(e)}")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "text-humanizer-api"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
