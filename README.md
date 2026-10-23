# Lexium Mobile
> A neurosymbolic AI-powered legal advisory application for Sri Lanka.

**Repository:** https://github.com/DhyanMohottie/Lexium

---

## Overview

Access to legal counsel remains a significant challenge for the 
general public in Sri Lanka. Lexium addresses this by providing 
AI-generated legal advisory responses through a Flutter mobile 
application, with a key differentiator — every response is 
validated by a neurosymbolic pipeline before being shown to the user.

The validation pipeline operates as follows:
- A **Heterogeneous Graph Attention Network (HeteroGAT)** trained 
  on 3,059 labelled legal claims extracted from 540 Sri Lankan court
  case files, linked to 534 statutes and 274 sections across ten 
  edge types.
- A **symbolic reasoning engine** evaluates the response against 
  10 weighted rules (citation validity, legal language, statute 
  specificity, etc.)
- A **fusion network** combines both scores into a single fused 
  confidence score
- If the score falls below 0.70, the system silently re-prompts 
  the LLM and retries up to 3 times
- The final response is returned to the user with a colour-coded 
  confidence indicator —  green (≥70%),  orange (≥50%), 
   red (<50%)

---

## Stack

| Layer | Tech |
|---|---|
| Mobile app | Flutter |
| Auth backend | Node.js + Express.js + MongoDB Atlas |
| AI backend | Python + Flask |
| LLM | OpenAI API (configurable via .env) |
| GNN | PyTorch + PyTorch Geometric (HeteroGAT) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |

---

## System Architecture
```
Flutter Mobile App
↓
Node.js / Express.js Backend (MongoDB Atlas)
↓
Flask REST API (/chat endpoint)
↓
SelfCorrectionController
↓
LLM → generates advisory response
↓
Neurosymbolic Validation Pipeline
├── HeteroGAT GNN     → legal validity score
├── Symbolic Engine   → 10 weighted rules + fuzzy statute matching
└── Fusion Network    → fused confidence score
↓
Score ≥ 0.70? → Return to user
Score < 0.70? → Re-prompt LLM (max 3 retries) → Return best response
```

![System Architecture](images/system_architecture.png)

---


## Flow Diagram

![Flow Diagram](images/flow_diagram.png)

---

## Project Layout
```
Lexora/
├── lexium_mobile/          # Flutter mobile app
├── express_backend/        # Auth server (Node.js)
└── lexium_mobile_backend/  # AI pipeline (Flask)
    ├── models/             # Trained model weights (not in git)
    └── data/               # Knowledge base CSVs (not in git)
```

---


## Prerequisites

- Python 3.8 or higher
- pip
- Node.js 18 or higher
- npm
- Flutter SDK
- Android Emulator or Physical Device
- MongoDB Atlas account
- OpenAI API key

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/DhyanMohottie/Lexium
cd Lexium
```

### 2. Set Up Flask AI Backend

```bash
cd lexium_mobile_backend
```

Create a virtual environment:

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4o              # or any OpenAI model
CORRECTION_THRESHOLD=0.70     # minimum confidence to accept
MAX_RETRIES=3                 # maximum re-prompt attempts
PORT=8080
DEBUG=false
```

Run the Flask server:
```bash
python app.py
```

```
Expected output:
============================================================
NEUROSYMBOLIC LEGAL AI - Starting up...
✅ GNN model loaded — 10 edge types
✅ Symbolic engine ready — 10 rules
✅ Fusion network loaded
All systems ready!
```

Health check:
```bash
curl http://localhost:8080/health
```

### 3. Set Up Express.js Auth Backend

```bash
cd ../express_backend
npm install
```

Create a `.env` file:
```env
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/lexium
JWT_SECRET=your_jwt_secret
JWT_EXPIRES_IN=7d
PORT=3000
```

Generate a secure JWT secret:
```bash
node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"
```

Run the server:
```bash
npm run dev
```

```
Expected output:
Server running on port 3000
MongoDB connected successfully
```

### 4. Set Up Flutter App

```bash
cd ../lexium_mobile
flutter pub get
flutter run
```

---

## Testing

### GNN Component

```bash
python test_gnn.py
```

```
✅ Model loaded — 10 edge types
Node types: ['document', 'statute', 'section', 'claim']
Overall Score: 74.1%
```

To test with custom input, open `test_gnn.py` and change the 
claim string:
```python
# Replace with any sentence to see how the GNN scores it
claim = "The defendant violated Section 2 of the Service Contracts Ordinance"
```

### Symbolic Reasoning Engine

```bash
python test_real_data.py
```

```
Test 1: The defendant violated Section 2 of the Service Contracts Ordinance
Score: 70.0% | Valid: True | Passed: 7/10 rules
Test 2: The plaintiff's claim under the Bribery Act and Section 10 is well-founded
Score: 90.0% | Valid: True | Passed: 9/10 rules
Test 3: Based on the Animals Act and Section 4, the court must rule in favor
Score: 90.0% | Valid: True | Passed: 9/10 rules
```

### Full Chat Pipeline

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What are my rights if my employer does not pay me?"}'
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | System status — GNN, symbolic, fusion, LLM |
| `/chat` | POST | Full pipeline — LLM + validation + self-correction |
| `/validate` | POST | Validate a single claim directly (no LLM) |
| `/validate/batch` | POST | Validate multiple claims |

---

## Neurosymbolic Components

### HeteroGAT GNN
- Trained on 3,059 Sri Lankan legal claims from AsianLII, 
  LankaLaw, and the Court of Appeal
- Four node types: claims, documents, statutes, sections
- Ten edge types (forward, reverse, self-loop)
- Test MAE: 0.1274 — 1.6× better than the naive baseline

### Symbolic Reasoning Engine
Ten weighted rules evaluated against each LLM response:

| Rule | Weight |
|---|---|
| has_legal_reference | 0.25 |
| reference_is_valid | 0.20 |
| actionable_language | 0.15 |
| specific_enough | 0.12 |
| legal_context | 0.12 |
| minimum_length | 0.06 |
| not_gibberish | 0.05 |
| logical_consistency | 0.03 |
| no_unknown_citations | 0.01 |
| coherent_reference | 0.01 |

Statute names are matched against `statutes.csv` and `sections.csv` 
at runtime using a five-tier fuzzy matching system that handles 
abbreviations, formatting variations, and partial matches.

### Fusion Network
- Input: GNN score, symbolic confidence, rules satisfied, 
  rules violated
- Architecture: Input(4) → Dense(64) → ReLU → BatchNorm → 
  Dropout(0.3) → Dense(32) → ReLU → BatchNorm → Dropout(0.2) → 
  Dense(1) → Sigmoid
- Trained with MAE loss over 300 epochs
- Best validation MAE: 0.1566 | Correlation with ground truth: 0.616

### Self-Correction Loop
- Acceptance threshold: 0.70
- Maximum retries: 3
- Feedback is derived from violated symbolic rules — not from 
  the GNN score, which provides no interpretable signal for 
  re-prompting
- The highest-scoring response across all attempts is returned

---

## Dependencies

### Flask Backend
```
torch==2.2.2
torch-geometric==2.7.0
torch-scatter>=2.1.0
torch-sparse>=0.6.18
sentence-transformers==5.2.0
transformers>=4.30.0
numpy==2.4.1
pandas==2.3.3
scikit-learn>=1.3.0
Flask>=3.0.0
Flask-CORS>=4.0.0
Flask-JWT-Extended>=4.5.0
openai>=1.0.0
python-dotenv>=1.0.0
tqdm>=4.66.0
```

### Express.js Backend
```json
{
  "dependencies": {
    "bcryptjs": "^2.4.3",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1",
    "express": "^4.18.2",
    "jsonwebtoken": "^9.0.2",
    "mongoose": "^8.0.3"
  }
}
```

### Flutter
```yaml
dependencies:
  http: ^1.2.0
  shared_preferences: ^2.2.2
  provider: ^6.1.1
  font_awesome_flutter: any
```

---

## Known Issues

**MongoDB Atlas DNS error (`querySrv ENOTFOUND`)**  
Some ISPs block MongoDB Atlas hostnames. Set your DNS to 
`8.8.8.8` / `8.8.4.4` or enable Cloudflare WARP.

**GNN standalone inference returns constant scores (~0.49)**  
Expected behaviour. The GNN was trained using full-graph 
transductive evaluation. Individual claim inference without 
the full graph context produces near-constant scores. 
Always use the `/chat` endpoint for accurate results.

**Fusion network fails to load (`hidden_dim` mismatch)**  
The saved `fusion_network.pt` uses `hidden_dim=64`. 
If you retrain with a different hidden dimension the checkpoint 
will fail to load. Verify with `ckpt['hidden_dim']` before loading.

---

## Author

**Gunathilake N.P**