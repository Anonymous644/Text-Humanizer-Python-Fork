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
# Style Profiles - Maximum Humanization with Different Styles
########################################
STYLE_PROFILES = {
    'academic': {
        'synonym_probability': 0.35,
        'transition_probability': 0.40,
        'hedging_probability': 0.30,
        'sentence_combine_probability': 0.35,
        'synonym_formality': 'formal',
        'transition_style': 'academic',
        'expand_contractions': True,
        'add_contractions': False,
        'human_imperfections': False,  # Keep academic perfect
        'style_variation': 0.05,  # Minimal variation
        'sentence_restructure': 0.10,
    },
    'formal': {
        'synonym_probability': 0.35,
        'transition_probability': 0.35,
        'hedging_probability': 0.25,
        'sentence_combine_probability': 0.30,
        'synonym_formality': 'formal',
        'transition_style': 'formal',
        'expand_contractions': True,
        'add_contractions': False,
        'human_imperfections': False,  # Keep formal perfect
        'style_variation': 0.10,
        'sentence_restructure': 0.15,
    },
    'casual': {
        'synonym_probability': 0.40,
        'transition_probability': 0.35,
        'hedging_probability': 0.10,
        'sentence_combine_probability': 0.45,
        'synonym_formality': 'casual',
        'transition_style': 'casual',
        'expand_contractions': False,
        'add_contractions': True,
        'human_imperfections': True,  # Add natural imperfections
        'style_variation': 0.25,  # More variation
        'sentence_restructure': 0.25,
    },
    'technical': {
        'synonym_probability': 0.30,
        'transition_probability': 0.30,
        'hedging_probability': 0.25,
        'sentence_combine_probability': 0.25,
        'synonym_formality': 'neutral',
        'transition_style': 'technical',
        'expand_contractions': True,
        'add_contractions': False,
        'human_imperfections': False,  # Technical stays clean
        'style_variation': 0.05,
        'sentence_restructure': 0.10,
    },
    'creative': {
        'synonym_probability': 0.45,
        'transition_probability': 0.40,
        'hedging_probability': 0.15,
        'sentence_combine_probability': 0.40,
        'synonym_formality': 'varied',
        'transition_style': 'creative',
        'expand_contractions': False,
        'add_contractions': False,
        'human_imperfections': True,  # Creative can be imperfect
        'style_variation': 0.30,  # High variation
        'sentence_restructure': 0.30,
    },
    'balanced': {  # Default
        'synonym_probability': 0.30,
        'transition_probability': 0.30,
        'hedging_probability': 0.20,
        'sentence_combine_probability': 0.35,
        'synonym_formality': 'neutral',
        'transition_style': 'general',
        'expand_contractions': True,
        'add_contractions': False,
        'human_imperfections': True,  # Balanced has some imperfections
        'style_variation': 0.15,
        'sentence_restructure': 0.20,
    }
}

########################################
# Step 2: Expansions, Synonyms, & Transitions
########################################
contraction_map = {
    "n't": " not", "'re": " are", "'s": " is", "'ll": " will",
    "'ve": " have", "'d": " would", "'m": " am"
}

# Reverse mapping for adding contractions (casual style)
expansion_to_contraction = {
    "do not": "don't", "does not": "doesn't", "did not": "didn't",
    "will not": "won't", "would not": "wouldn't", "should not": "shouldn't",
    "cannot": "can't", "could not": "couldn't",
    "is not": "isn't", "are not": "aren't", "was not": "wasn't", "were not": "weren't",
    "has not": "hasn't", "have not": "haven't", "had not": "hadn't",
    "it is": "it's", "that is": "that's", "what is": "what's",
    "they are": "they're", "we are": "we're", "you are": "you're",
    "i am": "i'm", "he is": "he's", "she is": "she's",
    "i will": "i'll", "you will": "you'll", "we will": "we'll",
    "i have": "i've", "you have": "you've", "we have": "we've",
    "i would": "i'd", "you would": "you'd", "they would": "they'd"
}

# Context-aware transitions organized by style and relationship
TRANSITIONS_BY_STYLE = {
    'academic': {
        'addition': ["Moreover,", "Furthermore,", "Additionally,", "In addition,"],
        'contrast': ["However,", "Nevertheless,", "Nonetheless,", "Conversely,"],
        'cause': ["Therefore,", "Thus,", "Hence,", "Consequently,"],
        'emphasis': ["Indeed,", "Notably,", "Particularly,", "Significantly,"],
    },
    'formal': {
        'addition': ["Furthermore,", "Moreover,", "In addition,"],
        'contrast': ["However,", "Nevertheless,", "Notwithstanding,"],
        'cause': ["Therefore,", "Consequently,", "Accordingly,"],
        'emphasis': ["Indeed,", "Notably,", "Significantly,"],
    },
    'casual': {
        'addition': ["Also,", "Plus,", "And,", "Besides,"],
        'contrast': ["But,", "Though,", "Still,", "Yet,"],
        'cause': ["So,", "That's why,", "Because of this,"],
        'emphasis': ["Actually,", "Really,", "In fact,"],
    },
    'technical': {
        'addition': ["Additionally,", "Moreover,", "Furthermore,"],
        'contrast': ["However,", "Conversely,"],
        'cause': ["Therefore,", "Thus,", "Consequently,"],
        'emphasis': ["Notably,", "Significantly,"],
    },
    'creative': {
        'addition': ["What's more,", "Besides,", "Also,", "And,"],
        'contrast': ["Yet,", "Still,", "Even so,", "On the other hand,"],
        'cause': ["So,", "Thus,", "As a result,"],
        'emphasis': ["Interestingly,", "Remarkably,", "Surprisingly,"],
    },
    'general': {  # Fallback
        'addition': ["Moreover,", "Additionally,", "Furthermore,", "Also,"],
        'contrast': ["However,", "Nevertheless,", "Yet,", "Still,"],
        'cause': ["Therefore,", "Thus,", "So,", "Consequently,"],
        'emphasis': ["Indeed,", "In fact,", "Notably,"],
    }
}

# Technical/domain terms that should NEVER be replaced
PROTECTED_TERMS = {
    # Programming
    'algorithm', 'function', 'method', 'class', 'array', 'string', 'integer',
    'boolean', 'float', 'variable', 'constant', 'parameter', 'argument',
    'loop', 'iteration', 'recursion', 'pointer', 'reference', 'object',
    'instance', 'interface', 'implementation', 'inheritance', 'polymorphism',
    
    # Data structures
    'list', 'queue', 'stack', 'tree', 'graph', 'node', 'edge', 'heap',
    
    # CS concepts
    'database', 'query', 'index', 'cache', 'buffer', 'memory', 'cpu',
    'thread', 'process', 'socket', 'protocol', 'network', 'server', 'client',
    
    # Math/Stats
    'equation', 'formula', 'theorem', 'proof', 'hypothesis', 'correlation',
    'regression', 'variance', 'deviation', 'mean', 'median', 'mode',
    'probability', 'statistic', 'distribution',
    
    # Research terms
    'methodology', 'participant', 'variable', 'control', 'experiment',
    'sample', 'population', 'dataset', 'metric', 'measure',
    
    # General technical
    'system', 'model', 'framework', 'architecture', 'structure',
    'component', 'module', 'layer', 'interface', 'endpoint'
}

# Words that are too common/generic to replace
SKIP_COMMON_WORDS = {
    'thing', 'way', 'time', 'make', 'get', 'go', 'come', 'take',
    'see', 'look', 'use', 'find', 'give', 'tell', 'ask', 'work',
    'seem', 'feel', 'try', 'leave', 'call', 'good', 'new', 'first',
    'last', 'long', 'great', 'little', 'own', 'other', 'old', 'right',
    'big', 'high', 'different', 'small', 'large', 'next', 'early',
    'young', 'important', 'few', 'public', 'bad', 'same', 'able'
}

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

def add_contractions(sentence):
    """Add contractions for casual style."""
    for expansion, contraction in expansion_to_contraction.items():
        # Case-insensitive replacement
        pattern = re.compile(re.escape(expansion), re.IGNORECASE)
        sentence = pattern.sub(contraction, sentence)
    return sentence

def replace_synonyms(sentence, p_syn=0.2, formality='neutral'):
    """Smart synonym replacement with style-aware formality."""
    if not nlp:
        return sentence

    doc = nlp(sentence)
    new_tokens = []
    
    for token in doc:
        # Skip citations
        if "[[REF_" in token.text:
            new_tokens.append(token.text)
            continue
        
        # Skip punctuation and non-words
        if token.pos_ not in ["ADJ", "NOUN", "VERB", "ADV"]:
            new_tokens.append(token.text)
            continue
        
        # Skip protected technical terms
        if token.text.lower() in PROTECTED_TERMS:
            new_tokens.append(token.text)
            continue
        
        # Skip very common/generic words (unless casual style wants simpler)
        if token.text.lower() in SKIP_COMMON_WORDS and formality != 'casual':
            new_tokens.append(token.text)
            continue
        
        # Skip proper nouns (names, places, etc.)
        if token.pos_ == "PROPN":
            new_tokens.append(token.text)
            continue
        
        # Try replacement with probability
        if wordnet.synsets(token.text) and random.random() < p_syn:
            synonyms = get_smart_synonyms(token.text, token.pos_, sentence, formality)
            if synonyms:
                new_tokens.append(random.choice(synonyms))
            else:
                new_tokens.append(token.text)
        else:
            new_tokens.append(token.text)
    
    return " ".join(new_tokens)

def add_academic_transition(sentence, prev_sentence=None, used_transitions=None, p_transition=0.2, style='general'):
    """
    Style-aware transition addition that matches sentence relationship.
    Tracks used transitions to avoid repetition.
    """
    if random.random() >= p_transition:
        return sentence
    
    # Don't add if sentence already starts with a transition
    first_word = sentence.split()[0] if sentence.split() else ""
    existing_transitions = ['moreover', 'however', 'therefore', 'furthermore', 
                           'additionally', 'consequently', 'nevertheless', 'thus',
                           'hence', 'indeed', 'besides', 'likewise', 'also', 'plus',
                           'but', 'so', 'yet', 'still', 'actually', 'really']
    if first_word.lower().rstrip(',') in existing_transitions:
        return sentence
    
    # Get transitions for this style
    style_transitions = TRANSITIONS_BY_STYLE.get(style, TRANSITIONS_BY_STYLE['general'])
    
    # Determine appropriate transition type based on previous sentence
    if prev_sentence and nlp:
        relationship = detect_sentence_relationship(prev_sentence, sentence)
        
        # Map relationship to transition type
        if relationship == 'contrast':
            transition_type = 'contrast'
        elif relationship == 'cause':
            transition_type = 'cause'
        elif relationship in ['addition', 'none']:
            transition_type = 'addition'
        else:
            transition_type = 'addition'  # Default to addition
    else:
        transition_type = 'addition'
    
    # Get appropriate transitions for this type
    available_transitions = style_transitions.get(transition_type, style_transitions['addition'])
    
    # Filter out recently used transitions if tracking is enabled
    if used_transitions is not None:
        unused = [t for t in available_transitions if t not in used_transitions]
        if unused:
            available_transitions = unused
    
    # Select and track transition
    transition = random.choice(available_transitions)
    if used_transitions is not None:
        used_transitions.add(transition)
        # Keep only last 3 transitions in memory
        if len(used_transitions) > 3:
            used_transitions.pop()
    
    return f"{transition} {sentence}"

def get_smart_synonyms(word, pos, sentence_context="", formality='neutral'):
    """
    Get quality-filtered synonyms that fit the context and formality level.
    """
    wn_pos = None
    if pos.startswith("ADJ"):
        wn_pos = wordnet.ADJ
    elif pos.startswith("NOUN"):
        wn_pos = wordnet.NOUN
    elif pos.startswith("ADV"):
        wn_pos = wordnet.ADV
    elif pos.startswith("VERB"):
        wn_pos = wordnet.VERB

    if not wn_pos:
        return []
    
    synonyms = []
    word_lower = word.lower()
    
    # Get synsets (meaning groups)
    synsets = wordnet.synsets(word, pos=wn_pos)
    
    # Only use the first 2 synsets (most common meanings)
    for syn in synsets[:2]:
        for lemma in syn.lemmas():
            lemma_name = lemma.name().replace("_", " ")
            lemma_lower = lemma_name.lower()
            
            # Skip if same as original
            if lemma_lower == word_lower:
                continue
            
            # Quality filters
            if len(lemma_name) > len(word) + 5:
                continue
            if '_' in lemma_name or '-' in lemma_name:
                continue
            if lemma_name.isupper():
                continue
            if any(char.isdigit() for char in lemma_name):
                continue
            if any(rare in lemma_lower for rare in ['ae', 'oe', 'ough', 'augh']):
                continue
            
            # Formality filtering
            if formality == 'formal':
                # Prefer longer, more sophisticated words
                if len(lemma_name) < len(word) - 2:
                    continue
            elif formality == 'casual':
                # Prefer shorter, simpler words
                if len(lemma_name) > len(word) + 2:
                    continue
            
            synonyms.append((lemma_name, lemma.count(), len(lemma_name)))
    
    # Sort by formality preference
    if formality == 'formal':
        # Prefer longer words
        synonyms.sort(key=lambda x: (x[1], x[2]), reverse=True)
    elif formality == 'casual':
        # Prefer shorter words
        synonyms.sort(key=lambda x: (x[1], -x[2]), reverse=True)
    else:
        # Prefer common words
        synonyms.sort(key=lambda x: x[1], reverse=True)
    
    # Return top 5
    return [syn[0] for syn in synonyms[:5]]

def get_synonyms(word, pos):
    """Legacy function for backward compatibility."""
    return get_smart_synonyms(word, pos, "")

########################################
# Human-like Imperfections & Variations
########################################

# Safe minor imperfections (natural human patterns)
HUMAN_IMPERFECTIONS = {
    'double_spaces': ['  '],  # Occasional double space
    'comma_variations': {
        ', and': ' and',  # Remove Oxford comma sometimes
        ', or': ' or',
        ', but': ' but',
    },
    'natural_fillers': [
        'actually', 'basically', 'essentially', 'generally',
        'typically', 'usually', 'often', 'sometimes'
    ]
}

def add_natural_imperfections(sentence, p=0.15):
    """
    Add subtle, safe human imperfections that don't break meaning.
    - Occasional double spaces
    - Inconsistent Oxford comma usage
    - Natural filler words
    """
    if random.random() >= p:
        return sentence
    
    imperfection_type = random.choice(['space', 'comma', 'filler'])
    
    if imperfection_type == 'space' and random.random() < 0.3:
        # Add occasional double space (subtle)
        words = sentence.split()
        if len(words) > 5:
            pos = random.randint(1, len(words) - 2)
            words[pos] = words[pos] + ' '  # Extra space after word
            sentence = ' '.join(words)
    
    elif imperfection_type == 'comma' and random.random() < 0.4:
        # Inconsistent Oxford comma
        for with_comma, without in HUMAN_IMPERFECTIONS['comma_variations'].items():
            if with_comma in sentence and random.random() < 0.5:
                sentence = sentence.replace(with_comma, without, 1)
                break
    
    elif imperfection_type == 'filler' and random.random() < 0.3:
        # Add natural filler at sentence start
        if not sentence.split()[0].rstrip(',').lower() in ['moreover', 'however', 'therefore']:
            filler = random.choice(HUMAN_IMPERFECTIONS['natural_fillers'])
            sentence = f"{filler.capitalize()}, {sentence[0].lower()}{sentence[1:]}"
    
    return sentence

def restructure_sentence(sentence, p=0.2):
    """
    Vary sentence structure by reordering clauses or inverting subject/verb.
    Only applies safe transformations.
    """
    if random.random() >= p or not nlp:
        return sentence
    
    doc = nlp(sentence)
    
    # Skip short sentences
    if len(doc) < 6:
        return sentence
    
    # Strategy 1: Move prepositional phrase to front
    # "The system works in many cases" → "In many cases, the system works"
    for i, token in enumerate(doc):
        if token.pos_ == 'ADP' and i > 2:  # Preposition (in, on, for, etc.)
            # Find end of prepositional phrase
            phrase_end = i
            for j in range(i+1, len(doc)):
                if doc[j].pos_ in ['PUNCT', 'VERB', 'CCONJ']:
                    phrase_end = j
                    break
            
            if phrase_end > i + 1 and phrase_end < len(doc) - 2:
                # Move prepositional phrase to front
                before = doc[:i].text.strip()
                prep_phrase = doc[i:phrase_end].text.strip()
                after = doc[phrase_end:].text.strip()
                
                if before and after:
                    return f"{prep_phrase.capitalize()}, {before.lower()} {after}"
    
    return sentence

def vary_formality_within_text(sentences, p=0.15):
    """
    Introduce slight inconsistencies in formality level across sentences.
    Makes text feel more human (humans aren't perfectly consistent).
    """
    if random.random() >= p:
        return sentences
    
    formality_levels = ['formal', 'neutral', 'casual']
    current_formality = 'neutral'
    
    varied = []
    for sent in sentences:
        # Occasionally shift formality
        if random.random() < p:
            current_formality = random.choice(formality_levels)
        
        # This is more of a flag for other functions to use
        # The actual variation happens in synonym selection
        varied.append(sent)
    
    return varied

########################################
# NEW: Intelligent Sentence Combining
########################################
def detect_sentence_relationship(sent1, sent2):
    """
    Analyze the logical relationship between two sentences.
    Returns: 'addition', 'contrast', 'cause', 'none', or 'unsafe'
    """
    if not nlp:
        return 'addition'  # Safe default
    
    sent1_lower = sent1.lower()
    sent2_lower = sent2.lower()
    
    # Parse both sentences
    doc1 = nlp(sent1)
    doc2 = nlp(sent2)
    
    # NEW: Check for topic shift indicators (UNSAFE to combine)
    topic_shift_indicators = [
        'meanwhile', 'separately', 'unrelated', 'on another note',
        'switching topics', 'changing subjects', 'in other news',
        'first', 'second', 'third', 'finally', 'lastly',  # Sequential markers
        'step 1', 'step 2', 'step 3'
    ]
    
    for indicator in topic_shift_indicators:
        if indicator in sent2_lower:
            return 'unsafe'  # Don't combine
    
    # NEW: Check for subject continuity
    subject1 = get_sentence_subject(doc1)
    subject2 = get_sentence_subject(doc2)
    
    # If subjects are completely different and unrelated, be cautious
    if subject1 and subject2:
        if not are_subjects_related(subject1, subject2, sent1_lower, sent2_lower):
            return 'unsafe'  # Different topics
    
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
    first_token = doc2[0] if len(doc2) > 0 else None
    if first_token and first_token.pos_ == 'PRON' and first_token.text.lower() in ['it', 'this', 'these', 'they', 'that']:
        return 'addition'  # Clear continuation/elaboration
    
    # Check if both sentences share common nouns/entities (same topic)
    if share_common_entities(doc1, doc2):
        return 'addition'  # Same topic
    
    # If we can't determine relationship, be safe
    return 'none'  # Don't combine unless clear relationship

def get_sentence_subject(doc):
    """Extract the main subject of a sentence."""
    for token in doc:
        if token.dep_ in ["nsubj", "nsubjpass"]:
            return token.text.lower()
    return None

def are_subjects_related(subj1, subj2, sent1, sent2):
    """Check if two subjects are related enough to combine sentences."""
    
    # Same subject
    if subj1 == subj2:
        return True
    
    # Pronoun in second sentence (clear reference)
    if subj2 in ['it', 'this', 'that', 'these', 'they', 'he', 'she']:
        return True
    
    # Check if both subjects are in same domain
    # Research-related subjects
    research_subjects = ['study', 'research', 'analysis', 'experiment', 'finding', 
                        'result', 'data', 'evidence', 'investigation', 'trial']
    if subj1 in research_subjects and subj2 in research_subjects:
        return True
    
    # Tech-related subjects  
    tech_subjects = ['system', 'algorithm', 'method', 'function', 'api', 
                    'application', 'software', 'program', 'model', 'network']
    if subj1 in tech_subjects and subj2 in tech_subjects:
        return True
    
    # AI/ML subjects
    ai_subjects = ['ai', 'ml', 'model', 'network', 'algorithm', 'learning', 
                  'intelligence', 'neural', 'deep', 'machine']
    
    # Check if subjects contain AI-related terms
    if any(ai in subj1 for ai in ai_subjects) and any(ai in subj2 for ai in ai_subjects):
        return True
    
    # Otherwise, subjects seem unrelated
    return False

def share_common_entities(doc1, doc2):
    """Check if two sentences share common named entities or key nouns."""
    
    # Extract named entities
    entities1 = set([ent.text.lower() for ent in doc1.ents])
    entities2 = set([ent.text.lower() for ent in doc2.ents])
    
    # Share any entities?
    if entities1 & entities2:
        return True
    
    # Extract important nouns (not pronouns)
    nouns1 = set([token.text.lower() for token in doc1 
                  if token.pos_ in ["NOUN", "PROPN"] and token.text.lower() not in ['thing', 'way', 'time']])
    nouns2 = set([token.text.lower() for token in doc2 
                  if token.pos_ in ["NOUN", "PROPN"] and token.text.lower() not in ['thing', 'way', 'time']])
    
    # Share significant nouns?
    common_nouns = nouns1 & nouns2
    if len(common_nouns) > 0:
        return True
    
    return False

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
    Returns: (combined_sentence, success_flag)
    """
    # Get relationship
    relationship = detect_sentence_relationship(sent1, sent2)
    
    # NEW: Don't combine if unsafe or no clear relationship
    if relationship in ['unsafe', 'none']:
        return None, False  # Signal not to combine
    
    # Get appropriate connector
    connector = get_appropriate_connector(relationship)
    
    # Combine: "Sent1. Sent2" → "Sent1 and sent2"
    sent1_clean = sent1.rstrip('.!?')
    sent2_lower = sent2[0].lower() + sent2[1:] if len(sent2) > 1 else sent2.lower()
    
    combined = f"{sent1_clean} {connector} {sent2_lower}"
    
    return combined, True

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
                combined, success = combine_short_sentences(sent, next_sent)
                
                # NEW: Only combine if relationship detection succeeded
                if success and combined:
                    new_sentences.append(combined)
                    i += 2  # Skip next sentence
                else:
                    # Relationship unclear or unsafe - keep separate
                    new_sentences.append(sent)
                    i += 1
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
def minimal_humanize_line(line, prev_line=None, used_transitions=None, config=None, sentence_index=0):
    """Apply all transformations to a single line with style configuration."""
    if config is None:
        config = {}
    
    # Extract config with defaults
    p_syn = config.get('synonym_probability', 0.2)
    p_trans = config.get('transition_probability', 0.2)
    p_hedge = config.get('hedging_probability', 0.15)
    formality = config.get('synonym_formality', 'neutral')
    style = config.get('transition_style', 'general')
    expand_contr = config.get('expand_contractions', True)
    add_contr = config.get('add_contractions', False)
    
    # NEW: Human-like features
    human_imperfections = config.get('human_imperfections', False)
    style_variation = config.get('style_variation', 0.0)
    restructure_prob = config.get('sentence_restructure', 0.0)
    
    # Vary formality slightly within text (inconsistent style)
    if style_variation > 0 and random.random() < style_variation:
        formality_options = ['formal', 'neutral', 'casual']
        formality = random.choice(formality_options)
    
    # Apply transformations
    if expand_contr:
        line = expand_contractions(line)
    
    line = replace_synonyms(line, p_syn=p_syn, formality=formality)
    line = add_hedging(line, p_hedge=p_hedge)
    
    # Vary sentence structure (restructure before transition)
    if restructure_prob > 0:
        line = restructure_sentence(line, p=restructure_prob)
    
    line = add_academic_transition(line, prev_sentence=prev_line, used_transitions=used_transitions, 
                                   p_transition=p_trans, style=style)
    
    if add_contr:
        line = add_contractions(line)
    
    # Add natural human imperfections
    if human_imperfections:
        line = add_natural_imperfections(line, p=0.15)
    
    return line

def minimal_rewriting(text, config=None):
    """Rewrite text with style configuration."""
    if config is None:
        config = {}
    
    p_combine = config.get('sentence_combine_probability', 0.3)
    style_variation = config.get('style_variation', 0.0)
    
    lines = sent_tokenize(text)
    
    # Track used transitions to avoid repetition
    used_transitions = set()
    
    # Apply transformations to each sentence with context
    out_lines = []
    for i, ln in enumerate(lines):
        prev_ln = lines[i-1] if i > 0 else None
        transformed = minimal_humanize_line(
            ln, 
            prev_line=prev_ln,
            used_transitions=used_transitions,
            config=config,
            sentence_index=i
        )
        out_lines.append(transformed)
    
    # Intelligently vary sentence length
    out_lines = vary_sentence_length(out_lines, p_combine=p_combine)
    
    # Apply style variation across sentences (inconsistent style)
    if style_variation > 0:
        out_lines = vary_formality_within_text(out_lines, p=style_variation)
    
    return " ".join(out_lines)

########################################
# Main API Function
########################################
def humanize_text_minimal(text, style='balanced', **overrides):
    """
    Humanize text with style profiles and optional overrides.
    
    Args:
        text: Input text to humanize
        style: Style profile ('academic', 'formal', 'casual', 'technical', 'creative', 'balanced')
        **overrides: Override any specific parameters:
            - synonym_probability
            - transition_probability  
            - hedging_probability
            - sentence_combine_probability
            - synonym_formality
            - transition_style
            - expand_contractions
            - add_contractions
    
    Returns:
        Dictionary with original and humanized text, plus word/sentence counts
    """
    orig_wc = count_words(text)
    orig_sc = count_sentences(text)
    
    # Load style profile
    if style in STYLE_PROFILES:
        config = STYLE_PROFILES[style].copy()
    else:
        config = STYLE_PROFILES['balanced'].copy()
    
    # Apply overrides
    config.update(overrides)
    
    # Extract citations
    no_refs_text, placeholders = extract_citations(text)
    
    # Rewrite text with configuration
    partially_rewritten = minimal_rewriting(no_refs_text, config=config)
    
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
        "humanized_sentence_count": new_sc,
        "style_used": style
    }

