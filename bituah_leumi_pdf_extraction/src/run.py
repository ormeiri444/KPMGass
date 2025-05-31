import streamlit as st
import json
from pathlib import Path

# Import your custom functions
from doc_ai_hebrew import extract_text_from_pdf, clean_document_text
from doc_ai_english import extract_text_from_pdf as extract_text_from_pdf_checkbox
from gpt_field_extraction import extract_fields_from_ocr_text

def display_json_fields(json_data, parent_key=""):
    """
    Recursively display JSON fields in a user-friendly format
    """
    for key, value in json_data.items():
        if isinstance(value, dict):
            # Display nested object header
            header_text = key.replace('_', ' ').title()
            if key == 'dateOfBirth':
                header_text = "Date Of Birth"
            elif key == 'dateOfInjury':
                header_text = "Date Of Injury"
            elif key == 'formFillingDate':
                header_text = "Form Filling Date"
            elif key == 'formReceiptDateAtClinic':
                header_text = "Form Receipt Date At Clinic"
            elif key == 'medicalInstitutionFields':
                header_text = "Medical Institution Fields"
            elif key == 'address':
                header_text = "Address"

            st.subheader(header_text)
            display_json_fields(value, key)
        else:
            # Create a more readable label
            if key == 'lastName':
                label = "Last Name"
            elif key == 'firstName':
                label = "First Name"
            elif key == 'idNumber':
                label = "ID Number"
            elif key == 'dateOfBirth':
                label = "Date of Birth"
            elif key == 'landlinePhone':
                label = "Landline Phone"
            elif key == 'mobilePhone':
                label = "Mobile Phone"
            elif key == 'jobType':
                label = "Job Type"
            elif key == 'timeOfInjury':
                label = "Time of Injury"
            elif key == 'accidentLocation':
                label = "Accident Location"
            elif key == 'accidentAddress':
                label = "Accident Address"
            elif key == 'accidentDescription':
                label = "Accident Description"
            elif key == 'injuredBodyPart':
                label = "Injured Body Part"
            elif key == 'houseNumber':
                label = "House Number"
            elif key == 'postalCode':
                label = "Postal Code"
            elif key == 'poBox':
                label = "PO Box"
            elif key == 'healthFundMember':
                label = "Health Fund Member"
            elif key == 'natureOfAccident':
                label = "Nature of Accident"
            elif key == 'medicalDiagnoses':
                label = "Medical Diagnoses"
            else:
                # Default formatting for other fields
                label = key.replace('_', ' ').title()

            # Display the field with its value
            if value:
                st.write(f"**{label}:** {value}")
            else:
                st.write(f"**{label}:** *Not found*")


def main():
    st.set_page_config(
        page_title="PDF Field Extraction",
        page_icon="📄",
        layout="wide"
    )

    st.title("📄 PDF Field Extraction Tool")
    st.markdown("Upload a PDF file to extract structured information using AI")

    # Create two columns for better layout
    col1, col2 = st.columns([1, 2])

    with col1:
        st.header("Upload PDF")

        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload a PDF document to extract fields from"
        )

        if uploaded_file is not None:
            st.success(f"File uploaded: {uploaded_file.name}")
            st.info(f"File size: {uploaded_file.size} bytes")

            # Process button
            process_button = st.button(
                "🚀 Process PDF",
                type="primary",
                use_container_width=True
            )

            if process_button:
                with st.spinner("Processing PDF... This may take a few moments."):
                    try:
                        # Get PDF content as bytes
                        pdf_content = uploaded_file.getvalue()

                        # Step 1: Extract text from PDF
                        st.write("📖 Extracting text from PDF...")
                        extracted_text = extract_text_from_pdf(pdf_content)
                        st.write("🧹 Cleaning extracted text...")
                        cleaned_text = clean_document_text(extracted_text)
                        st.write("🤖 Extracting fields using AI...")
                        extracted_fields = extract_fields_from_ocr_text(cleaned_text)
                        if extracted_fields['lastName'].isascii() or extracted_fields['firstName'].isascii():
                            extracted_text_checkbox = extract_text_from_pdf_checkbox(pdf_content)
                            cleaned_text_checkbox = clean_document_text(extracted_text_checkbox)
                            extracted_fields_checkbox = extract_fields_from_ocr_text(cleaned_text_checkbox)
                            if extracted_fields['lastName'] != "" and extracted_fields_checkbox['lastName'] == '':
                                extracted_fields_checkbox['lastName'] = extracted_fields['lastName']
                            extracted_fields = extracted_fields_checkbox

                        # Store results in session state
                        st.session_state.extracted_fields = extracted_fields
                        st.session_state.cleaned_text = cleaned_text

                        st.success("✅ Processing completed successfully!")

                    except Exception as e:
                        st.error(f"❌ Error processing PDF: {str(e)}")

    with col2:
        st.header("Extracted Fields")

        # Display results if available
        if hasattr(st.session_state, 'extracted_fields') and st.session_state.extracted_fields:

            # Add tabs for different views
            tab1, tab2, tab3 = st.tabs(["📋 Structured View", "📝 JSON View", "📄 Raw Text"])

            with tab1:
                st.subheader("Extracted Information")

                # Parse JSON if it's a string
                if isinstance(st.session_state.extracted_fields, str):
                    try:
                        json_data = json.loads(st.session_state.extracted_fields)
                    except json.JSONDecodeError:
                        st.error("Error parsing JSON data")
                        json_data = {}
                else:
                    json_data = st.session_state.extracted_fields

                # Display fields in a structured format
                if json_data:
                    display_json_fields(json_data)
                else:
                    st.warning("No fields were extracted from the document")

            with tab2:
                st.subheader("Raw JSON Output")

                # Display JSON with syntax highlighting
                if isinstance(st.session_state.extracted_fields, str):
                    json_str = st.session_state.extracted_fields
                else:
                    json_str = json.dumps(st.session_state.extracted_fields, indent=2, ensure_ascii=False)

                st.code(json_str, language='json')

            with tab3:
                if hasattr(st.session_state, 'cleaned_text'):
                    st.subheader("Cleaned Text")
                    st.text_area(
                        "Extracted and cleaned text from PDF:",
                        value=st.session_state.cleaned_text,
                        height=400,
                        disabled=True
                    )
                else:
                    st.info("No cleaned text available")

        else:
            st.info("👆 Upload a PDF file and click 'Process PDF' to see extracted fields here")

            # Show example JSON structure
            st.subheader("Expected JSON Structure")
            example_json = {
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

            st.code(json.dumps(example_json, indent=2), language='json')

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
            <p>PDF Field Extraction Tool - Powered by AI</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()