# KPMG GenAI Developer Assessment 

This repository contains the complete solution for the KPMG GenAI Developer Assessment Assignment, featuring two main phases:

1. **Phase 1**: Field Extraction from ביטוח לאומי (National Insurance Institute) forms using Azure Document Intelligence and OpenAI
2. **Phase 2**: Microservice-based chatbot for Israeli Health Fund (HMO) services

## Quick Start

### Prerequisites
- Python 3.8+
- Azure OpenAI credentials
- Required Python packages (see individual phase requirements)

### Repository Structure
```
KPMGass/
├── bituah_leumi_pdf_extraction/     # Phase 1: PDF Field Extraction
│   ├── src/                         # Source code
│   │   ├── run.py                   # Streamlit UI application
│   │   ├── doc_ai_hebrew.py         # Hebrew OCR processing
│   │   ├── doc_ai_english.py        # English/checkbox OCR processing
│   │   ├── gpt_field_extraction.py  # AI field extraction
│   │   └── evaluate_pdf_processing.py # Evaluation system
│   └── gold_standard/               # Gold standard test data
├── chatbot/                         # Phase 2: HMO Chatbot
│   ├── main.py                      # FastAPI backend
│   ├── frontend.py                  # Streamlit frontend
│   ├── requirements.txt             # Dependencies
│   └── services/                    # Service modules
├── phase1_data/                     # Test PDFs for Phase 1
├── phase2_data/                     # Knowledge base HTML files
└── README.md                        # This file
```

## 📄 Phase 1: PDF Field Extraction System

### Overview
An intelligent system that extracts structured information from ביטוח לאומי (National Insurance Institute) forms using OCR and Azure OpenAI.

### Features
- **Multi-language Support**: Handles forms filled in Hebrew or English
- **AI-Powered Field Extraction**: Uses GPT-4o to extract and structure form data
- **Interactive UI**: Streamlit-based interface for easy file upload and result visualization
- **Comprehensive Evaluation**: Built-in accuracy and completeness metrics

### Quick Start - Phase 1

1. **Navigate to the Phase 1 directory:**
   ```bash
   cd bituah_leumi_pdf_extraction/src
   ```

2. **Install dependencies:**
   ```bash
   pip install streamlit azure-ai-documentintelligence openai python-dotenv
   ```

3. **Set up environment variables:**
   Create a `.env` file in the `src` directory with your Azure credentials:
   ```env
   AZURE_OPENAI_API_KEY=your_api_key_here
   AZURE_OPENAI_ENDPOINT=your_endpoint_here
   AZURE_OPENAI_API_VERSION=2024-02-01
   AZURE_DOC_INTELLIGENCE_ENDPOINT=your_doc_intelligence_endpoint
   AZURE_DOC_INTELLIGENCE_KEY=your_doc_intelligence_key
   ```

4. **Run the application:**
   ```bash
   streamlit run run.py
   ```

5. **Access the web interface:**
   Open your browser to `http://localhost:8501`

### How to Use

1. **Upload PDF**: Click "Choose a PDF file" and select a ביטוח לאומי form
2. **Process**: Click "🚀 Process PDF" to start extraction
3. **View Results**: See extracted fields in three tabs:
   - **Structured View**: User-friendly display of all fields
   - **JSON View**: Raw JSON output with syntax highlighting
   - **Raw Text**: Cleaned OCR text for debugging

### Expected JSON Output Format

The system extracts the following structured data:

```json
{
  "lastName": "",
  "firstName": "",
  "idNumber": "",
  "gender": "",
  "dateOfBirth": {
    "day": "",
    "month": "",
    "year": ""
  },
  "address": {
    "street": "",
    "houseNumber": "",
    "entrance": "",
    "apartment": "",
    "city": "",
    "postalCode": "",
    "poBox": ""
  },
  "landlinePhone": "",
  "mobilePhone": "",
  "jobType": "",
  "dateOfInjury": {
    "day": "",
    "month": "",
    "year": ""
  },
  "timeOfInjury": "",
  "accidentLocation": "",
  "accidentAddress": "",
  "accidentDescription": "",
  "injuredBodyPart": "",
  "signature": "",
  "formFillingDate": {
    "day": "",
    "month": "",
    "year": ""
  },
  "formReceiptDateAtClinic": {
    "day": "",
    "month": "",
    "year": ""
  },
  "medicalInstitutionFields": {
    "healthFundMember": "",
    "natureOfAccident": "",
    "medicalDiagnoses": ""
  }
}
```

### Hebrew Field Names Translation

```json
{
  "שם משפחה": "lastName",
  "שם פרטי": "firstName",
  "מספר זהות": "idNumber",
  "מין": "gender",
  "תאריך לידה": "dateOfBirth",
  "כתובת": "address",
  "טלפון קווי": "landlinePhone",
  "טלפון נייד": "mobilePhone",
  "סוג העבודה": "jobType",
  "תאריך הפגיעה": "dateOfInjury",
  "שעת הפגיעה": "timeOfInjury",
  "מקום התאונה": "accidentLocation",
  "כתובת מקום התאונה": "accidentAddress",
  "תיאור התאונה": "accidentDescription",
  "האיבר שנפגע": "injuredBodyPart",
  "חתימה": "signature",
  "תאריך מילוי הטופס": "formFillingDate",
  "תאריך קבלת הטופס בקופה": "formReceiptDateAtClinic",
  "למילוי ע\"י המוסד הרפואי": "medicalInstitutionFields"
}
```

### Evaluation System

Run comprehensive evaluation on test files:

```bash
cd bituah_leumi_pdf_extraction/src
python evaluate_pdf_processing.py
```

The evaluation system provides:
- **Accuracy metrics** (compared to gold standard)
- **Completeness analysis** (percentage of fields extracted)
- **Detailed field-by-field comparison**
- **Performance breakdown** by accuracy ranges
- **Comprehensive reporting** with detailed mismatch analysis

**Sample Evaluation Output:**
```
📊 OVERALL EVALUATION SUMMARY
===============================
📁 Total files processed: 6
✅ Successfully processed: 6
❌ Failed processing: 0
📋 Files with gold standard: 6

📈 Average Completeness: 85.2%
📊 Average Accuracy: 78.9%

🎯 PERFORMANCE BREAKDOWN
-------------------------
Accuracy Distribution:
  Perfect (100%): 1 files (16.7%)
  Excellent (90-99%): 2 files (33.3%)
  Good (80-89%): 2 files (33.3%)
  Fair (70-79%): 1 files (16.7%)
  Poor (<70%): 0 files (0.0%)
```

## 🤖 Phase 2: Medical HMO Chatbot

### Overview
A stateless microservice-based chatbot system that provides personalized information about Israeli health fund services (Maccabi, Meuhedet, and Clalit) based on user-specific information.

### Features
- **Microservice Architecture**: FastAPI-based stateless backend
- **Two-Phase Operation**: 
  - Information Collection Phase
  - Q&A Phase with knowledge base integration
- **Multi-language Support**: Hebrew and English
- **Comprehensive Knowledge Base**: Covers dental, optometry, pregnancy, alternative medicine, and more
- **Hypothetical Query Support**: Answers questions about different HMOs and tiers
- **Smart Context Detection**: Identifies relevant services from user queries
- **Stateless Design**: All conversation context managed client-side

### Quick Start - Phase 2

1. **Navigate to the chatbot directory:**
   ```bash
   cd chatbot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file with your Azure OpenAI credentials:
   ```env
   AZURE_OPENAI_API_KEY=your_api_key_here
   AZURE_OPENAI_ENDPOINT=your_endpoint_here
   AZURE_OPENAI_API_VERSION=2024-02-01
   ```

4. **Start the backend server:**
   ```bash
   python main.py
   ```
   The API will be available at `http://localhost:8000`

5. **Start the frontend (in a new terminal):**
   ```bash
   streamlit run frontend.py
   ```
   Access the chatbot at `http://localhost:8501`

### How to Use the Chatbot

#### Phase 1: Information Collection
The chatbot will collect the following information:

1. **Personal Information:**
   - First and last name
   - ID number (9-digit validation)
   - Gender (זכר/נקבה/אחר)
   - Age (0-120 validation)

2. **HMO Information:**
   - HMO name (מכבי/מאוחדת/כללית)
   - HMO card number (9-digit validation)
   - Insurance tier (זהב/כסף/ארד)

#### Phase 2: Q&A
Once information is collected, you can ask questions about:
- Health services and benefits
- Coverage details for your specific HMO and tier
- Comparison between different HMOs or tiers
- Specific services like dental, pregnancy, optometry

**Example Questions:**
- "מה מגיע לי בתחום הריון?" (What pregnancy benefits do I get?)
- "איך השירותים של מכבי זהב בהשוואה לכללית?" (How do Maccabi Gold services compare to Clalit?)
- "מה לגבי טיפולי שיניים?" (What about dental treatments?)

### API Endpoints`

#### Main Chat Endpoint
```http
POST /chat
```

**Request Body:**
```json
{
  "message": "שלום, אני רוצה לדעת מה מגיע לי",
  "user_info": {
    "first_name": "יוסי",
    "last_name": "כהן",
    "id_number": "123456789",
    "gender": "זכר",
    "age": 30,
    "hmo_name": "מכבי",
    "hmo_card_number": "987654321",
    "insurance_tier": "זהב"
  },
  "conversation_history": [
    {
      "role": "user",
      "content": "שלום",
      "timestamp": "2025-05-31T10:00:00"
    }
  ],
  "phase": "qa",
  "language": "hebrew"
}
```

**Response:**
```json
{
  "response": "על פי מאגר הידע, הנה המידע עבור מכבי זהב...",
  "updated_user_info": { /* updated user info */ },
  "phase": "qa",
  "is_complete": true
}
```

#### Debug Endpoints
```http
GET /debug/knowledge    # Check knowledge base status
GET /debug/simple       # Simple pregnancy data test
GET /test              # Enhanced version test
```

### Knowledge Base Services

The chatbot provides information about:

1. **Dental Services** (`dentel_services.html`)
   - Dental treatments and coverage
   - Preventive care
   - Cosmetic dentistry

2. **Optometry Services** (`optometry_services.html`)
   - Eye exams and vision care
   - Glasses and contact lenses
   - Laser treatments

3. **Pregnancy Services** (`pragrency_services.html`)
   - Prenatal care
   - Delivery benefits
   - Genetic screening

4. **Alternative Medicine** (`alternative_services.html`)
   - Acupuncture
   - Homeopathy
   - Naturopathy

5. **Communication Clinic** (`communication_clinic_services.html`)
   - Speech therapy
   - Language disorders

6. **Workshops & Community** (`workshops_services.html`)
   - Health education
   - Community programs

## 🛠️ Technical Architecture

### Phase 1 Architecture
```
PDF Upload → Azure Document Intelligence (OCR) → Text Cleaning → 
GPT-4o Field Extraction → JSON Output → Validation & Evaluation
```

**Key Components:**
- `doc_ai_hebrew.py`: Hebrew text OCR processing with layout analysis
- `doc_ai_english.py`: English OCR processing for form fields
- `gpt_field_extraction.py`: AI-powered field extraction using GPT-4o
- `run.py`: Streamlit UI application with three-tab result display
- `evaluate_pdf_processing.py`: Comprehensive evaluation with gold standard comparison

**OCR Strategy:**
1. **Hybrid Decision**: Automatically switches based on content type (hebrew\english) (ASCII detection)
2. **Text Cleaning**: Removes noise and formats for GPT processing

### Phase 2 Architecture
```
Frontend (Streamlit) ↔ FastAPI Backend ↔ Azure OpenAI ↔ Knowledge Base (HTML Files)
```

**Key Components:**
- `main.py`: FastAPI microservice backend with comprehensive logging
- `frontend.py`: Streamlit user interface with conversation management
- `services/html_parser.py`: Knowledge base processing and structured data extraction
- HTML files: Structured knowledge base with tier-specific information

**Backend Features:**
- **Stateless Design**: No server-side session storage
- **Smart Query Detection**: Identifies hypothetical and comparison queries
- **Context Management**: Comprehensive knowledge base context generation
- **Multi-language Processing**: Bilingual prompt engineering
- **Service Detection**: Automatic identification of relevant services


### Environment Variables

**Phase 1 (.env in `bituah_leumi_pdf_extraction/src/`):**
```env
AZURE_OPENAI_API_KEY=your_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_DOC_INTELLIGENCE_ENDPOINT=https://your-doc-intelligence.cognitiveservices.azure.com/
AZURE_DOC_INTELLIGENCE_KEY=your_doc_intelligence_key
```

**Phase 2 (.env in `chatbot/`):**
```env
AZURE_OPENAI_API_KEY=your_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
```

