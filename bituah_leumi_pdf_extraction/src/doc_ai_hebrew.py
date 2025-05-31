import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature
from azure.core.credentials import AzureKeyCredential
import sys
import re
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

def extract_text_from_pdf(pdf_content):
    """
    Extract text from PDF using Azure Document Intelligence OCR

    Args:
        pdf_path (str): Path to the PDF file
        endpoint (str): Azure Document Intelligence endpoint
        api_key (str): Azure Document Intelligence API key

    Returns:
        str: Extracted text content
    """

    # Initialize the Document Intelligence client
    client = DocumentIntelligenceClient(
        endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
        credential=AzureKeyCredential(os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"))
    )

    try:
        # Analyze the document using the layout model
        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=pdf_content,
            locale="he-IL",  # Hebrew locale
            features=[
                DocumentAnalysisFeature.OCR_HIGH_RESOLUTION,  # Better text recognition
                DocumentAnalysisFeature.LANGUAGES,]
        )

        # Get the result
        result = poller.result()
        return result.content

    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return None


def clean_document_text(text):
    """
    Clean document text by removing specific symbols and sections.

    Args:
        text (str): The input text to clean

    Returns:
        str: Cleaned text with symbols and sections removed
    """
    # Remove the symbols |, [, and ]
    cleaned_text = text.replace('|', '').replace('[', '').replace(']', '')

    def fix_phone_numbers(text):
        def process_phone_line(line):
            if 'טלפון' in line:
                # For phone lines: reverse digits and fix OCR errors
                def fix_phone_digits(match):
                    digits = re.findall(r'\d', match.group(0))

                    # Fix OCR error: if first digit is 0, change to 6
                    if digits and digits[0] != '0':
                        digits[0] = '0'

                    # ADD THIS LINE - return the processed digits
                    return ''.join(digits)

                return re.sub(r'\d[\d\s]*', fix_phone_digits, line)
            else:
                # Return the original line if it's not a phone line
                return line

        lines = text.split('\n')
        processed_lines = [process_phone_line(line) for line in lines]
        return '\n'.join(processed_lines)
    # Remove 'X' after 'חתימה'
    cleaned_text = cleaned_text.replace('חתימה X', 'חתימה')
    cleaned_text = cleaned_text.replace('חתימהX', 'חתימה')
    # Replace :selected: and :unselected: with Hebrew equivalents
    # Newline before both markers
    cleaned_text = cleaned_text.replace(':selected:', 'נבחר: ')
    cleaned_text = cleaned_text.replace(':unselected:', 'לא נבחר: ')
    # This puts the option and status on the same line:
    cleaned_text = fix_phone_numbers(cleaned_text)


    # Find and remove everything from "עמוד 2 מתוך 2" onwards (including that line)
    page_2_marker = "עמוד 2 מתוך 2"
    page_2_index = cleaned_text.find(page_2_marker)

    if page_2_index != -1:
        # Keep everything before "עמוד 2 מתוך 2"
        cleaned_text = cleaned_text[:page_2_index].rstrip()

    return cleaned_text

def main():
    """
    Main function to run the OCR extraction
    """

    # Get PDF path from command line argument or use default
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "/Users/ormeiri/Desktop/KPMGassignment/KPMGasasignment/phase1_data/283_ex3.pdf"

    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' not found")
        return

    # Check if file is a PDF
    if not pdf_path.lower().endswith('.pdf'):
        print("Warning: File doesn't appear to be a PDF")

    print(f"Processing PDF: {pdf_path}")
    print("Extracting text using Azure Document Intelligence...")

    with open(pdf_path, 'rb') as pdf_file:
        pdf_content = pdf_file.read()

    # Extract text from PDF
    extracted_text = extract_text_from_pdf(pdf_content)

    if extracted_text:
        cleaned_text = clean_document_text(extracted_text)
        print("\n" + "=" * 50)
        print("EXTRACTED TEXT:")
        print("=" * 50)
        print(cleaned_text)
        print("=" * 50)
        # Optionally save to file
        output_file = pdf_path.replace('.pdf', '_extracted_text.txt')
        # Save the extracted text to a file in the extracted text directory
        extracted_text_path = '/Users/ormeiri/Desktop/KPMGassignment/KPMGasasignment/bituah_leumi_pdf_extraction/extracted_phase1_text'
        output_file = os.path.join(extracted_text_path, os.path.basename(output_file))
        with open(output_file, 'w', encoding='utf-8') as f_cleaned:
            f_cleaned.write(cleaned_text)
        print(f"Cleaned text saved to: {output_file}")
    else:
        print("Failed to extract text from PDF")


if __name__ == "__main__":
    main()

