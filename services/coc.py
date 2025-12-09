import google.generativeai as genai
from typing import Union, BinaryIO
import io
import os
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Retrieve the API key from environment variables
LLM_KEY = os.getenv("LLM_KEY")

# Configure the Google Generative AI API with your API key
genai.configure(api_key=LLM_KEY)
