import unittest
import importlib
from unittest.mock import Mock, patch, MagicMock
from services.summarizer import generate_university_notes


class TestSummarizer(unittest.TestCase):
    """Test suite for the summarizer functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.sample_topic = "Introduction to Machine Learning"
        self.sample_transcript = "Machine learning is a subset of artificial intelligence. It involves algorithms that can learn from data."

    @patch('services.summarizer.get_genai_model')
    @patch('services.summarizer.get_model')
    def test_generate_university_notes_with_genai_available(self, mock_get_model, mock_get_genai_model):
        """Test that the function uses genai when available."""
        # Mock the genai model response
        mock_genai_model = Mock()
        mock_response = Mock()
        mock_response.text = "Mocked university notes content"
        mock_genai_model.generate_content.return_value = mock_response
        mock_get_genai_model.return_value = mock_genai_model
        
        # Mock the fallback vertexai model (should not be used)
        mock_vertexai_model = Mock()
        mock_get_model.return_value = mock_vertexai_model

        result = generate_university_notes(self.sample_topic, self.sample_transcript)

        # Verify that genai model was used
        mock_get_genai_model.assert_called_once_with("gemini-3-flash-preview")
        mock_genai_model.generate_content.assert_called_once()
        self.assertEqual(result, "Mocked university notes content")

    @patch('services.summarizer.get_genai_model')
    @patch('services.summarizer.get_model')
    @patch('services.summarizer.GenerationConfig')
    def test_generate_university_notes_fallback_vertexai(self, mock_generation_config, mock_get_model, mock_get_genai_model):
        """Test that the function falls back to vertexai when genai is not available."""
        # Mock genai to return None (not available)
        mock_get_genai_model.return_value = None
        
        # Mock the vertexai model and response
        mock_vertexai_model = Mock()
        mock_response = Mock()
        mock_response.text = "Fallback university notes content"
        mock_get_model.return_value = mock_vertexai_model
        
        # Mock the generate_content function
        with patch('services.summarizer.generate_content') as mock_generate_content:
            mock_generate_content.return_value = mock_response
            
            result = generate_university_notes(self.sample_topic, self.sample_transcript)

            # Verify that genai was tried first but returned None
            mock_get_genai_model.assert_called_once_with("gemini-3-flash-preview")
            
            # Verify that vertexai was used as fallback
            mock_get_model.assert_called_once_with(model_name="models/gemini-3-flash-preview")
            mock_generate_content.assert_called_once()
            
            # Verify that the correct parameters were used
            mock_generation_config.assert_called_with(temperature=1.0, top_p=0.95, max_output_tokens=32000)
            
            self.assertEqual(result, "Fallback university notes content")

    @patch('services.summarizer.get_genai_model')
    def test_generate_university_notes_genai_exception_handling(self, mock_get_genai_model):
        """Test exception handling when genai is available but fails."""
        # Mock the genai model to raise an exception
        mock_genai_model = Mock()
        mock_genai_model.generate_content.side_effect = Exception("API Error")
        mock_get_genai_model.return_value = mock_genai_model

        result = generate_university_notes(self.sample_topic, self.sample_transcript)

        # Verify that the error is handled gracefully
        self.assertTrue(result.startswith("Note Generation Failed:"))

    @patch('services.summarizer.get_genai_model')
    @patch('services.summarizer.get_model')
    @patch('services.summarizer.generate_content')
    def test_generate_university_notes_vertexai_exception_handling(self, mock_generate_content, mock_get_model, mock_get_genai_model):
        """Test exception handling when vertexai is used but fails."""
        # Mock genai to return None (not available)
        mock_get_genai_model.return_value = None
        
        # Mock the vertexai model
        mock_vertexai_model = Mock()
        mock_get_model.return_value = mock_vertexai_model
        
        # Make generate_content raise an exception
        mock_generate_content.side_effect = Exception("Vertex AI Error")

        result = generate_university_notes(self.sample_topic, self.sample_transcript)

        # Verify that the error is handled gracefully
        self.assertTrue(result.startswith("Note Generation Failed:"))

    def test_generate_university_notes_function_signature(self):
        """Test that the function has the correct signature."""
        import inspect
        sig = inspect.signature(generate_university_notes)
        params = list(sig.parameters.keys())
        
        self.assertEqual(len(params), 2)
        self.assertIn('topic', params)
        self.assertIn('cleaned_transcript', params)
        
        # Verify return annotation if present
        self.assertEqual(sig.return_annotation, str)


class TestGenAIClient(unittest.TestCase):
    """Test suite for the genai client functionality."""
    
    @patch.dict('sys.modules', {
        'google.genai': None,  # Simulate google.genai not installed
        'google.generativeai': None  # Simulate google.generativeai not installed
    })
    def test_genai_client_import_error_handling(self):
        """Test that genai_client handles import errors gracefully."""
        # Force reimport of the module to trigger the import logic
        import sys
        if 'services.genai_client' in sys.modules:
            del sys.modules['services.genai_client']

        # Import fresh
        from services import genai_client

        # Verify that GENAI_AVAILABLE is False when package is not available
        self.assertFalse(genai_client.GENAI_AVAILABLE)
    
    @patch('services.genai_client.genai')
    def test_get_genai_model_success(self, mock_genai_module):
        """Test successful retrieval of genai model."""
        from services import genai_client
        
        # Mock the API key configuration
        mock_genai_module.configure = Mock()
        
        # Mock the GenerativeModel
        mock_model_instance = Mock()
        mock_genai_module.GenerativeModel.return_value = mock_model_instance
        
        # Set GENAI_AVAILABLE to True for this test
        original_available = genai_client.GENAI_AVAILABLE
        genai_client.GENAI_AVAILABLE = True
        
        try:
            result = genai_client.get_genai_model("test-model")
            
            # Verify the model was created
            mock_genai_module.GenerativeModel.assert_called_once_with("test-model")
            self.assertEqual(result, mock_model_instance)
        finally:
            # Restore original value
            genai_client.GENAI_AVAILABLE = original_available


if __name__ == '__main__':
    unittest.main()