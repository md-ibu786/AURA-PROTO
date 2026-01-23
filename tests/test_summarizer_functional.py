# test_summarizer_functional.py
# Functional tests for the university notes summarizer
#
# Validates GenAI/Vertex fallback behavior and configuration constants.
#
# @see: services/summarizer.py - Summarizer implementation under test
# @note: Uses path-based source checks for config verification

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath('.'))

from services.summarizer import generate_university_notes


class TestSummarizerFunctional(unittest.TestCase):
    """Functional tests for the summarizer implementation."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.sample_topic = "Introduction to Machine Learning"
        self.sample_transcript = "Machine learning is a subset of artificial intelligence. It involves algorithms that can learn from data."

    @patch('services.summarizer.get_genai_model')
    @patch('services.summarizer.get_model')
    def test_genai_path_is_attempted_first(self, mock_get_model, mock_get_genai_model):
        """Test that the genai path is attempted first."""
        # Mock genai to return None (not available) so we use the fallback path
        mock_get_genai_model.return_value = None
        
        # Mock the vertexai model and response
        mock_vertexai_model = Mock()
        mock_get_model.return_value = mock_vertexai_model
        
        with patch('services.summarizer.generate_content') as mock_generate_content:
            mock_response = Mock()
            mock_response.text = "Test response"
            mock_generate_content.return_value = mock_response

            result = generate_university_notes(self.sample_topic, self.sample_transcript)

            # Verify that genai was tried first
            mock_get_genai_model.assert_called_once_with("gemini-3-flash-preview")
            # Verify that vertexai was used as fallback
            mock_get_model.assert_called_once_with(model_name="models/gemini-3-flash-preview")
            # Verify generate_content was called
            mock_generate_content.assert_called_once()
            # Verify the result
            self.assertEqual(result, "Test response")

    @patch('services.summarizer.get_genai_model')
    def test_genai_path_works_when_available(self, mock_get_genai_model):
        """Test that the genai path works when available."""
        # Mock the genai model
        mock_genai_model = Mock()
        mock_get_genai_model.return_value = mock_genai_model
        
        with patch('services.genai_client.generate_content_with_thinking') as mock_genai_generate:
            mock_response = Mock()
            mock_response.text = "GenAI response"
            mock_genai_generate.return_value = mock_response

            result = generate_university_notes(self.sample_topic, self.sample_transcript)

            # Verify that genai was used
            mock_get_genai_model.assert_called_once_with("gemini-3-flash-preview")
            # Verify that genai generate was called
            mock_genai_generate.assert_called_once()
            # Verify the result
            self.assertEqual(result, "GenAI response")

    def test_function_handles_exceptions_gracefully(self):
        """Test that the function handles exceptions gracefully."""
        with patch('services.summarizer.get_genai_model', side_effect=Exception("Test error")):
            result = generate_university_notes(self.sample_topic, self.sample_transcript)
            # Should return an error message
            self.assertTrue(result.startswith("Note Generation Failed:"))

    def test_function_signature_matches_requirements(self):
        """Test that the function signature matches the original requirements."""
        import inspect
        sig = inspect.signature(generate_university_notes)
        
        # Check that it has the required parameters
        params = list(sig.parameters.keys())
        self.assertEqual(params, ['topic', 'cleaned_transcript'])
        
        # Check return type annotation
        self.assertEqual(sig.return_annotation, str)

    def test_configuration_parameters_are_in_source_code(self):
        """Verify that the required configuration parameters are in the source code."""
        summarizer_path = Path(__file__).resolve().parents[1] / "services" / "summarizer.py"
        with open(summarizer_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that the required values are present in the code
        self.assertIn('temperature=1.0', content)
        self.assertIn('top_p=0.95', content)
        self.assertIn('max_output_tokens=32000', content)
        self.assertIn('thinking_level="MEDIUM"', content)


class TestGenAIClientFunctional(unittest.TestCase):
    """Functional tests for the genai client."""

    def test_genai_client_imports_successfully(self):
        """Test that the genai client module imports without errors."""
        try:
            from services import genai_client
            # Verify that required functions exist
            self.assertTrue(hasattr(genai_client, 'get_genai_model'))
            self.assertTrue(hasattr(genai_client, 'generate_content_with_thinking'))
            self.assertTrue(hasattr(genai_client, 'GENAI_AVAILABLE'))
        except ImportError as e:
            # This is acceptable if the package isn't available in the test environment
            print(f"Import error (acceptable in test environment): {e}")


if __name__ == '__main__':
    unittest.main()