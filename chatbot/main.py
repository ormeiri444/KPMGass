from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import List, Dict, Optional, Literal
import logging
import os
from datetime import datetime
import json
from openai import AzureOpenAI
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Try to import BeautifulSoup, handle if not installed
try:
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"ERROR: BeautifulSoup4 is not installed. Please install it with: pip install beautifulsoup4")
    print(f"Import error: {e}")
    raise ImportError("BeautifulSoup4 is required but not installed")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Medical HMO Chatbot",
              description="Enhanced chatbot for Israeli health funds with full knowledge base")

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Knowledge base storage
knowledge_base = {}


def load_knowledge_base():
    """Load all HTML files into memory as knowledge base"""
    global knowledge_base

    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_directory = os.path.join(os.path.dirname(current_dir), "phase2_data")

    print(f"📂 Loading knowledge base from: {data_directory}")
    print(f"📁 Directory exists: {os.path.exists(data_directory)}")

    if os.path.exists(data_directory):
        files_in_dir = os.listdir(data_directory)
        print(f"📄 Files in directory: {files_in_dir}")
    else:
        print(f"❌ ERROR: Directory does not exist!")
        return

    service_files = {
        'dental': 'dentel_services.html',
        'optometry': 'optometry_services.html',
        'pregnancy': 'pragrency_services.html',
        'alternative': 'alternative_services.html',
        'communication_clinic': 'communication_clinic_services.html',
        'workshops': 'workshops_services.html'
    }

    for service_type, filename in service_files.items():
        file_path = os.path.join(data_directory, filename)
        print(f"🔍 Trying to load: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                knowledge_base[service_type] = {
                    'raw_html': content,
                    'clean_text': clean_html_content(content),
                    'structured_data': extract_structured_data(content)
                }
            print(f"✅ Loaded {service_type} - {len(content)} chars")
            print(f"   Title: {knowledge_base[service_type]['structured_data']['title']}")
        except Exception as e:
            print(f"❌ Failed to load {filename}: {e}")

    print(f"🏁 Knowledge base loaded with {len(knowledge_base)} services: {list(knowledge_base.keys())}")

    # Test pregnancy specifically
    if 'pregnancy' in knowledge_base:
        pregnancy_data = knowledge_base['pregnancy']['structured_data']
        print(f"🤰 Pregnancy data loaded:")
        print(f"   Title: {pregnancy_data['title']}")
        print(f"   Services: {len(pregnancy_data['services'])}")
        if pregnancy_data['services']:
            print(f"   First service: {pregnancy_data['services'][0]['service_name']}")
    else:
        print(f"❌ Pregnancy data NOT loaded!")


def clean_html_content(html_content):
    """Clean HTML content and extract structured text"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove any script or style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text content
    text = soup.get_text()

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)

    return text


def extract_structured_data(html_content):
    """Extract structured data from HTML for better processing"""
    soup = BeautifulSoup(html_content, 'html.parser')

    structured_data = {
        'title': '',
        'description': '',
        'services': [],
        'contact_info': {}
    }

    # Extract title
    title = soup.find('h2')
    if title:
        structured_data['title'] = title.get_text().strip()

    # Extract description (first paragraph)
    first_p = soup.find('p')
    if first_p:
        structured_data['description'] = first_p.get_text().strip()

    # Extract table data
    table = soup.find('table')
    if table:
        rows = table.find_all('tr')
        for row in rows[1:]:  # Skip header row
            cells = row.find_all('td')
            if len(cells) >= 4:
                service_data = {
                    'service_name': cells[0].get_text().strip(),
                    'maccabi': parse_tier_benefits(cells[1].get_text().strip()),
                    'meuhedet': parse_tier_benefits(cells[2].get_text().strip()),
                    'clalit': parse_tier_benefits(cells[3].get_text().strip())
                }
                structured_data['services'].append(service_data)

    # Extract contact information
    contact_section = soup.find('h3', string='מספרי טלפון לשירות לקוחות:')
    if contact_section:
        contact_list = contact_section.find_next('ul')
        if contact_list:
            for li in contact_list.find_all('li'):
                text = li.get_text().strip()
                if 'מכבי:' in text:
                    structured_data['contact_info']['maccabi'] = text
                elif 'מאוחדת:' in text:
                    structured_data['contact_info']['meuhedet'] = text
                elif 'כללית:' in text:
                    structured_data['contact_info']['clalit'] = text

    return structured_data


def parse_tier_benefits(benefits_text):
    """Parse tier benefits from text"""
    tiers = {}
    lines = benefits_text.split('\n')
    current_tier = None

    for line in lines:
        line = line.strip()
        if line.startswith('זהב:'):
            current_tier = 'זהב'
            tiers[current_tier] = line.replace('זהב:', '').strip()
        elif line.startswith('כסף:'):
            current_tier = 'כסף'
            tiers[current_tier] = line.replace('כסף:', '').strip()
        elif line.startswith('ארד:'):
            current_tier = 'ארד'
            tiers[current_tier] = line.replace('ארד:', '').strip()
        elif current_tier and line:
            # Continue previous tier description
            tiers[current_tier] += ' ' + line

    return tiers

def detect_hypothetical_query(user_message: str) -> Dict[str, Optional[str]]:
    """Detect if user is asking about different HMOs or tiers than their own"""
    message_lower = user_message.lower()

    # HMO detection - ENHANCED with English support
    detected_hmos = []

    # Hebrew HMO detection
    if any(word in message_lower for word in ['מכבי', 'maccabi']):
        detected_hmos.append('מכבי')
    if any(word in message_lower for word in ['מאוחדת', 'meuhedet']):
        detected_hmos.append('מאוחדת')
    if any(word in message_lower for word in ['כללית', 'clalit']):
        detected_hmos.append('כללית')

    # Tier detection - ENHANCED with English support
    detected_tiers = []

    # Hebrew and English tier detection
    if any(word in message_lower for word in ['זהב', 'gold']):
        detected_tiers.append('זהב')
    if any(word in message_lower for word in ['כסף', 'silver']):
        detected_tiers.append('כסף')
    if any(word in message_lower for word in ['ארד', 'bronze']):
        detected_tiers.append('ארד')

    # **ENHANCED: Better comparison and hypothetical indicators - BILINGUAL**
    comparison_phrases = [
        # Hebrew phrases
        'השווה', 'השוואה', 'לעומת', 'נגד', 'מול', 'בהשוואה ל',
        'מה ההבדל', 'איך שונה', 'מה יותר טוב', 'איזה עדיף',
        'מה לגבי', 'ואם הייתי', 'אם הייתי ב', 'לו הייתי',
        'במקום', 'אילו הייתי', 'אם אני עוברת ל', 'אם אעבור ל',
        # English phrases
        'compare', 'comparison', 'versus', 'vs', 'against', 'compared to',
        'what is the difference', 'how different', 'what is better', 'which is better',
        'what about', 'what if i', 'if i was', 'if i were', 'suppose i',
        'instead of', 'if i had', 'if i switch to', 'if i move to',
        'rather than', 'as opposed to', 'in contrast to'
    ]

    is_comparison = any(phrase in message_lower for phrase in comparison_phrases)

    # Multiple HMO/tier indicators - now based on actual detection
    multiple_hmos = len(detected_hmos) > 1
    multiple_tiers = len(detected_tiers) > 1

    # **NEW: Detect if this is a follow-up hypothetical question - BILINGUAL**
    is_followup_hypothetical = any(phrase in message_lower for phrase in [
        # Hebrew
        'מה לגבי', 'ואם', 'אם הייתי', 'לו הייתי', 'במקום', 'אילו',
        # English
        'what about', 'what if', 'if i was', 'if i were', 'suppose', 'instead'
    ])

    return {
        'hmo': detected_hmos[0] if len(detected_hmos) == 1 else None,
        'hmos': detected_hmos,
        'tier': detected_tiers[0] if len(detected_tiers) == 1 else None,
        'tiers': detected_tiers,
        'is_comparison': is_comparison,
        'multiple_hmos': multiple_hmos,
        'multiple_tiers': multiple_tiers,
        'is_followup_hypothetical': is_followup_hypothetical
    }

def get_comprehensive_knowledge_context(user_message: str, user_info, hypothetical_context: Dict) -> str:
    """Get comprehensive knowledge base context for detailed answers"""
    logger.info(f"🔍 Starting get_comprehensive_knowledge_context")
    logger.info(f"👤 User info: HMO={user_info.hmo_name}, Tier={user_info.insurance_tier}")
    logger.info(f"🤔 Hypothetical context: {hypothetical_context}")

    # **FIXED: Check if hypothetical context exists - if so, grab ALL knowledge base**
    should_load_all_services = (
        hypothetical_context.get('is_comparison') or
        hypothetical_context.get('multiple_hmos') or
        hypothetical_context.get('multiple_tiers') or
        hypothetical_context.get('is_followup_hypothetical') or
        hypothetical_context.get('hmo') or  # ANY HMO mentioned
        hypothetical_context.get('tier') or  # ANY tier mentioned
        bool(hypothetical_context.get('hmos')) or  # Non-empty HMO list
        bool(hypothetical_context.get('tiers'))    # Non-empty tier list
    )

    if should_load_all_services:
        logger.info("🌐 Hypothetical/general context detected - loading ALL knowledge base")
        relevant_services = list(knowledge_base.keys())  # Get ALL services
        logger.info(f"📋 Using ALL services: {relevant_services}")
    else:
        # Original behavior - identify specific relevant services
        relevant_services = identify_relevant_services(user_message)
        logger.info(f"📋 Identified relevant services: {relevant_services}")

        # **FALLBACK: If no services found but knowledge base exists, load all**
        if not relevant_services and knowledge_base:
            logger.info("⚠️ No relevant services found - loading ALL as fallback")
            relevant_services = list(knowledge_base.keys())

    # **DEBUG: Add more logging**
    logger.info(f"🎯 Final relevant services: {relevant_services}")
    logger.info(f"📚 Available services in knowledge base: {list(knowledge_base.keys())}")

    context_parts = []

    # Add comprehensive context for each relevant service
    for service in relevant_services:
        logger.info(f"🔄 Processing service: {service}")
        if service in knowledge_base:
            service_data = knowledge_base[service]
            logger.info(f"✅ Found {service} in knowledge base")

            # Add service title and description
            title = service_data['structured_data']['title']
            description = service_data['structured_data']['description']

            context_parts.append(f"\n\n=== {title} ===")
            context_parts.append(f"תיאור: {description}")

            # **ENHANCED: Better logic for determining which HMOs and tiers to include**
            target_hmos = []
            target_tiers = []

            # Priority 1: Explicit hypothetical query (e.g., "מה לגבי אם הייתי במכבי?")
            if hypothetical_context.get('is_followup_hypothetical') and hypothetical_context['hmo']:
                target_hmos = [hypothetical_context['hmo']]
                logger.info(f"🎯 Follow-up hypothetical detected - using: {hypothetical_context['hmo']}")
            # Priority 2: Specific HMO mentioned in query like "פרטים לגבי מאוחדת"
            elif hypothetical_context.get('hmo'):
                target_hmos = [hypothetical_context['hmo']]
                logger.info(f"🎯 Including specific HMO: {hypothetical_context['hmo']}")
            # Priority 3: Comparison queries
            elif hypothetical_context['is_comparison'] or hypothetical_context['multiple_hmos']:
                target_hmos = ['מכבי', 'מאוחדת', 'כללית']
                logger.info("🔄 Including all HMOs for comparison")
            # Priority 4: User's HMO
            else:
                if user_info.hmo_name:
                    target_hmos = [user_info.hmo_name]
                    logger.info(f"👤 Including user's HMO: {user_info.hmo_name}")
                else:
                    target_hmos = ['מכבי', 'מאוחדת', 'כללית']
                    logger.info("🔄 No user HMO, including all")

            # Similar logic for tiers
            if hypothetical_context.get('is_followup_hypothetical') and hypothetical_context.get('tier'):
                target_tiers = [hypothetical_context['tier']]
                logger.info(f"🎯 Follow-up hypothetical tier detected - using: {hypothetical_context['tier']}")
            elif hypothetical_context.get('tier'):
                target_tiers = [hypothetical_context['tier']]
                logger.info(f"🎯 Including specific tier: {hypothetical_context['tier']}")
            elif hypothetical_context['is_comparison'] or hypothetical_context['multiple_tiers']:
                target_tiers = ['זהב', 'כסף', 'ארד']
                logger.info("🔄 Including all tiers for comparison")
            else:
                if user_info.insurance_tier:
                    target_tiers = [user_info.insurance_tier]
                    logger.info(f"👤 Including user's tier: {user_info.insurance_tier}")
                else:
                    target_tiers = ['זהב', 'כסף', 'ארד']
                    logger.info("🔄 No user tier, including all")

            logger.info(f"📊 Final targets - HMOs: {target_hmos}, Tiers: {target_tiers}")

            # Add detailed service information
            services_data = service_data['structured_data']['services']
            logger.info(f"📋 Processing {len(services_data)} services")

            for service_info in services_data:
                service_name = service_info['service_name']
                context_parts.append(f"\n** {service_name} **")

                for hmo in target_hmos:
                    hmo_key = {'מכבי': 'maccabi', 'מאוחדת': 'meuhedet', 'כללית': 'clalit'}[hmo]
                    hmo_benefits = service_info[hmo_key]

                    context_parts.append(f"\n{hmo}:")
                    for tier in target_tiers:
                        if tier in hmo_benefits:
                            benefit_text = hmo_benefits[tier]
                            context_parts.append(f"  • {tier}: {benefit_text}")

            # Add contact information
            contact_info = service_data['structured_data']['contact_info']
            if contact_info:
                context_parts.append(f"\n** מידע ליצירת קשר **")

                for hmo in target_hmos:
                    hmo_key = {'מכבי': 'maccabi', 'מאוחדת': 'meuhedet', 'כללית': 'clalit'}[hmo]
                    if hmo_key in contact_info:
                        contact_text = contact_info[hmo_key]
                        context_parts.append(f"• {contact_text}")
        else:
            logger.info(f"❌ Service {service} not found in knowledge base")

    result = '\n'.join(context_parts)
    logger.info(f"📝 Final comprehensive context length: {len(result)} chars")
    logger.info(f"📄 First 300 chars of context:")
    logger.info(result[:300])
    logger.info("=" * 50)

    return result

# **NEW: Enhanced service detection that can work with conversation context**
def identify_relevant_services_with_context(user_message: str, conversation_history: List = None) -> List[str]:
    """Enhanced version that can infer services from conversation context"""

    # First try the original function
    relevant_services = identify_relevant_services(user_message)

    if relevant_services:
        return relevant_services

    # If no services found and we have conversation history, try to infer
    if conversation_history:
        # Look at recent messages for service context
        recent_messages = conversation_history[-4:]  # Last 4 messages
        for msg in reversed(recent_messages):  # Most recent first
            if msg.role == "assistant":
                # Check if assistant mentioned specific services
                if "הריון" in msg.content or "pregnancy" in msg.content.lower():
                    print("🔍 Inferred pregnancy from conversation context")
                    return ['pregnancy']
                elif "שיניים" in msg.content or "dental" in msg.content.lower():
                    print("🔍 Inferred dental from conversation context")
                    return ['dental']
                elif "ראייה" in msg.content or "עיניים" in msg.content or "optometry" in msg.content.lower():
                    print("🔍 Inferred optometry from conversation context")
                    return ['optometry']
                # Add more service inference as needed

    return relevant_services

def identify_relevant_services(user_message: str) -> List[str]:
    """Identify which services are relevant to the user's query - ENHANCED with English support"""
    message_lower = user_message.lower()
    relevant_services = []

    # Service keywords mapping - ENHANCED with comprehensive English support
    service_keywords = {
        'dental': [
            # Hebrew terms
            'שיניים', 'שן', 'סתימה', 'כתר', 'שתל', 'טיפול שורש', 'יישור', 'קוסמטי',
            # English terms
            'dental', 'teeth', 'tooth', 'filling', 'crown', 'implant', 'root canal',
            'orthodontic', 'braces', 'cosmetic dental', 'dentist', 'cavity', 'extraction',
            'cleaning', 'whitening', 'oral hygiene', 'gum', 'periodontal'
        ],
        'optometry': [
            # Hebrew terms
            'ראייה', 'משקפיים', 'עדשות', 'עיניים', 'עין', 'לחץ תוך עיני', 'לייזר',
            # English terms
            'optometry', 'glasses', 'contact', 'vision', 'eye', 'eyes', 'laser',
            'eyeglasses', 'contact lenses', 'eye exam', 'prescription', 'frames',
            'ophthalmology', 'glaucoma', 'retina', 'cataract', 'vision correction'
        ],
        'pregnancy': [
            # Hebrew terms
            'הריון', 'לידה', 'היריון', 'בהיריון', 'מיילדת', 'הרה', 'הריונית', 'מעקב הריון',
            'סקר גנטי', 'הכנה ללידה', 'מגיע לי', 'זכויות הריון',
            # English terms
            'pregnancy', 'birth', 'pregnant', 'maternity', 'prenatal', 'obstetric',
            'delivery', 'labor', 'midwife', 'ultrasound', 'genetic screening',
            'childbirth', 'prenatal care', 'pregnancy benefits', 'maternal care',
            'postpartum', 'antenatal', 'expecting', 'conception'
        ],
        'alternative': [
            # Hebrew terms
            'רפואה משלימה', 'אלטרנטיבית', 'דיקור', 'שיאצו', 'רפלקסולוגיה', 'נטורופתיה',
            'הומאופתיה', 'כירופרקטיקה',
            # English terms
            'alternative', 'complementary medicine', 'acupuncture', 'shiatsu',
            'reflexology', 'naturopathy', 'homeopathy', 'chiropractic', 'holistic',
            'massage therapy', 'herbal medicine', 'traditional medicine', 'wellness'
        ],
        'communication_clinic': [
            # Hebrew terms
            'תקשורת', 'קלינקה', 'דיבור', 'שפה',
            # English terms
            'communication', 'clinic', 'speech', 'language', 'speech therapy',
            'language therapy', 'communication disorders', 'speech pathology',
            'stuttering', 'voice therapy', 'articulation'
        ],
        'workshops': [
            # Hebrew terms
            'סדנאות', 'קהילה', 'בריאות הקהילה', 'קורסים',
            # English terms
            'workshops', 'community', 'courses', 'classes', 'seminars',
            'community health', 'health education', 'wellness programs',
            'health workshops', 'group sessions', 'training'
        ]
    }

    # Check for general questions about benefits or services - ENHANCED with English
    general_keywords = [
        # Hebrew terms
        'הטבות', 'שירותים', 'קופת חולים', 'מסלול', 'זהב', 'כסף', 'ארד',
        'מגיע לי', 'זכויות',
        # English terms
        'benefits', 'services', 'hmo', 'tier', 'gold', 'silver', 'bronze',
        'coverage', 'insurance', 'plan', 'entitled', 'rights', 'what do i get',
        'what am i entitled to', 'health insurance', 'medical coverage'
    ]

    is_general_query = any(keyword in message_lower for keyword in general_keywords)

    # First check for specific services mentioned
    for service, keywords in service_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            relevant_services.append(service)

    # If specific services found, return them
    if relevant_services:
        return relevant_services

    # If it's a general query and no specific services, include all services
    if is_general_query:
        return list(service_keywords.keys())

    # If nothing found but query seems to be about benefits, include all - ENHANCED with English
    benefit_phrases = [
        # Hebrew
        'מה מגיע', 'איך מגיע', 'זכויות', 'הטבות',
        # English
        'what do i get', 'what am i entitled', 'what are my benefits', 'what coverage',
        'what services', 'my benefits', 'my rights', 'entitled to'
    ]

    if any(phrase in message_lower for phrase in benefit_phrases):
        return list(service_keywords.keys())

    return relevant_services


# Azure OpenAI client initialization
try:
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    deployment_name = "gpt-4o"
    logger.info("Azure OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Azure OpenAI client: {e}")
    raise Exception(f"Azure OpenAI initialization failed: {e}")


# Pydantic models for request/response
class UserInfo(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    id_number: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    hmo_name: Optional[Literal["מכבי", "מאוחדת", "כללית"]] = None
    hmo_card_number: Optional[str] = None
    insurance_tier: Optional[Literal["זהב", "כסף", "ארד"]] = None

    @validator('id_number')
    def validate_id_number(cls, v):
        if v and (not v.isdigit() or len(v) != 9):
            raise ValueError('ID number must be exactly 9 digits')
        return v

    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 120):
            raise ValueError('Age must be between 0 and 120')
        return v

    @validator('hmo_card_number')
    def validate_hmo_card_number(cls, v):
        if v and (not v.isdigit() or len(v) != 9):
            raise ValueError('HMO card number must be exactly 9 digits')
        return v


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    message: str
    user_info: UserInfo
    conversation_history: List[ChatMessage] = []
    phase: Literal["collection", "qa"] = "collection"
    language: Literal["hebrew", "english"] = "hebrew"


class ChatResponse(BaseModel):
    response: str
    updated_user_info: UserInfo
    phase: Literal["collection", "qa"]
    is_complete: bool = False


# ENHANCED: Better collection phase transition detection - BILINGUAL
def should_transition_to_qa(message: str, user_info: UserInfo) -> tuple[bool, bool]:
    """
    Determine if we should transition from collection to QA phase
    Returns: (should_transition, is_question_not_confirmation)
    """
    message_lower = message.lower()

    # Confirmation words - BILINGUAL
    confirmation_words = [
        # Hebrew
        'כן', 'נכון', 'אישור', 'מאשר', 'אוקיי', 'בסדר', 'נכון',
        # English
        'yes', 'correct', 'confirm', 'right', 'okay', 'ok', 'sure', 'confirm'
    ]

    is_confirmation = any(word in message_lower for word in confirmation_words)

    # Question indicators - BILINGUAL
    question_indicators = [
        # Hebrew
        'מה מגיע', 'איך', 'מתי', 'איפה', 'כמה', 'אילו', 'שירותים', 'הטבות', 'הריון',
        # English
        'what do i get', 'what am i entitled', 'how', 'when', 'where', 'how much',
        'which', 'services', 'benefits', 'pregnancy', 'what about', 'can i get'
    ]

    is_question = any(indicator in message_lower for indicator in question_indicators)

    should_transition = is_confirmation or is_question

    return should_transition, is_question

# Enhanced prompts for different phases
COLLECTION_PROMPT_HEBREW = """
אתה עוזר וירטואלי שתפקידו לאסוף מידע מהמשתמש לפני מתן שירותי יעוץ רפואי.
עליך לאסוף את המידע הבא בצורה ידידותית ומקצועית:

1. שם פרטי ושם משפחה
2. מספר תעודת זהות (9 ספרות)
3. מין (זכר/נקבה/אחר)
4. גיל (בין 0 ל-120)
5. שם קופת החולים (מכבי/מאוחדת/כללית)
6. מספר כרטיס קופת חולים (9 ספרות)
7. דרגת ביטוח (זהב/כסף/ארד)

כללים חשובים:
- התחל תמיד בהסבר איזה מידע אתה צריך
- אסוף פרט אחד בכל פעם
- ציין בבירור איזה מידע אתה מחפש כעת
- וודא שהמידע תקין לפני מעבר לפרט הבא
- היה ידידותי ומקצועי
- תן דוגמאות כשמתאים (למשל: "נא הזן מספר תעודת זהות בן 9 ספרות, לדוגמה: 123456789")
- אל תעבור לשלב הבא עד שכל המידע נאסף ואושר
- בסוף תן למשתמש אפשרות לאשר את כל המידע ולתקן אם נדרש

מידע נוכחי על המשתמש: {user_info}

אם זה התחלת השיחה, התחל בהצגת רשימת המידע הנדרש והסבר למה אתה צריך אותו.
"""

# ENHANCED English Collection Prompt - maintains same logic as Hebrew
COLLECTION_PROMPT_ENGLISH_ENHANCED = """
You are a virtual assistant whose role is to collect user information before providing medical consultation services.
You need to collect the following information in a friendly and professional manner:

1. First and last name
2. ID number (9 digits)
3. Gender (Male/Female/Other)
4. Age (between 0 and 120)
5. HMO name (Maccabi/Meuhedet/Clalit)
6. HMO card number (9 digits)
7. Insurance tier (Gold/Silver/Bronze)

Important rules:
- Always start by explaining what information you need and why
- Collect one piece of information at a time
- Clearly specify what information you're currently looking for
- Verify the information is valid before moving to the next item
- Be friendly and professional
- Provide examples when appropriate (e.g., "Enter your 9-digit ID number, example: 123456789")
- Don't move to the next phase until all information is collected and confirmed
- At the end, give the user a chance to confirm all information and make corrections if needed
- If the user asks a question about services or benefits, transition to Q&A mode immediately
- When presenting information lists - use simple numbers (1. 2. 3.) and field names only

Current user information: {user_info}

If this is the start of the conversation, present the list of required information and explain why you need it for providing personalized health service information.
"""

QA_PROMPT_HEBREW = """
אתה עוזר וירטואלי מומחה בשירותי בריאות בישראל. 

מידע על המשתמש:
- שם: {first_name} {last_name}
- קופת חולים: {hmo_name}
- דרגת ביטוח: {insurance_tier}
- גיל: {age}

**הוראות קריטיות:**

1. **תמיד השתמש במידע מהמאגר שמצורף למטה**
2. **אם המאגר מכיל מידע רלוונטי - חובה להציג אותו**
3. **ספק מידע מפורט על ההטבות הספציפיות**
4. **כלול מספרי טלפון כשהם זמינים**

**פורמט תשובה:**
- התחל עם: "על פי מאגר הידע, הנה המידע עבור [קופת חולים] [דרגת ביטוח]:"
- הצג כל שירות בפורמט: 🔹 **[שם השירות]**: [פרטי ההטבה]
- סיים עם פרטי יצירת קשר אם זמינים

**חשוב: המאגר מכיל מידע עבור כל הקופות והדרגות - אם יש מידע במאגר, חובה להציג אותו!**

**רק אם המאגר ריק לחלוטין או לא מכיל שום מידע רלוונטי בכלל - אז אמר "לא נמצא מידע במאגר"**

**מאגר הידע:**
{knowledge_context}

---
**אם המאגר לעיל מכיל מידע (גם אם הוא לא מושלם) - חובה להשתמש בו ולא לומר שאין מידע!**
"""

# ENHANCED English Q&A Prompt - matches Hebrew logic exactly
QA_PROMPT_ENGLISH_ENHANCED = """
You are a virtual assistant expert in Israeli health services.

User Information:
- Name: {first_name} {last_name}
- HMO: {hmo_name}
- Insurance Tier: {insurance_tier}
- Age: {age}

**CRITICAL INSTRUCTIONS:**

1. **ALWAYS use information from the knowledge base below**
2. **If the knowledge base contains relevant information - you MUST present it**
3. **Provide detailed information about specific benefits**
4. **Include phone numbers when available**

**RESPONSE FORMAT:**
- Start with: "Based on the knowledge base, here's the information for {hmo_name} {insurance_tier}:"
- Display each service as: 🔹 **[Service Name]**: [Benefit details]
- End with contact details if available

**IMPORTANT: The knowledge base contains information for all HMOs and tiers - if there's information in the knowledge base, you MUST present it!**

**Only if the knowledge base is completely empty or contains no relevant information at all - then say "No information found in the knowledge base"**

**Knowledge Base:**
{knowledge_context}

---
**If the knowledge base above contains information (even if incomplete) - you MUST use it and not say there's no information!**
"""

def extract_user_info_from_conversation(message: str, current_info: UserInfo) -> UserInfo:
    """Extract user information from the message - ENHANCED with English support"""
    import re

    # Create a copy to modify
    info_dict = current_info.dict()
    message_lower = message.lower()
    logger.info(f"message_lower: {message_lower}")

    # **ENHANCED: Add validation to ensure we're not parsing assistant messages - BILINGUAL**
    assistant_phrases = [
        # Hebrew phrases
        'בואו נתחיל', 'נתחיל באיסוף', 'איסוף המידע', 'נא להזין',
        'בבקשה הזן', 'מה השם', 'איך קורא לך', 'תודה', 'מצוין',
        'עכשיו נעבור', 'הבא צריך', 'נדרש מידע', 'אסוף מידע',
        # English phrases - ENHANCED
        'let\'s start', 'let\'s', 'we\'ll start', 'start collecting', 'collecting information',
        'collecting the information', 'please enter', 'please provide', 'what is your name',
        'what\'s your name', 'thank you', 'excellent', 'now we\'ll move', 'next we need',
        'information required', 'collect information', 'great', 'perfect', 'moving on',
        'next step', 'i need to collect', 'need to gather', 'let me collect',
        'information gathering', 'data collection', 'we need', 'i\'ll need'
    ]

    # **ENHANCED: Better detection of assistant messages**
    # Check for long phrases that are clearly assistant responses
    if (len(message.split()) > 3 and
            any(phrase in message_lower for phrase in assistant_phrases)):
        logger.info(f"Skipping extraction - message appears to be from assistant: {message}")
        return current_info

    # Also skip if message is too long to be user input (likely assistant response)
    if len(message.split()) > 8:
        logger.info(f"Skipping extraction - message too long, likely assistant response: {message}")
        return current_info

    # Extract gender - ENHANCED with English support
    if not current_info.gender:
        gender_keywords = {
            'זכר': [
                # Hebrew
                'זכר', 'גבר', 'בן',
                # English
                'male', 'man', 'boy', 'm'
            ],
            'נקבה': [
                # Hebrew
                'נקבה', 'אישה', 'בת',
                # English
                'female', 'woman', 'girl', 'f'
            ],
            'אחר': [
                # Hebrew
                'אחר',
                # English
                'other', 'non-binary', 'prefer not to say'
            ]
        }

        for gender, keywords in gender_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                info_dict['gender'] = gender
                logger.info(f"Extracted gender: {gender}")
                break

    # Extract age - ENHANCED with English context patterns
    if not current_info.age:
        age_patterns = [
            # Hebrew patterns
            r'גיל[:\s]*(\d{1,2})',
            r'בן[:\s]*(\d{1,2})',
            r'בת[:\s]*(\d{1,2})',
            # English patterns
            r'age[:\s]*(\d{1,2})',
            r'i am[:\s]*(\d{1,2})',
            r'i\'m[:\s]*(\d{1,2})',
            r'(\d{1,2})[:\s]*years old',
            r'(\d{1,2})[:\s]*yrs old',
            # Just a number by itself
            r'^(\d{1,2})$'
        ]

        for pattern in age_patterns:
            age_match = re.search(pattern, message, re.IGNORECASE)
            if age_match:
                age = int(age_match.group(1))
                if 0 <= age <= 120:
                    info_dict['age'] = age
                    logger.info(f"Extracted age: {age}")
                    break

    # Extract HMO name - ENHANCED with English variations
    if not current_info.hmo_name:
        hmo_keywords = {
            'מכבי': ['מכבי', 'maccabi', 'macabi'],
            'מאוחדת': ['מאוחדת', 'meuhedet', 'united', 'meuched'],
            'כללית': ['כללית', 'clalit', 'general', 'klalit']
        }

        for hmo, keywords in hmo_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                info_dict['hmo_name'] = hmo
                logger.info(f"Extracted HMO: {hmo}")
                break

    # Extract insurance tier - ENHANCED with English support
    if not current_info.insurance_tier:
        tier_keywords = {
            'זהב': ['זהב', 'gold', 'premium'],
            'כסף': ['כסף', 'silver', 'standard'],
            'ארד': ['ארד', 'bronze', 'basic']
        }

        for tier, keywords in tier_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                info_dict['insurance_tier'] = tier
                logger.info(f"Extracted insurance tier: {tier}")
                break

    # **FIX: Add length validation - real names are usually 2-20 characters per part**
    def is_valid_name_part(name_part):
        return (
                2 <= len(name_part) <= 20 and  # Reasonable length
                not any(char.isdigit() for char in name_part) and  # No digits
                not any(phrase in name_part for phrase in assistant_phrases)  # No assistant phrases
        )

    # Extract first name (if not already set)
    if not current_info.first_name and not current_info.last_name:
        # If user provides full name
        name_parts = message.strip().split()
        if (len(name_parts) >= 2 and
                all(is_valid_name_part(part) for part in name_parts[:2])):  # Validate both parts
            info_dict['first_name'] = name_parts[0]
            info_dict['last_name'] = ' '.join(name_parts[1:])
            logger.info(f"Extracted full name: {name_parts[0]} {' '.join(name_parts[1:])}")
        elif (len(name_parts) == 1 and
              is_valid_name_part(name_parts[0])):
            info_dict['first_name'] = name_parts[0]
            logger.info(f"Extracted first name: {name_parts[0]}")

    elif not current_info.last_name and current_info.first_name:
        # Extract last name
        name_candidate = message.strip()
        if is_valid_name_part(name_candidate):
            info_dict['last_name'] = name_candidate
            logger.info(f"Extracted last name: {name_candidate}")

    # Extract ID number (9 digits) - only if it's isolated and looks like an ID
    id_match = re.search(r'\b\d{9}\b', message)
    if id_match and not current_info.id_number:
        # Additional validation: make sure it's not part of a longer number
        id_candidate = id_match.group()
        # Check if this is the entire message (user just entered ID) or clearly separated
        if (message.strip() == id_candidate or
                len(message.split()) <= 2):  # Short message likely to be just ID
            info_dict['id_number'] = id_candidate
            logger.info(f"Extracted ID number: {id_candidate}")

    # Extract HMO card number (9 digits, different from ID)
    if not current_info.hmo_card_number and current_info.id_number:
        card_match = re.search(r'\b\d{9}\b', message)
        if card_match and card_match.group() != current_info.id_number:
            info_dict['hmo_card_number'] = card_match.group()
            logger.info(f"Extracted HMO card number: {card_match.group()}")

    return UserInfo(**info_dict)


def format_user_info_for_display(user_info: UserInfo, language: str = "hebrew") -> dict:
    """Format user info for display in the correct language"""

    # Gender translation
    gender_translation = {
        'hebrew': {
            'זכר': 'זכר',
            'נקבה': 'נקבה',
            'אחר': 'אחר'
        },
        'english': {
            'זכר': 'Male',
            'נקבה': 'Female',
            'אחר': 'Other'
        }
    }

    # HMO translation
    hmo_translation = {
        'hebrew': {
            'מכבי': 'מכבי',
            'מאוחדת': 'מאוחדת',
            'כללית': 'כללית'
        },
        'english': {
            'מכבי': 'Maccabi',
            'מאוחדת': 'Meuhedet',
            'כללית': 'Clalit'
        }
    }

    # Tier translation
    tier_translation = {
        'hebrew': {
            'זהב': 'זהב',
            'כסף': 'כסף',
            'ארד': 'ארד'
        },
        'english': {
            'זהב': 'Gold',
            'כסף': 'Silver',
            'ארד': 'Bronze'
        }
    }

    display_info = {
        'first_name': user_info.first_name or ("לא סופק" if language == "hebrew" else "Not provided"),
        'last_name': user_info.last_name or ("לא סופק" if language == "hebrew" else "Not provided"),
        'id_number': user_info.id_number or ("לא סופק" if language == "hebrew" else "Not provided"),
        'gender': gender_translation[language].get(user_info.gender,
                                                   "לא סופק" if language == "hebrew" else "Not provided"),
        'age': user_info.age or ("לא סופק" if language == "hebrew" else "Not provided"),
        'hmo_name': hmo_translation[language].get(user_info.hmo_name,
                                                  "לא סופק" if language == "hebrew" else "Not provided"),
        'hmo_card_number': user_info.hmo_card_number or ("לא סופק" if language == "hebrew" else "Not provided"),
        'insurance_tier': tier_translation[language].get(user_info.insurance_tier,
                                                         "לא סופק" if language == "hebrew" else "Not provided")
    }

    return display_info


@app.on_event("startup")
async def startup_event():
    """Load knowledge base on startup"""
    print("🚀 Starting up - Loading knowledge base...")
    load_knowledge_base()
    print(f"✅ Startup complete - {len(knowledge_base)} services loaded")
    print(f"📋 Available services: {list(knowledge_base.keys())}")


@app.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify the enhanced version is running"""
    return {
        "message": "Enhanced version is running!",
        "knowledge_base_count": len(knowledge_base),
        "services": list(knowledge_base.keys()) if knowledge_base else []
    }


@app.get("/health")
async def health_check():
    logger.info(f"health check")
    return {"status": "healthy", "timestamp": datetime.now(), "knowledge_base_loaded": len(knowledge_base)}


@app.get("/")
async def root():
    logger.info(f"root")
    return {"message": "Enhanced Medical HMO Chatbot API is running"}


@app.get("/debug/knowledge")
async def debug_knowledge():
    """Debug endpoint to check knowledge base status"""
    debug_info = {
        "knowledge_base_loaded": len(knowledge_base),
        "services": list(knowledge_base.keys()),
        "sample_data": {}
    }

    # Add sample data for each service
    for service_name, service_data in knowledge_base.items():
        debug_info["sample_data"][service_name] = {
            "title": service_data['structured_data']['title'],
            "description_length": len(service_data['structured_data']['description']),
            "services_count": len(service_data['structured_data']['services']),
            "raw_html_length": len(service_data['raw_html']),
            "first_100_chars": service_data['raw_html'][:100]
        }

    return debug_info


@app.get("/debug/simple")
async def debug_simple():
    """Simple debug to check if pregnancy data exists"""

    result = {
        "knowledge_base_loaded": len(knowledge_base),
        "services": list(knowledge_base.keys()),
        "pregnancy_exists": 'pregnancy' in knowledge_base
    }

    if 'pregnancy' in knowledge_base:
        pregnancy = knowledge_base['pregnancy']
        result["pregnancy_info"] = {
            "raw_html_length": len(pregnancy['raw_html']),
            "structured_services_count": len(pregnancy['structured_data']['services']),
            "title": pregnancy['structured_data']['title'],
            "first_service_name": pregnancy['structured_data']['services'][0]['service_name'] if
            pregnancy['structured_data']['services'] else "None"
        }

        # Test service detection
        test_query = "מה מגיע לי מבחינת הריון"
        relevant_services = identify_relevant_services(test_query)
        result["service_detection"] = {
            "query": test_query,
            "detected_services": relevant_services,
            "pregnancy_detected": 'pregnancy' in relevant_services
        }

    return result


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        logger.info(f"Chat request received - Phase: {request.phase}, Language: {request.language}")

        # Extract user info from the message if in collection phase
        updated_user_info = request.user_info
        if request.phase == "collection":
            updated_user_info = extract_user_info_from_conversation(request.message, request.user_info)
        logger.info(f"Updated user info: {updated_user_info}")
        # Check if we should transition from collection to Q&A
        current_phase = request.phase
        if request.phase == "collection":
            logger.info(f"🔄 DEBUG: Collection phase, checking for transition...")

            should_transition, is_question = should_transition_to_qa(request.message, updated_user_info)

            if should_transition:
                current_phase = "qa"
                logger.info(f"🎉 DEBUG: Transitioning to QA phase!")

                if is_question:
                    # User asked a question, go straight to answering it
                    logger.info(f"🚀 DEBUG: User asked question, proceeding to answer...")
                else:
                    # User confirmed, give transition message
                    if request.language == "hebrew":
                        assistant_response = "מצוין! עכשיו אני יכול לעזור לך עם שאלות על שירותי הבריאות שלך בהתבסס על מאגר המידע המפורט. איך אוכל לעזור?"
                    else:
                        assistant_response = "Great! Now I can help you with questions about your health services based on our detailed database. How can I assist you?"

                    return ChatResponse(
                        response=assistant_response,
                        updated_user_info=updated_user_info,
                        phase=current_phase,
                        is_complete=True
                    )
            else:
                logger.info(f"❌ DEBUG: No confirmation or question detected, staying in collection phase")

        # # Get comprehensive knowledge context for Q&A phase
        knowledge_context = ""
        if current_phase == "qa":
            # Detect hypothetical queries (asking about other HMOs/tiers)
            hypothetical_context = detect_hypothetical_query(request.message)
            logger.info(f"🤔 Hypothetical context detected: {hypothetical_context}")

            # **ENHANCED: Use conversation history for better service detection**
            relevant_services = identify_relevant_services_with_context(
                request.message,
                request.conversation_history
            )
            logger.info(f"📋 Identified relevant services: {relevant_services}")

            # **IMPORTANT: Always try to get context, even for follow-ups**
            knowledge_context = get_comprehensive_knowledge_context(
                request.message,
                updated_user_info,
                hypothetical_context
            )

            logger.info(f"📝 Knowledge context length: {len(knowledge_context)}")

            # **DEBUG: Log what's happening**
            if not knowledge_context:
                print("❌ WARNING: No knowledge context generated!")
                print(f"   Message: {request.message}")
                print(f"   Hypothetical: {hypothetical_context}")
                print(f"   Services: {relevant_services}")
            else:
                print("✅ Knowledge context generated successfully")

        # # Update the system prompt to handle missing context better
        if current_phase == "collection":
            if request.language == "hebrew":
                system_prompt = COLLECTION_PROMPT_HEBREW.format(user_info=updated_user_info.dict())
            else:
                system_prompt = COLLECTION_PROMPT_ENGLISH_ENHANCED.format(user_info=updated_user_info.dict())
        else:
            # **ENHANCED: Better handling when knowledge context is empty**
            if not knowledge_context and hypothetical_context.get('hmo'):
                # If we detected an HMO but no context, generate a helpful message
                knowledge_context = f"המשתמש שואל על {hypothetical_context['hmo']} - יש לחפש מידע רלוונטי במאגר הידע."

            if request.language == "hebrew":
                system_prompt = QA_PROMPT_HEBREW.format(
                    first_name=updated_user_info.first_name or "",
                    last_name=updated_user_info.last_name or "",
                    hmo_name=updated_user_info.hmo_name or "לא צוין",
                    insurance_tier=updated_user_info.insurance_tier or "לא צוין",
                    age=updated_user_info.age or "לא צוין",
                    knowledge_context=knowledge_context
                )
            else:
                system_prompt = QA_PROMPT_ENGLISH_ENHANCED.format(
                    first_name=updated_user_info.first_name or "",
                    last_name=updated_user_info.last_name or "",
                    hmo_name=updated_user_info.hmo_name or "Not specified",
                    insurance_tier=updated_user_info.insurance_tier or "Not specified",
                    age=updated_user_info.age or "Not specified",
                    knowledge_context=knowledge_context
                )

        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 6 messages to avoid token limits)
        recent_history = request.conversation_history[-6:] if len(
            request.conversation_history) > 6 else request.conversation_history
        for msg in recent_history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add current user message
        messages.append({"role": "user", "content": request.message})

        # Call Azure OpenAI
        logger.info(f"Calling Azure OpenAI with model: {deployment_name}")
        logger.info(f"Knowledge context length: {len(knowledge_context)} chars")

        response = client.chat.completions.create(
            model=deployment_name,
            messages=messages,
            max_tokens=5000,  # Reduced to focus on specific answers
            temperature=0.3  # Very low temperature for precise, instruction-following responses
        )

        assistant_response = response.choices[0].message.content

        logger.info(f"Chat response generated successfully - Length: {len(assistant_response)} chars")

        return ChatResponse(
            response=assistant_response,
            updated_user_info=updated_user_info,
            phase=current_phase,
            is_complete=False
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)