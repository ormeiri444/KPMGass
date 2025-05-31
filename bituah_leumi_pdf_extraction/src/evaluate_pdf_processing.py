import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Add the src directory to the path to import your modules
sys.path.append('/Users/ormeiri/Desktop/KPMGassignment/KPMGasasignment/bituah_leumi_pdf_extraction/src')

from doc_ai_hebrew import extract_text_from_pdf, clean_document_text
from doc_ai_english import extract_text_from_pdf as extract_text_from_pdf_checkbox
from gpt_field_extraction import extract_fields_from_ocr_text


def calculate_completeness(extracted_json: Dict, total_fields: int) -> float:
    """
    Calculate completeness based on how many fields have non-empty values

    Args:
        extracted_json: The extracted JSON data
        total_fields: Total number of fields in the structure

    Returns:
        float: Completeness percentage (0.0 to 1.0)
    """
    filled_fields = 0

    def count_filled_fields(obj, parent_key=""):
        nonlocal filled_fields
        if isinstance(obj, dict):
            for key, value in obj.items():
                count_filled_fields(value, f"{parent_key}.{key}" if parent_key else key)
        else:
            # Count as filled if it's not empty string and not None
            if obj and str(obj).strip():
                filled_fields += 1

    count_filled_fields(extracted_json)
    return filled_fields / total_fields if total_fields > 0 else 0.0


def count_total_fields(json_structure: Dict) -> int:
    """
    Count total number of leaf fields in the JSON structure
    """
    count = 0

    def count_fields(obj):
        nonlocal count
        if isinstance(obj, dict):
            for value in obj.values():
                count_fields(value)
        else:
            count += 1

    count_fields(json_structure)
    return count


def compare_jsons_detailed(extracted_json: Dict, gold_json: Dict) -> Tuple[float, float, Dict]:
    """
    Compare two JSON objects with detailed analysis

    Args:
        extracted_json: The extracted JSON data
        gold_json: The gold standard JSON data

    Returns:
        Tuple of (accuracy, completeness, mismatched_fields)
    """
    if not isinstance(extracted_json, dict) or not isinstance(gold_json, dict):
        raise ValueError("Both inputs must be dictionaries.")

    total_fields = count_total_fields(gold_json)
    matching_fields = 0
    mismatched_fields = {}

    def compare_nested(obj1, obj2, path=""):
        nonlocal matching_fields, mismatched_fields

        if isinstance(obj1, dict) and isinstance(obj2, dict):
            for key in obj2:  # Use gold standard keys as reference
                current_path = f"{path}.{key}" if path else key

                if key not in obj1:
                    mismatched_fields[current_path] = {
                        'extracted': 'MISSING_FIELD',
                        'gold': obj2[key],
                        'type': 'missing_field'
                    }
                    continue

                compare_nested(obj1[key], obj2[key], current_path)
        else:
            # Compare leaf values
            extracted_val = str(obj1).strip() if obj1 else ""
            gold_val = str(obj2).strip() if obj2 else ""

            if extracted_val == gold_val:
                matching_fields += 1
            else:
                mismatched_fields[path] = {
                    'extracted': extracted_val,
                    'gold': gold_val,
                    'type': 'value_mismatch'
                }

    compare_nested(extracted_json, gold_json)

    accuracy = matching_fields / total_fields if total_fields > 0 else 0.0
    completeness = calculate_completeness(extracted_json, total_fields)

    return accuracy, completeness, mismatched_fields


def process_single_pdf(pdf_path: str, gold_json_path: str = None) -> Dict:
    """
    Process a single PDF through the entire pipeline with hybrid OCR approach

    Args:
        pdf_path: Path to the PDF file
        gold_json_path: Path to the corresponding gold standard JSON (optional)

    Returns:
        Dictionary with processing results and metrics
    """
    result = {
        'pdf_file': os.path.basename(pdf_path),
        'success': False,
        'extracted_json': None,
        'accuracy': 0.0,
        'completeness': 0.0,
        'mismatched_fields': {},
        'error': None
    }

    try:
        print(f"\n📄 Processing: {os.path.basename(pdf_path)}")

        # Read PDF content once
        with open(pdf_path, 'rb') as pdf_file:
            pdf_content = pdf_file.read()

        # Step 1a: Extract text from PDF using regular OCR
        print("  📖 Extracting text from PDF (regular OCR)...")
        extracted_text = extract_text_from_pdf(pdf_content)
        if not extracted_text:
            result['error'] = "Failed to extract text from PDF (regular OCR)"
            return result

        # Step 2: Clean both extracted texts
        print("  🧹 Cleaning extracted texts...")
        cleaned_text = clean_document_text(extracted_text)
        # Step 3: Extract fields using GPT from both versions
        print("  🤖 Extracting fields using AI (regular OCR)...")
        extracted_fields = extract_fields_from_ocr_text(cleaned_text)

        if extracted_fields['lastName'].isascii() or extracted_fields['firstName'].isascii():
            print("  📋 Extracting text from PDF (checkbox OCR)...")
            extracted_text_checkbox = extract_text_from_pdf_checkbox(pdf_content)
            if not extracted_text_checkbox:
                result['error'] = "Failed to extract text from PDF (checkbox OCR)"
                return result
            cleaned_text_checkbox = clean_document_text(extracted_text_checkbox)
            print("  🤖 Extracting fields using AI (checkbox OCR)...")
            extracted_fields_checkbox = extract_fields_from_ocr_text(cleaned_text_checkbox)

            if extracted_fields['lastName'] != "" and extracted_fields_checkbox['lastName'] == '':
                extracted_fields_checkbox['lastName'] = extracted_fields['lastName']
            extracted_fields = extracted_fields_checkbox

        result['extracted_json'] = extracted_fields
        result['success'] = True

        # Step 5: Evaluate against gold standard if available
        if gold_json_path and os.path.exists(gold_json_path):
            print("  📊 Evaluating against gold standard...")
            with open(gold_json_path, 'r', encoding='utf-8') as f:
                gold_json = json.load(f)

            accuracy, completeness, mismatched_fields = compare_jsons_detailed(extracted_fields, gold_json)
            result['accuracy'] = accuracy
            result['completeness'] = completeness
            result['mismatched_fields'] = mismatched_fields
        else:
            # Calculate completeness even without gold standard
            total_fields = count_total_fields(extracted_fields)
            result['completeness'] = calculate_completeness(extracted_fields, total_fields)
            print("  ⚠️  No gold standard found for comparison")

    except Exception as e:
        result['error'] = str(e)
        print(f"  ❌ Error: {str(e)}")

    return result


def print_detailed_results(result: Dict):
    """Print detailed results for a single file"""
    print(f"\n{'=' * 60}")
    print(f"📄 File: {result['pdf_file']}")
    print(f"{'=' * 60}")

    if not result['success']:
        print(f"❌ Processing failed: {result['error']}")
        return

    print(f"✅ Processing successful")
    print(f"📊 Accuracy: {result['accuracy']:.2%}")
    print(f"📈 Completeness: {result['completeness']:.2%}")

    if result['mismatched_fields']:
        print(f"\n🔍 Field Analysis ({len(result['mismatched_fields'])} issues found):")
        print("-" * 50)

        for field_path, details in result['mismatched_fields'].items():
            field_name = field_path.split('.')[-1]
            if details['type'] == 'missing_field':
                print(f"❌ {field_name}: FIELD MISSING")
                print(f"   Expected: '{details['gold']}'")
            else:
                print(f"❌ {field_name}: VALUE MISMATCH")
                print(f"   Extracted: '{details['extracted']}'")
                print(f"   Expected:  '{details['gold']}'")
            print()
    else:
        print("✅ All fields match perfectly!")


def run_evaluation():
    """
    Main evaluation function that processes all PDFs in the folder
    """

    # Configuration
    pdf_folder = "/Users/ormeiri/Desktop/KPMGassignment/KPMGasasignment/phase1_data"
    gold_folder = "/Users/ormeiri/Desktop/KPMGassignment/KPMGasasignment/bituah_leumi_pdf_extraction/gold_standard"

    print("🚀 Starting Comprehensive PDF Processing Evaluation (Hybrid OCR)")
    print("=" * 70)

    # Get all PDF files
    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]

    if not pdf_files:
        print(f"❌ No PDF files found in {pdf_folder}")
        return

    print(f"Found {len(pdf_files)} PDF files to process")

    # Process each PDF
    all_results = []
    successful_processes = 0
    total_accuracy = 0.0
    total_completeness = 0.0
    files_with_gold_standard = 0

    for pdf_file in sorted(pdf_files):
        pdf_path = os.path.join(pdf_folder, pdf_file)

        # Try to find corresponding gold standard file
        # Assuming naming convention: 283_ex1.pdf -> 283_ex1_gold.json
        base_name = os.path.splitext(pdf_file)[0]
        gold_file = f"{base_name}_gold.json"
        gold_path = os.path.join(gold_folder, gold_file)

        if not os.path.exists(gold_path):
            gold_path = None
        else:
            files_with_gold_standard += 1

        # Process the PDF
        result = process_single_pdf(pdf_path, gold_path)
        all_results.append(result)

        # Print detailed results
        print_detailed_results(result)

        # Update statistics
        if result['success']:
            successful_processes += 1
            total_completeness += result['completeness']
            if gold_path:  # Only count accuracy if we have gold standard
                total_accuracy += result['accuracy']

    # Print overall summary
    print("\n" + "=" * 70)
    print("📊 OVERALL EVALUATION SUMMARY")
    print("=" * 70)

    print(f"📁 Total files processed: {len(pdf_files)}")
    print(f"✅ Successfully processed: {successful_processes}")
    print(f"❌ Failed processing: {len(pdf_files) - successful_processes}")
    print(f"📋 Files with gold standard: {files_with_gold_standard}")

    if successful_processes > 0:
        avg_completeness = total_completeness / successful_processes
        print(f"\n📈 Average Completeness: {avg_completeness:.2%}")

        if files_with_gold_standard > 0:
            avg_accuracy = total_accuracy / files_with_gold_standard
            print(f"📊 Average Accuracy: {avg_accuracy:.2%}")
        else:
            print("📊 Average Accuracy: N/A (no gold standards found)")

    # Save detailed results to JSON
    output_file = "/Users/ormeiri/Desktop/KPMGassignment/KPMGasasignment/evaluation_results_hybrid.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Detailed results saved to: {output_file}")

    # Performance breakdown
    print(f"\n🎯 PERFORMANCE BREAKDOWN")
    print("-" * 40)
    accuracy_ranges = {'Perfect (100%)': 0, 'Excellent (90-99%)': 0, 'Good (80-89%)': 0,
                       'Fair (70-79%)': 0, 'Poor (<70%)': 0}
    completeness_ranges = {'Complete (100%)': 0, 'High (90-99%)': 0, 'Medium (70-89%)': 0,
                           'Low (50-69%)': 0, 'Very Low (<50%)': 0}

    for result in all_results:
        if result['success']:
            # Categorize accuracy
            acc = result['accuracy']
            if acc == 1.0:
                accuracy_ranges['Perfect (100%)'] += 1
            elif acc >= 0.9:
                accuracy_ranges['Excellent (90-99%)'] += 1
            elif acc >= 0.8:
                accuracy_ranges['Good (80-89%)'] += 1
            elif acc >= 0.7:
                accuracy_ranges['Fair (70-79%)'] += 1
            else:
                accuracy_ranges['Poor (<70%)'] += 1

            # Categorize completeness
            comp = result['completeness']
            if comp == 1.0:
                completeness_ranges['Complete (100%)'] += 1
            elif comp >= 0.9:
                completeness_ranges['High (90-99%)'] += 1
            elif comp >= 0.7:
                completeness_ranges['Medium (70-89%)'] += 1
            elif comp >= 0.5:
                completeness_ranges['Low (50-69%)'] += 1
            else:
                completeness_ranges['Very Low (<50%)'] += 1

    print("Accuracy Distribution:")
    for range_name, count in accuracy_ranges.items():
        if files_with_gold_standard > 0:
            percentage = (count / files_with_gold_standard) * 100
            print(f"  {range_name}: {count} files ({percentage:.1f}%)")

    print("\nCompleteness Distribution:")
    for range_name, count in completeness_ranges.items():
        if successful_processes > 0:
            percentage = (count / successful_processes) * 100
            print(f"  {range_name}: {count} files ({percentage:.1f}%)")


if __name__ == "__main__":
    run_evaluation()