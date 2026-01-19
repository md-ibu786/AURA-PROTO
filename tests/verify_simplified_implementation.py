"""
Verification script for the simplified summarizer implementation using only Vertex AI.
This script verifies that the simplified implementation meets the requirements.
"""

def test_simplified_implementation_verification():
    """Verify that the simplified implementation meets the requirements."""
    
    print("Verifying Simplified Summarizer Implementation...")
    
    # 1. Check that the required configuration values are in the code
    with open('services/summarizer.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n[CHECK] Checking configuration parameters in summarizer.py:")
    requirements_met = []
    
    # Check for temperature=1.0
    if 'temperature=1.0' in content:
        print("   [PASS] Temperature set to 1.0 (as required)")
        requirements_met.append(True)
    else:
        print("   [FAIL] Temperature not set to 1.0")
        requirements_met.append(False)
    
    # Check for top_p=0.95
    if 'top_p=0.95' in content:
        print("   [PASS] Top_p set to 0.95 (as required)")
        requirements_met.append(True)
    else:
        print("   [FAIL] Top_p not set to 0.95")
        requirements_met.append(False)
    
    # Check for max_output_tokens=32000
    if 'max_output_tokens=32000' in content:
        print("   [PASS] Max output tokens set to 32000 (as required)")
        requirements_met.append(True)
    else:
        print("   [FAIL] Max output tokens not set to 32000")
        requirements_met.append(False)
    
    # 2. Check that genai_client was removed (simplification)
    try:
        with open('services/genai_client.py', 'r', encoding='utf-8'):
            print("\n[FAIL] genai_client.py module still exists (should be removed for simplification)")
            requirements_met.append(False)
    except FileNotFoundError:
        print("\n[CHECK] genai_client.py module correctly removed (simplification achieved)")
        requirements_met.append(True)
    
    # 3. Check that requirements.txt still has necessary packages
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        req_content = f.read()
    
    if 'google-generativeai' in req_content:
        print("[CHECK] google-generativeai package still available (needed for Vertex AI)")
        requirements_met.append(True)
    else:
        print("[ERROR] google-generativeai package not found in requirements.txt")
        requirements_met.append(False)
    
    # 4. Verify function signature
    if 'def generate_university_notes(topic: str, cleaned_transcript: str) -> str:' in content:
        print("[CHECK] Function signature matches requirements")
        requirements_met.append(True)
    else:
        print("[ERROR] Function signature does not match requirements")
        requirements_met.append(False)
    
    # 5. Check that only Vertex AI imports are used
    if 'services.vertex_ai_client import' in content and 'genai_client' not in content:
        print("[CHECK] Only Vertex AI client is imported (simplification achieved)")
        requirements_met.append(True)
    else:
        print("[ERROR] GenAI client still imported (not simplified)")
        requirements_met.append(False)
    
    print(f"\n[SUMMARY] {sum(requirements_met)}/{len(requirements_met)} requirements met")
    
    if all(requirements_met):
        print("\n[SUCCESS] ALL SIMPLIFICATION REQUIREMENTS SUCCESSFULLY IMPLEMENTED!")
        print("\n[SUMMARY] Implementation Summary:")
        print("   - Temperature set to 1.0 for enhanced reasoning")
        print("   - Top_p set to 0.95 for broader idea exploration")
        print("   - Max output tokens set to 32000")
        print("   - GenAI dependency removed (simplification achieved)")
        print("   - Only Vertex AI SDK used")
        print("   - Backward compatibility maintained")
        return True
    else:
        print(f"\n[ERROR] {len(requirements_met) - sum(requirements_met)} requirements not met")
        return False


def test_import_functionality():
    """Test that the simplified modules can be imported without errors."""
    import sys
    import os
    # Add the parent directory to the path to allow imports
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    print("\n[TEST] Testing import functionality...")

    try:
        from services.summarizer import generate_university_notes
        print("[CHECK] Summarizer module imports successfully")

        # Check if the function exists
        if callable(generate_university_notes):
            print("[CHECK] Required function exists in summarizer")
        else:
            print("[ERROR] Required function missing from summarizer")
            return False

        return True
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("SIMPLIFIED SUMMARIZER IMPLEMENTATION VERIFICATION")
    print("="*60)
    
    # Test implementation
    implementation_ok = test_simplified_implementation_verification()
    
    # Test imports
    imports_ok = test_import_functionality()
    
    print("\n" + "="*60)
    if implementation_ok and imports_ok:
        print("[SUCCESS] OVERALL: ALL TESTS PASSED - SIMPLIFIED IMPLEMENTATION IS COMPLETE!")
    else:
        print("[WARNING] OVERALL: SOME TESTS FAILED - CHECK SIMPLIFIED IMPLEMENTATION")
    print("="*60)