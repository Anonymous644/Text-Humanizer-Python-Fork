# Text Humanizer & AI Detection API

A FastAPI-based backend service for humanizing AI-generated text and detecting AI content.

## Features

### 🔍 AI Detection API

- Analyzes text to detect AI-generated content
- Classifies each sentence as:
  - AI-generated
  - AI-generated & AI-refined
  - Human-written
  - Human-written & AI-refined
- Returns detailed percentages and classification results
- Uses `roberta-base-openai-detector` model

### ✍️ Text Humanizer API

- Humanizes AI-generated text while preserving APA citations
- Expands contractions naturally
- Replaces words with contextual synonyms
- Adds academic transitions
- Configurable transformation probabilities

## Installation

### Prerequisites

- Python 3.9+
- pip

### Setup

1. **Clone the repository:**

```bash
git clone <repository-url>
cd Text-Humanizer-Python-Fork
```

2. **Create a virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m nltk.downloader punkt punkt_tab wordnet averaged_perceptron_tagger
```

4. **Run the API:**

```bash
uvicorn main:app --reload
```

The API will be available at: **http://localhost:8000**

## API Endpoints

### `POST /humanize`

Humanize AI-generated text while preserving citations.

**Request Body:**

```json
{
  "text": "Your AI-generated text here...",
  "synonym_probability": 0.2,
  "transition_probability": 0.2
}
```

**Response:**

```json
{
  "original_text": "...",
  "humanized_text": "...",
  "original_word_count": 150,
  "humanized_word_count": 165,
  "original_sentence_count": 8,
  "humanized_sentence_count": 8
}
```

### `POST /detect`

Detect AI-generated content in text.

**Request Body:**

```json
{
  "text": "Your text to analyze..."
}
```

**Response:**

```json
{
  "text": "...",
  "classification_results": {
    "First sentence.": "AI-generated",
    "Second sentence.": "Human-written"
  },
  "percentages": {
    "AI-generated": 45.5,
    "AI-generated & AI-refined": 10.2,
    "Human-written": 30.1,
    "Human-written & AI-refined": 14.2
  },
  "summary": { ... }
}
```

### `GET /`

Root endpoint with API information.

### `GET /health`

Health check endpoint.

### `GET /docs`

Interactive API documentation (Swagger UI).

## Usage Examples

### Using cURL

**Humanize Text:**

```bash
curl -X POST "http://localhost:8000/humanize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "AI is transforming industries. It is creating new opportunities.",
    "synonym_probability": 0.3,
    "transition_probability": 0.2
  }'
```

**Detect AI:**

```bash
curl -X POST "http://localhost:8000/detect" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The research methodology employed a quantitative approach."
  }'
```

### Using Python

```python
import requests

# Humanize text
response = requests.post(
    "http://localhost:8000/humanize",
    json={
        "text": "Your AI text here...",
        "synonym_probability": 0.2,
        "transition_probability": 0.2
    }
)
result = response.json()
print(result['humanized_text'])

# Detect AI
response = requests.post(
    "http://localhost:8000/detect",
    json={"text": "Text to analyze..."}
)
result = response.json()
print(result['percentages'])
```

### Using JavaScript/Fetch

```javascript
// Humanize text
fetch("http://localhost:8000/humanize", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    text: "Your AI text here...",
    synonym_probability: 0.2,
    transition_probability: 0.2,
  }),
})
  .then((res) => res.json())
  .then((data) => console.log(data));

// Detect AI
fetch("http://localhost:8000/detect", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    text: "Text to analyze...",
  }),
})
  .then((res) => res.json())
  .then((data) => console.log(data));
```

## Testing

Run the test script to verify everything works:

```bash
python test_api.py
```

Or visit the interactive documentation at: **http://localhost:8000/docs**

## Project Structure

```
Text-Humanizer-Python-Fork/
├── main.py                    # FastAPI application
├── utils/
│   ├── __init__.py
│   ├── ai_detection_utils.py  # AI detection logic
│   ├── model_loaders.py       # Model caching
│   └── text_humanizer.py      # Text humanization logic
├── requirements.txt           # Python dependencies
├── test_api.py                # Test script
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

## Technologies

- **FastAPI** - Modern web framework for building APIs
- **Transformers** - HuggingFace library for AI models
- **spaCy** - Industrial-strength NLP
- **NLTK** - Natural Language Toolkit
- **PyTorch** - Deep learning framework
- **Uvicorn** - ASGI server

## API Parameters

### Humanize Endpoint

| Parameter                | Type   | Default  | Range   | Description                                  |
| ------------------------ | ------ | -------- | ------- | -------------------------------------------- |
| `text`                   | string | required | -       | Text to humanize                             |
| `synonym_probability`    | float  | 0.2      | 0.0-1.0 | Probability of replacing words with synonyms |
| `transition_probability` | float  | 0.2      | 0.0-1.0 | Probability of adding academic transitions   |

### Detect Endpoint

| Parameter | Type   | Default  | Description                      |
| --------- | ------ | -------- | -------------------------------- |
| `text`    | string | required | Text to analyze for AI detection |

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
