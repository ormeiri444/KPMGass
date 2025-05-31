import json
import os
import re
from openai import AzureOpenAI
from dotenv import load_dotenv
# Load environment variables
load_dotenv()


def extract_fields_from_ocr_text(ocr_text):
    """
    Simple function to extract fields from OCR text using Azure OpenAI
    """

    # Initialize Azure OpenAI client
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )

    prompt = """
You are extracting information from an Israeli National Insurance Institute (ביטוח לאומי) form.

Extract the following fields from the OCR text and return ONLY a valid JSON object.
For any field not found, use an empty string "".

Here are detailed extraction rules to follow EXACTLY:

1. Text Preservation - STRICT RULE:
   - NEVER shorten, abbreviate, or modify any written text from the document
   - Copy text EXACTLY as it appears, including spelling errors or unusual formatting

2. ID Numbers - STRICT RULE:
   - If ID number has MORE than 9 digits, keep ALL extra digits - do NOT truncate
   - If ID number has LESS than 9 digits, keep exactly what's written - do NOT add zeros
   - ID is only numbers with no letters in it! If there are spaces between the numbers remove them.

3. Job Type Detection - STRICT RULE:
   - Look for this EXACT pattern hierarchy:
     1. First find "סוג העבודה"
     2. Look at the line ABOVE "סוג העבודה" - this should contain "תאריך"
     3. Look at the line ABOVE the "תאריך" line - THIS is the actual job type value
   - Do NOT use any text that appears after or below "סוג העבודה"
   - If this pattern is not found, leave jobType empty ""

4. Signature Field - STRICT RULE:
   - Look ONLY at the line immediately after the word "חתימה" If that line contains text, fill by it!
   - If there is a **Name** after חתימה fill the correct spot in the json!
   - If there is a **Name** exactly one line BELOW חתימה fill the correct spot in the json!
   - If that line contains ANY numbers, dates, symbols, or institutional text, the signature field MUST be empty ""
   - NEVER use names from other parts of the document !! just from the row after "חתימה"
   - NEVER fill signature based on context or judgment!! just based on what's directly after "חתימה"
   - Example: if you see "חתימה" followed by "5" or any number, signature = ""

5. First Name Inference - STRICT RULE:
   - First, look for direct "שם פרטי" field
   - If "שם פרטי" field is empty or not found, then you MAY infer from other sections:
     * Check "שם המבקש" section for full name, extract first name portion
     * Check signature area for full names
     * Check any other name fields in the document
   - When inferring, extract ONLY the first name part, not the full name
   - If you find "יוסף כהן", extract only "יוסף" for firstName

6. Selection Field Extraction - STRICT RULE:
   - When you see "נבחר:" (selected), extract the text that comes immediately after it on the same line
   - If nothing follows "נבחר:" on the same line, look at the text on the line directly below
   - Continue reading subsequent lines until you encounter another "נבחר:" or "לא נבחר:"
   - Stop extracting when you reach another selection marker or a clear field separator
   - Ignore any "לא נבחר:" (unselected) options completely

7. **accidentLocation** (מקום התאונה) - STRICT RULE:
- Look for the "מקום התאונה:" section in the document
- Possible values are: במפעל, תאונה בדרך ללא רכב, ת. דרכים בדרך לעבודה/מהעבודה, ת. דרכים בעבודה, אחר
- **Selection Detection Methods** (in order of priority):
  1. **Direct "נבחר:" marker**: Look for text immediately followed by "נבחר:" - this is the selected option
  2. **Checkbox or mark indicators**: Look for visual markers like ✓, ☑, X, or other symbols next to options
  3. **"לא נבחר:" exclusion**: If an option shows "לא נבחר:" it is NOT selected - ignore it completely
  4. **Formatting clues**: Selected options may appear without "לא נבחר:" while unselected ones have "לא נבחר:"

8. **natureOfAccident** - STRICT RULE:
   - This field can ONLY contain one of these two values: "סומן" or ""
   - Look for checkboxes or selection indicators related to nature of accident
   - If you see any indication that this field is marked/checked/selected, use "סומן"
   - If you see any indication that this field is not marked/unchecked/unselected, use ""
   - If no clear indication is found, leave as empty string ""

9. **Address Fields - Entrance vs Apartment** - STRICT RULE:
   - **Entrance (כניסה)**: Can be letters (א, ב, ג, A, B, C) OR numbers (1, 2, 3, etc.) - typically single digit or letter
   - **Apartment (דירה)**: Numbers (1, 2, 3, 12, 42, etc.) - can be single or multiple digits
   - **Field Position Logic**: Look at the ADDRESS section structure in the form:
     * "רחוב / תא דואר" → street field
     * "מס׳ בית" → houseNumber field  
     * "כניסה" → entrance field (what comes after the כניסה label)
     * "דירה" → apartment field (what comes after the דירה label)
   - **Pattern Recognition Logic**:
     * **3 components** (street, house number, single number/letter): entrance="", apartment=single number
     I am saying again if you see 3 values its in the form of street, house number and apartment number!
     * **4 components** (street, house number, entrance, apartment): entrance=first value, apartment=second value
   - **Important**: Extract based on POSITION in the form, not content type
   - Examples from real forms:
     * "hameri 48 3 tel aviv" → street="hameri", houseNumber="48", entrance="", apartment="3"
     * "הרמבם 16 1 12 אבן יהודה" → street="הרמבם", houseNumber="16", entrance="1", apartment="12"
     * "ראובן רובין 7 12 באר שבע" → street="ראובן רובין", houseNumber="7", entrance="", apartment="12"

10. CRITICAL: Return the COMPLETE JSON structure with ALL fields
    - NEVER remove any fields from the JSON structure, even if not found in the text. Leave empty fields as empty strings "" but keep the field in the JSON.
    - The JSON structure must match the provided template exactly, with all fields present
    - Never remove the field medicalDiagnoses in your answer, even if not found in the text. Leave it as an empty string "" if not found.
    
11. ONLY phone numbers always start with 0. If the first digit is not read as zero, change the first digit to zero (do not add an extra zero). Note: don't change numbers like ID only phone numbers!

Look for these Hebrew/English field mappings:
- שם משפחה / Last Name → lastName
- שם פרטי / First Name → firstName
- מספר זהות / ID Number → idNumber
- מין / Gender → gender
- תאריך לידה / Date of Birth → dateOfBirth (split into day, month, year)
- רחוב / Street → address.street
- מספר בית / House Number → address.houseNumber
- כניסה / Entrance → address.entrance
- דירה / Apartment → address.apartment
- ישוב / City → address.city
- מיקוד / Postal Code → address.postalCode
- תא דואר / PO Box → address.poBox
- טלפון קווי / Landline → landlinePhone
- טלפון נייד / Mobile → mobilePhone
- סוג העבודה / Job Type → jobType
- תאריך הפגיעה / Date of Injury → dateOfInjury (split into day, month, year)
- שעת הפגיעה / Time of Injury → timeOfInjury
- מקום התאונה / Accident Location → accidentLocation
- כתובת מקום התאונה / Accident Address → accidentAddress
- תיאור התאונה / Accident Description → accidentDescription
- האיבר שנפגע / Injured Body Part → injuredBodyPart
- חתימה / Signature → signature
- תאריך מילוי הטופס / Form Filling Date → formFillingDate (split into day, month, year)
- תאריך קבלת הטופס בקופה / Form Receipt Date → formReceiptDateAtClinic (split into day, month, year)
- Medical fields → medicalInstitutionFields

Return this exact JSON structure:
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

OCR TEXT TO ANALYZE:
"""

    # Make API call
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # or your deployment name
            messages=[
                {"role": "user", "content": prompt + ocr_text}
            ],
            temperature=0.1,
            max_tokens=2000
        )

        # Extract and parse JSON response
        content = response.choices[0].message.content.strip()

        # Try to extract JSON from response
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1

        if start_idx != -1 and end_idx != -1:
            json_str = content[start_idx:end_idx]
            extracted_data = json.loads(json_str)
            return extracted_data
        else:
            print("No JSON found in response")
            return None

    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    """
    Main function - replace 'ocr_text.txt' with your actual file path
    """

    # Path to your OCR text file
    text_file_path = "/Users/ormeiri/Desktop/KPMGassignment/KPMGasasignment/bituah_leumi_pdf_extraction/extracted_phase1_text/283_ex3_extracted_text.txt"  # Change this to your file path

    print("Extracting fields from OCR text...")

    # Get the OCR text from the file
    with open(text_file_path, 'r', encoding='utf-8') as file:
        ocr_text = file.read()

    # Extract fields
    result = extract_fields_from_ocr_text(ocr_text)

    if result:
        # Print the result
        print("\nExtracted Fields:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Save to file
        file_name = text_file_path.split('/')[-1].replace('_extracted_text.txt', '_extracted_fields.json')
        with open(f"/Users/ormeiri/Desktop/KPMGassignment/KPMGasasignment/bituah_leumi_pdf_extraction/extracted_jsons/{file_name}", "w",
                  encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to '{file_name}'")
    else:
        print("Failed to extract fields")


if __name__ == "__main__":
    main()
