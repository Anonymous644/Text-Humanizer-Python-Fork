# utils/text_humanizer.py
import random
import re
import ssl
import warnings
import nltk
import spacy
from nltk.corpus import wordnet
from nltk.tokenize import sent_tokenize, word_tokenize

warnings.filterwarnings("ignore", category=FutureWarning)

########################################
# Download needed NLTK resources
########################################
def download_nltk_resources():
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context

    resources = ['punkt', 'averaged_perceptron_tagger',
                 'punkt_tab', 'wordnet', 'averaged_perceptron_tagger_eng']
    for r in resources:
        try:
            nltk.download(r, quiet=True)
        except:
            pass

download_nltk_resources()

########################################
# Load spaCy pipeline
########################################
nlp = None
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Warning: spaCy en_core_web_sm model not found. Synonym replacement will be limited.")

########################################
# Citation Regex
########################################
CITATION_REGEX = re.compile(
    r"\(\s*[A-Za-z&\-,\.\s]+(?:et al\.\s*)?,\s*\d{4}(?:,\s*(?:pp?\.\s*\d+(?:-\d+)?))?\s*\)"
)

########################################
# Helper: Word & Sentence Counts
########################################
def count_words(text):
    return len(word_tokenize(text))

def count_sentences(text):
    return len(sent_tokenize(text))

########################################
# Step 1: Extract & Restore Citations
########################################
def extract_citations(text):
    refs = CITATION_REGEX.findall(text)
    placeholder_map = {}
    replaced_text = text
    for i, r in enumerate(refs, start=1):
        placeholder = f"[[REF_{i}]]"
        placeholder_map[placeholder] = r
        replaced_text = replaced_text.replace(r, placeholder, 1)
    return replaced_text, placeholder_map

PLACEHOLDER_REGEX = re.compile(r"\[\s*\[\s*REF_(\d+)\s*\]\s*\]")

def restore_citations(text, placeholder_map):
    def replace_placeholder(match):
        placeholder = match.group(0)
        return placeholder_map.get(placeholder, placeholder)
    
    restored = PLACEHOLDER_REGEX.sub(replace_placeholder, text)
    return restored

########################################
# Step 2: Expansions, Synonyms, & Transitions
########################################
contraction_map = {
    "n't": " not", "'re": " are", "'s": " is", "'ll": " will",
    "'ve": " have", "'d": " would", "'m": " am"
}

ACADEMIC_TRANSITIONS = [
    "Moreover,",
    "Additionally,",
    "Furthermore,",
    "Hence,",
    "Therefore,",
    "Consequently,",
    "Nonetheless,",
    "Nevertheless,",
    "In contrast,",
    "On the other hand,",
    "In addition,",
    "As a result,",
]

def expand_contractions(sentence):
    tokens = word_tokenize(sentence)
    expanded = []
    for t in tokens:
        replaced = False
        lower_t = t.lower()
        for contr, expansion in contraction_map.items():
            if contr in lower_t and lower_t.endswith(contr):
                new_t = lower_t.replace(contr, expansion)
                if t[0].isupper():
                    new_t = new_t.capitalize()
                expanded.append(new_t)
                replaced = True
                break
        if not replaced:
            expanded.append(t)
    return " ".join(expanded)

def replace_synonyms(sentence, p_syn=0.2):
    if not nlp:
        return sentence

    doc = nlp(sentence)
    new_tokens = []
    for token in doc:
        if "[[REF_" in token.text:
            new_tokens.append(token.text)
            continue
        if token.pos_ in ["ADJ", "NOUN", "VERB", "ADV"] and wordnet.synsets(token.text):
            if random.random() < p_syn:
                synonyms = get_synonyms(token.text, token.pos_)
                if synonyms:
                    new_tokens.append(random.choice(synonyms))
                else:
                    new_tokens.append(token.text)
            else:
                new_tokens.append(token.text)
        else:
            new_tokens.append(token.text)
    return " ".join(new_tokens)

def add_academic_transition(sentence, p_transition=0.2):
    if random.random() < p_transition:
        transition = random.choice(ACADEMIC_TRANSITIONS)
        return f"{transition} {sentence}"
    return sentence

def get_synonyms(word, pos):
    wn_pos = None
    if pos.startswith("ADJ"):
        wn_pos = wordnet.ADJ
    elif pos.startswith("NOUN"):
        wn_pos = wordnet.NOUN
    elif pos.startswith("ADV"):
        wn_pos = wordnet.ADV
    elif pos.startswith("VERB"):
        wn_pos = wordnet.VERB

    synonyms = set()
    if wn_pos:
        for syn in wordnet.synsets(word, pos=wn_pos):
            for lemma in syn.lemmas():
                lemma_name = lemma.name().replace("_", " ")
                if lemma_name.lower() != word.lower():
                    synonyms.add(lemma_name)
    return list(synonyms)

########################################
# NEW: Intelligent Sentence Combining
########################################
def detect_sentence_relationship(sent1, sent2):
    """
    Analyze the logical relationship between two sentences.
    Returns: 'addition', 'contrast', 'cause', or 'none'
    """
    if not nlp:
        return 'addition'  # Safe default
    
    sent1_lower = sent1.lower()
    sent2_lower = sent2.lower()
    
    # Contrast indicators
    contrast_words = ['however', 'but', 'although', 'despite', 'yet', 
                     'nevertheless', 'different', 'opposite', 'unlike']
    if any(word in sent2_lower for word in contrast_words):
        return 'contrast'
    
    # Cause/result indicators  
    cause_words = ['because', 'since', 'therefore', 'thus', 'so', 
                  'consequently', 'as a result', 'hence']
    if any(word in sent2_lower for word in cause_words):
        return 'cause'
    
    # Check if sent2 starts with pronoun referring to sent1 subject
    if nlp:
        doc2 = nlp(sent2)
        first_token = doc2[0] if len(doc2) > 0 else None
        if first_token and first_token.pos_ == 'PRON' and first_token.text.lower() in ['it', 'this', 'these', 'they']:
            return 'addition'  # Continuation/elaboration
    
    # Default: addition (safe connector)
    return 'addition'

def get_appropriate_connector(relationship):
    """
    Return grammatically correct connector based on sentence relationship.
    Only returns connectors that work in middle of sentence.
    """
    connectors = {
        'addition': ['and', 'and'],  # Most common, safest
        'contrast': ['but', 'yet'],   # Contrast
        'cause': ['so', 'and so'],    # Cause/effect (careful with 'because' - doesn't work mid-sentence)
        'none': ['and']               # Safe default
    }
    
    return random.choice(connectors.get(relationship, ['and']))

def combine_short_sentences(sent1, sent2):
    """
    Intelligently combine two sentences with appropriate connector.
    Only combines if it makes semantic sense.
    """
    # Get relationship
    relationship = detect_sentence_relationship(sent1, sent2)
    
    # Get appropriate connector
    connector = get_appropriate_connector(relationship)
    
    # Combine: "Sent1. Sent2" → "Sent1 and sent2"
    sent1_clean = sent1.rstrip('.!?')
    sent2_lower = sent2[0].lower() + sent2[1:] if len(sent2) > 1 else sent2.lower()
    
    combined = f"{sent1_clean} {connector} {sent2_lower}"
    
    return combined

def vary_sentence_length(sentences, p_combine=0.3):
    """
    Intelligently vary sentence length by combining short sentences.
    Uses semantic analysis to ensure grammatical correctness.
    """
    if not sentences:
        return sentences
    
    new_sentences = []
    i = 0
    
    while i < len(sentences):
        sent = sentences[i]
        word_count = len(sent.split())
        
        # Only combine very short sentences (< 6 words)
        # AND if there's a next sentence
        # AND random chance triggers
        if (word_count < 6 and 
            i + 1 < len(sentences) and 
            random.random() < p_combine):
            
            next_sent = sentences[i + 1]
            next_word_count = len(next_sent.split())
            
            # Don't combine if result would be too long (> 20 words)
            if word_count + next_word_count <= 20:
                combined = combine_short_sentences(sent, next_sent)
                new_sentences.append(combined)
                i += 2  # Skip next sentence
            else:
                new_sentences.append(sent)
                i += 1
        else:
            new_sentences.append(sent)
            i += 1
    
    return new_sentences

########################################
# NEW: Add Hedging Language
########################################
def add_hedging(sentence, p_hedge=0.15):
    """
    Add hedging language to make statements less absolute.
    Places hedges contextually before verbs or adjectives.
    """
    if not nlp or random.random() >= p_hedge:
        return sentence
    
    doc = nlp(sentence)
    
    # Hedges for different contexts
    verb_hedges = ["often", "generally", "typically", "usually", "tends to", "appears to"]
    adj_hedges = ["relatively", "fairly", "rather", "somewhat", "quite"]
    
    # Find main verb or strong adjective
    for token in doc:
        # Add hedge before main verb
        if token.pos_ == "VERB" and token.dep_ in ["ROOT", "ccomp"]:
            hedge = random.choice(verb_hedges)
            # Insert hedge before verb
            pattern = r'\b' + re.escape(token.text) + r'\b'
            sentence = re.sub(pattern, f"{hedge} {token.text}", sentence, count=1)
            break
        
        # Add hedge before strong adjective
        elif token.pos_ == "ADJ" and token.text.lower() in ['significant', 'important', 'critical', 'essential', 'major']:
            hedge = random.choice(adj_hedges)
            pattern = r'\b' + re.escape(token.text) + r'\b'
            sentence = re.sub(pattern, f"{hedge} {token.text}", sentence, count=1)
            break
    
    return sentence

########################################
# Step 3: Enhanced "Humanize" line-by-line
########################################
def minimal_humanize_line(line, p_syn=0.2, p_trans=0.2, p_hedge=0.15):
    line = expand_contractions(line)
    line = replace_synonyms(line, p_syn=p_syn)
    line = add_hedging(line, p_hedge=p_hedge)  # NEW
    line = add_academic_transition(line, p_transition=p_trans)
    return line

def minimal_rewriting(text, p_syn=0.2, p_trans=0.2, p_hedge=0.15, p_combine=0.3):
    lines = sent_tokenize(text)
    
    # Apply transformations to each sentence
    out_lines = [
        minimal_humanize_line(ln, p_syn=p_syn, p_trans=p_trans, p_hedge=p_hedge) 
        for ln in lines
    ]
    
    # NEW: Intelligently vary sentence length
    out_lines = vary_sentence_length(out_lines, p_combine=p_combine)
    
    return " ".join(out_lines)

########################################
# Main API Function
########################################
def humanize_text_minimal(text, p_syn=0.2, p_trans=0.2, p_hedge=0.15, p_combine=0.3):
    """
    Humanize text with minimal changes while preserving citations.
    
    Args:
        text: Input text to humanize
        p_syn: Probability of synonym replacement (0.0-1.0)
        p_trans: Probability of adding academic transitions (0.0-1.0)
        p_hedge: Probability of adding hedging language (0.0-1.0)
        p_combine: Probability of combining short sentences (0.0-1.0)
    
    Returns:
        Dictionary with original and humanized text, plus word/sentence counts
    """
    orig_wc = count_words(text)
    orig_sc = count_sentences(text)
    
    # Extract citations
    no_refs_text, placeholders = extract_citations(text)
    
    # Rewrite text with all transformations
    partially_rewritten = minimal_rewriting(
        no_refs_text, 
        p_syn=p_syn, 
        p_trans=p_trans,
        p_hedge=p_hedge,
        p_combine=p_combine
    )
    
    # Restore citations
    final_text = restore_citations(partially_rewritten, placeholders)
    
    # Normalize spaces around punctuation
    final_text = re.sub(r"\s+([.,;:!?])", r"\1", final_text)
    final_text = re.sub(r"(\()\s+", r"\1", final_text)
    final_text = re.sub(r"\s+(\))", r")", final_text)
    
    new_wc = count_words(final_text)
    new_sc = count_sentences(final_text)
    
    return {
        "original_text": text,
        "humanized_text": final_text,
        "original_word_count": orig_wc,
        "humanized_word_count": new_wc,
        "original_sentence_count": orig_sc,
        "humanized_sentence_count": new_sc
    }
