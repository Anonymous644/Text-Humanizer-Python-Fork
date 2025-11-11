# utils/model_loaders.py
from transformers import pipeline
from functools import lru_cache

# Available detection models
DETECTOR_MODELS = {
    'gpt2': {
        'name': 'roberta-base-openai-detector',
        'description': 'Original GPT-2 detector (fast, good for older AI)',
        'best_for': 'GPT-2, GPT-3',
        'accuracy': 'High on GPT-2/3, Medium on GPT-4'
    },
    'chatgpt': {
        'name': 'Hello-SimpleAI/chatgpt-detector-roberta',
        'description': 'ChatGPT detector (trained on ChatGPT outputs)',
        'best_for': 'GPT-3.5, GPT-4, ChatGPT',
        'accuracy': 'Variable - may need threshold adjustment'
    },
    'ensemble': {
        'name': 'ensemble',
        'description': 'Uses BOTH detectors and votes for higher accuracy',
        'best_for': 'Maximum accuracy, all AI models',
        'accuracy': 'Highest - combines both models'
    }
}

@lru_cache(maxsize=3)
def load_detector_model(model_type='gpt2'):
    """
    Load an AI text detection model.
    
    Args:
        model_type: 'gpt2' (fast, older AI) or 'chatgpt' (better for modern AI)
    
    Returns:
        HuggingFace pipeline for text classification
    """
    if model_type not in DETECTOR_MODELS:
        raise ValueError(f"Invalid model_type. Choose from: {list(DETECTOR_MODELS.keys())}")
    
    model_name = DETECTOR_MODELS[model_type]['name']
    print(f"Loading AI detector model ({model_name})...")
    return pipeline("text-classification", model=model_name)

@lru_cache(maxsize=1)
def load_paraphrase_model():
    """
    Load the T5-based paraphrasing pipeline (e.g., google/flan-t5-base).
    Cached to avoid reloading the model on every request.
    """
    print("Loading T5 paraphrase model (google/flan-t5-base)...")
    return pipeline("text2text-generation", model="google/flan-t5-base")

def get_available_detectors():
    """Return information about available detector models."""
    return DETECTOR_MODELS
