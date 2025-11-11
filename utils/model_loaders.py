# utils/model_loaders.py
from transformers import pipeline
from functools import lru_cache

@lru_cache(maxsize=1)
def load_detector_model():
    """
    Load the roberta-base-openai-detector pipeline for AI text detection.
    Cached to avoid reloading the model on every request.
    """
    print("Loading AI detector model (roberta-base-openai-detector)...")
    return pipeline("text-classification", model="roberta-base-openai-detector")

@lru_cache(maxsize=1)
def load_paraphrase_model():
    """
    Load the T5-based paraphrasing pipeline (e.g., google/flan-t5-base).
    Cached to avoid reloading the model on every request.
    """
    print("Loading T5 paraphrase model (google/flan-t5-base)...")
    return pipeline("text2text-generation", model="google/flan-t5-base")
