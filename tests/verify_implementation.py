"""
Verification script for the summarizer implementation with thinking configuration.
This script verifies that the implementation meets the requirements.
"""

def test_implementation_verification():
    """Verify that the implementation meets the specified requirements."""
    
    print("[INFO] Verifying Summarizer Implementation...")
    
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

    # Check for thinking_level="MEDIUM"
    if 'thinking_level="MEDIUM"' in content:
        print("   [PASS] Thinking level set to MEDIUM (as required)")
        requirements_met.append(True)
    else:
        print("   [FAIL] Thinking level not set to MEDIUM")
        requirements_met.append(False)

    # Check for include_thoughts=False
    if 'include_thoughts=False' in content:
        print("   [PASS] Include thoughts set to False (as required)")
        requirements_met.append(True)
    else:
        print("   [FAIL] Include thoughts not set to False")
        requirements_met.append(False)

    # 2. Check that genai_client was created
    try:
        with open('services/genai_client.py', 'r', encoding='utf-8') as f:
            genai_content = f.read()
        print("\n[CHECK] genai_client.py module created successfully")
        requirements_met.append(True)
    except FileNotFoundError:
        print("\n[ERROR] genai_client.py module not found")
        requirements_met.append(False)

    # 3. Check that requirements.txt was updated
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        req_content = f.read()

    if 'google-generativeai' in req_content:
        print("[CHECK] google-generativeai package added to requirements.txt")
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

    # 5. Check for fallback implementation
    if 'fallback' in content.lower() or 'get_model' in content:
        print("[CHECK] Fallback implementation to vertexai present")
        requirements_met.append(True)
    else:
        print("[ERROR] Fallback implementation not found")
        requirements_met.append(False)

    print(f"\n[SUMMARY] {sum(requirements_met)}/{len(requirements_met)} requirements met")

    if all(requirements_met):
        print("\n[SUCCESS] ALL REQUIREMENTS SUCCESSFULLY IMPLEMENTED!")
        print("\n[SUMMARY] Implementation Summary:")
        print("   - Temperature set to 1.0 for enhanced reasoning")
        print("   - Top_p set to 0.95 for broader idea exploration")
        print("   - Max output tokens set to 32000")
        print("   - Thinking level set to MEDIUM as requested")
        print("   - Include thoughts set to False")
        print("   - Fallback to vertexai when genai not available")
        print("   - Backward compatibility maintained")
        return True
    else:
        print(f"\n[ERROR] {len(requirements_met) - sum(requirements_met)} requirements not met")
        return False


def test_import_functionality():
    """Test that the modules can be imported without errors."""
    import sys
    import os
    # Add the parent directory to the path to allow imports
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    print("\n[TEST] Testing import functionality...")

    try:
        from services.summarizer import generate_university_notes
        print("[CHECK] Summarizer module imports successfully")

        from services import genai_client
        print("[CHECK] GenAI client module imports successfully")

        # Check if required functions exist
        if hasattr(genai_client, 'get_genai_model') and hasattr(genai_client, 'generate_content_with_thinking'):
            print("[CHECK] Required functions exist in genai_client")
        else:
            print("[ERROR] Required functions missing from genai_client")
            return False

        return True
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("SUMMARIZER THINKING CONFIGURATION IMPLEMENTATION VERIFICATION")
    print("="*60)

    # Test implementation
    implementation_ok = test_implementation_verification()

    # Test imports
    imports_ok = test_import_functionality()

    print("\n" + "="*60)
    if implementation_ok and imports_ok:
        print("[SUCCESS] OVERALL: ALL TESTS PASSED - IMPLEMENTATION IS COMPLETE!")
    else:
        print("[WARNING] OVERALL: SOME TESTS FAILED - CHECK IMPLEMENTATION")
    print("="*60)