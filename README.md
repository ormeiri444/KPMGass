# KPMG GenAI Developer Assessment Assignment

<p align="center">
  <img src="https://github.com/user-attachments/assets/ed5b23ba-3e7e-46fd-a18c-8fcc520bee52" alt="kpmg-logo-1" width="200" />
</p>

This repository contains the complete solution for the KPMG GenAI Developer Assessment Assignment, featuring two main phases:

1. **Phase 1**: Field Extraction from ביטוח לאומי (National Insurance Institute) forms using Azure Document Intelligence and OpenAI
2. **Phase 2**: Microservice-based chatbot for Israeli Health Fund (HMO) services

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Azure OpenAI credentials (provided in the assignment email)
- Required Python packages (see individual phase requirements)

### Repository Structure
```
KPMGass/
├── bituah_leumi_pdf_extraction/     # Phase 1: PDF Field Extraction
├── chatbot/                         # Phase 2: HMO Chatbot
├── phase1_data/                     # Test data for Phase 1
├── phase2_data/                     # Knowledge base for Phase 2
└── README.md                        # This file
```

## 📄 Phase 1: PDF Field Extraction System

### Overview
An intelligent system that extracts structured information from ביטוח לאומי (National Insurance Institute) forms using OCR and Azure OpenAI.

### Features
- **Hybrid OCR Processing**: Utilizes both regular and checkbox-specific OCR modes for optimal accuracy
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

### Expected JSON Output Format
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

### Evaluation System
Run the comprehensive evaluation on test files:
```bash
cd bituah_leumi_pdf_extraction/src
python evaluate_pdf_processing.py
```

The evaluation system provides:
- **Accuracy metrics** (compared to gold standard)
- **Completeness analysis** (percentage of fields extracted)
- **Detailed field-by-field comparison**
- **Performance breakdown** by accuracy ranges

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

### API Endpoints

#### Health Check
```
GET /health
```

#### Main Chat Endpoint
```
POST /chat
```

**Request Body:**
```json
{
  "message": "user message",
  "user_info": {
    "first_name": "string",
    "last_name": "string",
    "id_number": "123456789",
    "gender": "זכר/נקבה/אחר",
    "age": 30,
    "hmo_name": "מכבי/מאוחדת/כללית",
    "hmo_card_number": "123456789",
    "insurance_tier": "זהב/כסף/ארד"
  },
  "conversation_history": [],
  "phase": "collection/qa",
  "language": "hebrew/english"
}
```

#### Debug Endpoints
```
GET /debug/knowledge  # Check knowledge base status
GET /debug/simple     # Simple pregnancy data test
```

### User Information Collection
The system collects the following information:
- First and last name
- ID number (9-digit validation)
- Gender
- Age (0-120 validation)
- HMO name (מכבי | מאוחדת | כללית)
- HMO card number (9-digit validation)
- Insurance membership tier (זהב | כסף | ארד)

### Knowledge Base Services
The chatbot provides information about:
- **Dental Services** (`dentel_services.html`)
- **Optometry Services** (`optometry_services.html`)
- **Pregnancy Services** (`pragrency_services.html`)
- **Alternative Medicine** (`alternative_services.html`)
- **Communication Clinic** (`communication_clinic_services.html`)
- **Workshops & Community** (`workshops_services.html`)

## 🛠️ Technical Architecture

### Phase 1 Architecture
```
PDF Upload → Azure Document Intelligence (OCR) → Text Cleaning → 
GPT-4o Field Extraction → JSON Output → Validation & Evaluation
```

**Key Components:**
- `doc_ai_hebrew.py`: Hebrew text OCR processing
- `doc_ai_english.py`: English/checkbox OCR processing
- `gpt_field_extraction.py`: AI-powered field extraction
- `run.py`: Streamlit UI application
- `evaluate_pdf_processing.py`: Comprehensive evaluation system

### Phase 2 Architecture
```
Frontend (Streamlit) ↔ FastAPI Backend ↔ Azure OpenAI ↔ Knowledge Base (HTML Files)
```

**Key Components:**
- `main.py`: FastAPI microservice backend
- `frontend.py`: Streamlit user interface
- `services/html_parser.py`: Knowledge base processing
- HTML files: Structured knowledge base

## 📊 Performance Metrics

### Phase 1 Evaluation
The system achieves:
- **High Accuracy**: Measured against gold standard annotations
- **Robust Completeness**: Extracts data from most form fields
- **Multi-language Support**: Handles both Hebrew and English forms
- **Hybrid OCR Approach**: Optimizes extraction based on content type

### Phase 2 Features
- **Stateless Design**: No server-side memory, all context in requests
- **Comprehensive Coverage**: All major HMO services included
- **Smart Query Understanding**: Detects hypothetical and comparison queries
- **Bilingual Support**: Full Hebrew and English functionality

## 🔧 Configuration

### Azure Resources Required
- **Azure OpenAI**: GPT-4o and GPT-4o Mini models
- **Document Intelligence**: For OCR processing
- **ADA 002**: For text embeddings (if needed)

### Environment Variables
Both phases require Azure OpenAI credentials:
```env
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_DOC_INTELLIGENCE_ENDPOINT=your_doc_intelligence_endpoint  # Phase 1 only
AZURE_DOC_INTELLIGENCE_KEY=your_doc_intelligence_key            # Phase 1 only
```

## 🧪 Testing

### Phase 1 Testing
```bash
cd bituah_leumi_pdf_extraction/src
python evaluate_pdf_processing.py
```

### Phase 2 Testing
```bash
cd chatbot
# Test API health
curl http://localhost:8000/health

# Test knowledge base
curl http://localhost:8000/debug/knowledge
```

## 📝 Logging and Monitoring

### Phase 1
- Detailed processing logs in console output
- Evaluation results saved to JSON files
- Error handling with specific error messages

### Phase 2
- Comprehensive logging to `chatbot.log`
- API request/response logging
- Knowledge base loading status
- Error tracking and debugging information

## 🚀 Deployment Notes

### Production Considerations
1. **Environment Variables**: Secure credential management
2. **Scaling**: FastAPI supports horizontal scaling
3. **Monitoring**: Built-in logging for production monitoring
4. **Error Handling**: Comprehensive error handling and validation

### Docker Support
Both phases can be containerized for deployment:
```dockerfile
# Example for Phase 2
FROM python:3.9-slim
WORKDIR /app
COPY chatbot/requirements.txt .
RUN pip install -r requirements.txt
COPY chatbot/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📚 Documentation

### API Documentation
When running Phase 2, automatic API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Code Documentation
- Comprehensive docstrings throughout
- Type hints for better IDE support
- Inline comments for complex logic

## ⚠️ Known Limitations

### Phase 1
- Performance depends on PDF quality and format consistency
- Some complex layouts may require manual review
- Handwritten text recognition limitations

### Phase 2
- Knowledge base limited to provided HTML files
- No persistent user sessions (by design)
- Rate limiting not implemented (consider for production)

## 🤝 Contributing

This is an assessment project. For questions or clarifications, contact:
**Dor Getter**

## 📄 License

This project is part of the KPMG GenAI Developer Assessment Assignment.

---

**Project completed by:** Or Meiri  
**Assessment Duration:** 4 days  
**Technologies Used:** Azure OpenAI, Document Intelligence, FastAPI, Streamlit, Python 3.9+