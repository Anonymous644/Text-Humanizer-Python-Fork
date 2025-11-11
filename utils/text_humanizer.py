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
# NEW: Comprehensive Hedging Language System
########################################

# Expanded hedging vocabulary organized by type
HEDGING_LIBRARY = {
    # Adverbs of frequency - how often something happens
    'frequency': [
        "often", "generally", "typically", "usually", "frequently",
        "commonly", "normally", "regularly", "ordinarily", "customarily",
        "sometimes", "occasionally", "periodically", "sporadically"
    ],
    
    # Epistemic stance - degree of certainty
    'epistemic': [
        "appears to", "seems to", "tends to", "appears that",
        "seems that", "suggests that", "indicates that",
        "may", "might", "could", "would", "should",
        "possibly", "probably", "likely", "perhaps", "potentially"
    ],
    
    # Approximators - degree/extent modifiers
    'approximators': [
        "relatively", "fairly", "rather", "somewhat", "quite",
        "reasonably", "moderately", "comparatively", "largely",
        "mostly", "mainly", "primarily", "predominantly",
        "essentially", "basically", "fundamentally"
    ],
    
    # Quantifiers - amount hedging
    'quantifiers': [
        "many", "some", "several", "various", "numerous",
        "a number of", "a variety of", "certain", "particular",
        "most", "the majority of", "a large portion of"
    ],
    
    # Evidential markers - source of knowledge
    'evidential': [
        "it appears that", "it seems that", "it is likely that",
        "research suggests", "studies indicate", "evidence shows",
        "findings suggest", "data indicates", "results demonstrate",
        "observations suggest", "analysis reveals"
    ],
    
    # Conditional/Hypothetical
    'conditional': [
        "may", "might", "could potentially", "would likely",
        "can", "could possibly", "might possibly"
    ],
    
    # Scope limiters - restricting claims
    'scope_limiters': [
        "in many cases", "in most cases", "in some cases",
        "to some extent", "to a certain degree", "to a large extent",
        "in general", "on the whole", "for the most part",
        "by and large", "as a rule"
    ]
}

# Strong claim words that benefit from hedging
STRONG_ADJECTIVES = [
    'significant', 'important', 'critical', 'essential', 'crucial',
    'vital', 'key', 'major', 'substantial', 'considerable',
    'dramatic', 'remarkable', 'notable', 'exceptional', 'outstanding',
    'definite', 'certain', 'absolute', 'complete', 'total',
    'perfect', 'ideal', 'optimal', 'superior', 'excellent'
]

STRONG_VERBS = [
    'proves', 'demonstrates', 'shows', 'confirms', 'establishes',
    'determines', 'verifies', 'validates', 'certifies', 'guarantees',
    'ensures', 'assures', 'solves', 'eliminates', 'prevents',
    'causes', 'creates', 'produces', 'generates', 'achieves'
]

STRONG_NOUNS = [
    'proof', 'evidence', 'fact', 'truth', 'certainty',
    'solution', 'answer', 'result', 'conclusion', 'finding'
]

########################################
# NEW: Advanced Safety Checks
########################################

# Technical/Domain keywords that indicate literal usage (don't hedge these sentences)
TECHNICAL_INDICATORS = [
    # Programming/CS
    'algorithm', 'function', 'method', 'class', 'variable', 'array', 'pointer',
    'database', 'query', 'SQL', 'API', 'endpoint', 'HTTP', 'JSON', 'XML',
    'thread', 'process', 'memory', 'CPU', 'cache', 'compile', 'runtime',
    'syntax', 'parse', 'execute', 'debug', 'exception', 'error', 'stack',
    
    # Mathematics
    'equation', 'theorem', 'formula', 'calculate', 'compute', 'equal',
    'multiply', 'divide', 'addition', 'subtraction', 'integer', 'decimal',
    
    # Technical specifications
    'specification', 'protocol', 'standard', 'compliance', 'compatible',
    'version', 'release', 'update', 'patch', 'requirement',
    
    # Physical measurements
    'meter', 'kilogram', 'second', 'volt', 'ampere', 'watt', 'hertz',
    'celsius', 'fahrenheit', 'degree', 'measurement',
    
    # UI/Display (literal "shows")
    'display', 'screen', 'monitor', 'interface', 'button', 'menu', 'dialog',
    'window', 'panel', 'tab', 'icon', 'cursor'
]

# Verbs that have literal meanings and shouldn't be hedged in certain contexts
LITERAL_VERB_CONTEXTS = {
    'shows': ['display', 'screen', 'monitor', 'figure', 'table', 'chart', 'graph', 'image'],
    'displays': ['screen', 'monitor', 'interface', 'system', 'device'],
    'indicates': ['sign', 'symbol', 'light', 'indicator', 'gauge', 'meter'],
    'represents': ['symbol', 'notation', 'variable', 'constant', 'figure'],
    'contains': ['box', 'container', 'array', 'list', 'set', 'collection'],
    'returns': ['function', 'method', 'call', 'query', 'request'],
    'produces': ['generator', 'factory', 'builder', 'compiler']
}

# Patterns that indicate facts/definitions (don't hedge these)
FACTUAL_PATTERNS = [
    r'\d+\s*[\+\-\*\/\=]\s*\d+',  # Mathematical expressions: 2 + 2 = 4
    r'is defined as',              # Definitions
    r'refers to',                  # References
    r'means that',                 # Meanings
    r'by definition',              # Definitions
    r'is called',                  # Nomenclature
    r'is known as',                # Nomenclature
]

def should_skip_hedging(sentence, doc):
    """
    Advanced safety check to determine if sentence should NOT be hedged.
    Returns True if hedging should be skipped.
    """
    sentence_lower = sentence.lower()
    
    # Check 1: Skip very short sentences (< 4 words)
    if len(sentence.split()) < 4:
        return True
    
    # Check 2: Skip sentences with technical indicators
    for indicator in TECHNICAL_INDICATORS:
        if indicator.lower() in sentence_lower:
            return True
    
    # Check 3: Skip sentences matching factual patterns
    for pattern in FACTUAL_PATTERNS:
        if re.search(pattern, sentence_lower):
            return True
    
    # Check 4: Skip questions (already uncertain by nature)
    if sentence.strip().endswith('?'):
        return True
    
    # Check 5: Skip commands/imperatives
    if doc and len(doc) > 0:
        # Check if first token is a verb in imperative form
        first_token = doc[0]
        if first_token.pos_ == "VERB" and first_token.tag_ == "VB":
            return True
    
    # Check 6: Skip if sentence has numbers that look like facts/measurements
    # e.g., "The temperature is 25 degrees"
    if re.search(r'\d+\s*(percent|%|degrees?|meters?|feet|inches|kg|lb|ml|l\b)', sentence_lower):
        return True
    
    # Check 7: Skip citations (already handled, but double-check)
    if '[[REF_' in sentence:
        return True
    
    return False

def is_literal_verb_usage(verb_text, sentence, doc):
    """
    Detect if a verb is being used literally (not as a claim).
    
    Examples:
    - "The screen shows the menu" → True (literal display)
    - "The study shows improvement" → False (claim/finding)
    """
    verb_lower = verb_text.lower()
    sentence_lower = sentence.lower()
    
    # Check if this verb has literal contexts
    if verb_lower not in LITERAL_VERB_CONTEXTS:
        return False
    
    # Check if any literal context words appear in the sentence
    literal_contexts = LITERAL_VERB_CONTEXTS[verb_lower]
    for context_word in literal_contexts:
        if context_word in sentence_lower:
            return True
    
    return False

def detect_subject_type(sentence, doc):
    """
    Detect the type of subject to determine if hedging is appropriate.
    
    Returns:
    - 'technical': Technical system/object (don't hedge strong claims)
    - 'research': Research/study claims (hedge these)
    - 'general': General claims (hedge these)
    """
    if not doc:
        return 'general'
    
    sentence_lower = sentence.lower()
    
    # Technical subjects
    technical_subjects = [
        'the system', 'the algorithm', 'the function', 'the method',
        'the api', 'the interface', 'the display', 'the screen',
        'the application', 'the software', 'the program', 'the code'
    ]
    
    for tech_subj in technical_subjects:
        if tech_subj in sentence_lower:
            return 'technical'
    
    # Research subjects (these SHOULD be hedged)
    research_subjects = [
        'the study', 'the research', 'the analysis', 'the investigation',
        'the findings', 'the results', 'the data', 'the evidence',
        'the experiment', 'the trial', 'the observation'
    ]
    
    for research_subj in research_subjects:
        if research_subj in sentence_lower:
            return 'research'
    
    return 'general'

def add_hedging(sentence, p_hedge=0.15):
    """
    Comprehensive hedging system with multiple strategies and advanced safety checks.
    Adds appropriate hedging based on sentence structure and content.
    """
    if not nlp or random.random() >= p_hedge:
        return sentence
    
    doc = nlp(sentence)
    original_sentence = sentence
    hedged = False
    
    # NEW: Advanced safety check - skip if inappropriate
    if should_skip_hedging(sentence, doc):
        return sentence
    
    # NEW: Detect subject type for context-aware hedging
    subject_type = detect_subject_type(sentence, doc)
    
    # Skip hedging for technical specifications with strong guarantees
    if subject_type == 'technical' and any(word in sentence.lower() for word in ['guarantees', 'ensures', 'requires']):
        return sentence
    
    # Strategy 1: Modal verbs for strong claims (30% of time)
    if not hedged and random.random() < 0.3:
        sentence, hedged = add_modal_hedging(sentence, doc)
    
    # Strategy 2: Frequency adverbs before verbs (25% of time)
    if not hedged and random.random() < 0.25:
        sentence, hedged = add_frequency_hedging(sentence, doc)
    
    # Strategy 3: Approximators for adjectives (20% of time)
    if not hedged and random.random() < 0.2:
        sentence, hedged = add_approximator_hedging(sentence, doc)
    
    # Strategy 4: Epistemic stance markers (15% of time)
    if not hedged and random.random() < 0.15:
        sentence, hedged = add_epistemic_hedging(sentence, doc)
    
    # Strategy 5: Scope limiters at sentence start (10% of time)
    if not hedged and random.random() < 0.1:
        sentence, hedged = add_scope_limiter(sentence)
    
    return sentence if hedged else original_sentence

def add_modal_hedging(sentence, doc):
    """Replace or add modal verbs to soften strong claims with literal verb detection"""
    
    # Replace strong verbs with hedged versions
    replacements = {
        'proves': ['suggests', 'indicates', 'may prove', 'appears to prove'],
        'demonstrates': ['suggests', 'indicates', 'seems to demonstrate', 'may demonstrate'],
        'shows': ['suggests', 'indicates', 'appears to show', 'tends to show'],
        'confirms': ['supports', 'suggests', 'may confirm', 'appears to confirm'],
        'guarantees': ['may ensure', 'likely ensures', 'tends to ensure'],
        'ensures': ['may ensure', 'helps ensure', 'can ensure'],
        'is': ['may be', 'could be', 'might be', 'appears to be'],
        'are': ['may be', 'could be', 'might be', 'appear to be'],
        'will': ['may', 'might', 'could', 'would likely'],
        'causes': ['may cause', 'can cause', 'tends to cause'],
        'solves': ['may solve', 'can help solve', 'tends to solve']
    }
    
    for strong_verb, hedged_versions in replacements.items():
        pattern = r'\b' + re.escape(strong_verb) + r'\b'
        if re.search(pattern, sentence, re.IGNORECASE):
            # NEW: Check for literal verb usage
            if is_literal_verb_usage(strong_verb, sentence, doc):
                continue  # Skip this verb, it's being used literally
            
            hedge = random.choice(hedged_versions)
            sentence = re.sub(pattern, hedge, sentence, count=1, flags=re.IGNORECASE)
            return sentence, True
    
    return sentence, False

def add_frequency_hedging(sentence, doc):
    """Add frequency adverbs before main verbs with literal verb detection"""
    
    for token in doc:
        if token.pos_ == "VERB" and token.dep_ in ["ROOT", "ccomp", "xcomp"]:
            # Skip if already has a frequency adverb
            if any(child.text.lower() in HEDGING_LIBRARY['frequency'] for child in token.children):
                continue
            
            # NEW: Check for literal verb usage
            if is_literal_verb_usage(token.text, sentence, doc):
                continue  # Skip this verb, it's being used literally
            
            hedge = random.choice(HEDGING_LIBRARY['frequency'])
            pattern = r'\b' + re.escape(token.text) + r'\b'
            
            # Check if we can insert the hedge
            match = re.search(pattern, sentence)
            if match:
                sentence = re.sub(pattern, f"{hedge} {token.text}", sentence, count=1)
                return sentence, True
    
    return sentence, False

def add_approximator_hedging(sentence, doc):
    """Add approximators before strong adjectives"""
    
    for token in doc:
        if token.pos_ == "ADJ":
            # Target strong adjectives
            if token.text.lower() in [adj.lower() for adj in STRONG_ADJECTIVES]:
                # Skip if already modified
                if any(child.pos_ == "ADV" for child in token.children):
                    continue
                
                hedge = random.choice(HEDGING_LIBRARY['approximators'])
                pattern = r'\b' + re.escape(token.text) + r'\b'
                
                match = re.search(pattern, sentence)
                if match:
                    sentence = re.sub(pattern, f"{hedge} {token.text}", sentence, count=1)
                    return sentence, True
    
    return sentence, False

def add_epistemic_hedging(sentence, doc):
    """Add epistemic stance markers (appears to, seems to, etc.)"""
    
    # Look for main verb
    for token in doc:
        if token.pos_ == "VERB" and token.dep_ == "ROOT":
            # Choose appropriate epistemic marker
            if token.text.lower() in [v.lower() for v in STRONG_VERBS]:
                epistemic_phrases = [
                    "appears to", "seems to", "tends to",
                    "is likely to", "is believed to"
                ]
            else:
                epistemic_phrases = HEDGING_LIBRARY['epistemic'][:5]  # First 5 are most natural
            
            hedge = random.choice(epistemic_phrases)
            
            # If hedge ends with 'to', we need the base form of verb
            if hedge.endswith('to'):
                pattern = r'\b' + re.escape(token.text) + r'\b'
                # Get base form if possible
                base_form = token.lemma_ if hasattr(token, 'lemma_') else token.text
                sentence = re.sub(pattern, f"{hedge} {base_form}", sentence, count=1)
                return sentence, True
    
    return sentence, False

def add_scope_limiter(sentence):
    """Add scope limiting phrases at the beginning"""
    
    # Don't add if sentence already starts with a hedge
    first_words = sentence.split()[:3]
    first_phrase = ' '.join(first_words).lower()
    
    existing_hedges = [
        'generally', 'typically', 'often', 'usually', 'moreover',
        'furthermore', 'however', 'additionally', 'in fact'
    ]
    
    if any(hedge in first_phrase for hedge in existing_hedges):
        return sentence, False
    
    limiter = random.choice(HEDGING_LIBRARY['scope_limiters'])
    sentence = f"{limiter}, {sentence[0].lower()}{sentence[1:]}"
    return sentence, True

def add_quantifier_hedging(sentence, doc):
    """Add quantifier hedging for overly broad statements"""
    
    # Replace absolute quantifiers with hedged ones
    replacements = {
        'all': ['many', 'most', 'the majority of'],
        'every': ['many', 'most'],
        'always': ['often', 'typically', 'generally'],
        'never': ['rarely', 'seldom', 'infrequently'],
        'none': ['few', 'very few'],
        'everything': ['many things', 'most things']
    }
    
    for absolute, hedged_versions in replacements.items():
        pattern = r'\b' + re.escape(absolute) + r'\b'
        if re.search(pattern, sentence, re.IGNORECASE):
            hedge = random.choice(hedged_versions)
            sentence = re.sub(pattern, hedge, sentence, count=1, flags=re.IGNORECASE)
            return sentence, True
    
    return sentence, False

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
