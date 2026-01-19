import unittest
from unittest.mock import Mock, patch, MagicMock
from services.summarizer import generate_university_notes


class TestSummarizerIntegration(unittest.TestCase):
    """Integration tests for the summarizer functionality focusing on configuration."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.sample_topic = "Introduction to Machine Learning"
        self.sample_transcript = "Machine learning is a subset of artificial intelligence. It involves algorithms that can learn from data."

    @patch('services.summarizer.get_genai_model')
    @patch('services.summarizer.get_model')
    @patch('services.summarizer.generate_content')
    def test_configuration_parameters_used_correctly(self, mock_generate_content, mock_get_model, mock_get_genai_model):
        """Test that the correct configuration parameters are used in the fallback scenario."""
        # Mock genai to return None (not available) so we use the fallback path
        mock_get_genai_model.return_value = None
        
        # Mock the vertexai model
        mock_vertexai_model = Mock()
        mock_get_model.return_value = mock_vertexai_model
        
        # Mock the response
        mock_response = Mock()
        mock_response.text = "Test university notes content"
        mock_generate_content.return_value = mock_response

        # Call the function
        result = generate_university_notes(self.sample_topic, self.sample_transcript)

        # Verify that genai was tried first
        mock_get_genai_model.assert_called_once_with("gemini-3-flash-preview")
        
        # Verify that vertexai was used as fallback
        mock_get_model.assert_called_once_with(model_name="models/gemini-3-flash-preview")
        
        # Verify that generate_content was called with the correct parameters
        self.assertEqual(mock_generate_content.call_count, 1)
        call_args = mock_generate_content.call_args
        self.assertIsNotNone(call_args)
        
        # Check that the GenerationConfig was called with the correct parameters
        # The config should be passed as a keyword argument
        if len(call_args) > 1 and 'generation_config' in call_args.kwargs:
            config = call_args.kwargs['generation_config']
            # Verify the attributes were set correctly
            self.assertEqual(config.temperature, 1.0)
            self.assertEqual(config.top_p, 0.95)
            self.assertEqual(config.max_output_tokens, 32000)
        
        self.assertEqual(result, "Test university notes content")

    def test_function_handles_different_input_types(self):
        """Test that the function can handle different types of inputs."""
        # Test with minimal valid inputs
        with patch('services.summarizer.get_genai_model') as mock_get_genai_model, \
             patch('services.summarizer.get_model') as mock_get_model, \
             patch('services.summarizer.generate_content') as mock_generate_content:
            
            mock_get_genai_model.return_value = None
            mock_vertexai_model = Mock()
            mock_get_model.return_value = mock_vertexai_model
            mock_response = Mock()
            mock_response.text = "Valid response"
            mock_generate_content.return_value = mock_response
            
            result = generate_university_notes("Test Topic", "This is a test transcript.")
            
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)

    def test_function_signature_and_return_type(self):
        """Test the function signature and return type."""
        import inspect
        sig = inspect.signature(generate_university_notes)
        
        # Check parameters
        params = list(sig.parameters.keys())
        self.assertEqual(params, ['topic', 'cleaned_transcript'])
        self.assertEqual(sig.return_annotation, str)


class TestConfigurationValues(unittest.TestCase):
    """Test that the configuration values match the requirements."""

    def test_required_temperature_and_top_p_values(self):
        """Verify that the required configuration values are used."""
        # These are the values that were specifically requested in the requirements
        expected_temperature = 1.0
        expected_top_p = 0.95
        expected_max_tokens = 32000
        
        # These values should be hardcoded in the function
        # We can't directly access them, but we can verify they're being used
        # by checking the implementation in the code
        import ast
        import inspect
        
        # Read the source code to verify the values are correct
        with open('services/summarizer.py', 'r') as f:
            source = f.read()
        
        # Parse the AST to find the configuration values
        tree = ast.parse(source)
        
        # Look for the temperature=1.0 assignment
        found_temp = False
        found_top_p = False
        found_tokens = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == 'temperature' and isinstance(keyword.value, ast.Constant) and keyword.value.value == 1.0:
                        found_temp = True
                    elif keyword.arg == 'top_p' and isinstance(keyword.value, ast.Constant) and keyword.value.value == 0.95:
                        found_top_p = True
                    elif keyword.arg == 'max_output_tokens' and isinstance(keyword.value, ast.Constant) and keyword.value.value == 32000:
                        found_tokens = True
        
        self.assertTrue(found_temp, "Temperature=1.0 should be in the code")
        self.assertTrue(found_top_p, "Top_p=0.95 should be in the code")
        self.assertTrue(found_tokens, "Max_output_tokens=32000 should be in the code")


if __name__ == '__main__':
    unittest.main()