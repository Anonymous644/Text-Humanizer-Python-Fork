import nltk
from nltk.tokenize import sent_tokenize
from utils.model_loaders import load_detector_model

nltk.download('punkt', quiet=True)

def classify_text_ensemble(text, threshold=0.8):
    """
    Use BOTH detectors and combine results for better accuracy.
    If both models agree, use that. If they disagree, report as "Uncertain".
    """
    sentences = sent_tokenize(text)
    
    # Load both models
    detector_gpt2 = load_detector_model('gpt2')
    detector_chatgpt = load_detector_model('chatgpt')
    
    # Get results from both
    results_gpt2 = detector_gpt2(sentences, truncation=True)
    results_chatgpt = detector_chatgpt(sentences, truncation=True)
    
    classification_map = {}
    counts = {
        "AI-generated": 0,
        "AI-generated & AI-refined": 0,
        "Human-written": 0,
        "Human-written & AI-refined": 0,
        "Uncertain (models disagree)": 0
    }
    
    for sentence, result_gpt2, result_chatgpt in zip(sentences, results_gpt2, results_chatgpt):
        # Process both results
        label_gpt2 = result_gpt2['label'].upper()
        score_gpt2 = result_gpt2['score']
        label_chatgpt = result_chatgpt['label'].upper()
        score_chatgpt = result_chatgpt['score']
        
        # Classify each model's result
        if label_gpt2 == "FAKE":
            class_gpt2 = "AI" if score_gpt2 >= threshold else "AI-refined"
        else:
            class_gpt2 = "Human" if score_gpt2 >= threshold else "Human-refined"
        
        if label_chatgpt == "FAKE":
            class_chatgpt = "AI" if score_chatgpt >= threshold else "AI-refined"
        else:
            class_chatgpt = "Human" if score_chatgpt >= threshold else "Human-refined"
        
        # Ensemble voting: both must agree
        if class_gpt2 == class_chatgpt == "AI":
            new_label = "AI-generated"
        elif class_gpt2 == class_chatgpt == "Human":
            new_label = "Human-written"
        elif (class_gpt2 in ["AI", "AI-refined"] and class_chatgpt in ["AI", "AI-refined"]):
            new_label = "AI-generated & AI-refined"
        elif (class_gpt2 in ["Human", "Human-refined"] and class_chatgpt in ["Human", "Human-refined"]):
            new_label = "Human-written & AI-refined"
        else:
            # Models disagree significantly
            new_label = "Uncertain (models disagree)"
        
        classification_map[sentence] = new_label
        counts[new_label] += 1
    
    total = sum(counts.values())
    percentages = {
        cat: round((count / total)*100, 2) if total > 0 else 0
        for cat, count in counts.items()
    }
    return classification_map, percentages

def classify_text_hf(text, threshold=0.8, detector_model='gpt2'):
    """
    Splits text into sentences, uses selected detector to classify each sentence
    as AI-generated or human-written, returning a map of {sentence: label} and overall percentages.
    
    Args:
        text: Input text to classify
        threshold: Confidence threshold (0.0-1.0)
        detector_model: 'gpt2' (fast, older AI) or 'chatgpt' (better for modern AI)
    """
    detector = load_detector_model(detector_model)
    sentences = sent_tokenize(text)
    results = detector(sentences, truncation=True)

    classification_map = {}
    counts = {
        "AI-generated": 0,
        "AI-generated & AI-refined": 0,
        "Human-written": 0,
        "Human-written & AI-refined": 0
    }

    for sentence, result in zip(sentences, results):
        label = result['label'].upper()  # "FAKE" or "REAL"
        score = result['score']
        if label == "FAKE":
            if score >= threshold:
                new_label = "AI-generated"
            else:
                new_label = "AI-generated & AI-refined"
        elif label == "REAL":
            if score >= threshold:
                new_label = "Human-written"
            else:
                new_label = "Human-written & AI-refined"
        else:
            new_label = "Human-written"
        classification_map[sentence] = new_label
        counts[new_label] += 1

    total = sum(counts.values())
    percentages = {
        cat: round((count / total)*100, 2) if total > 0 else 0
        for cat, count in counts.items()
    }
    return classification_map, percentages
