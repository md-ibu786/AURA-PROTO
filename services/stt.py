"""
Speech-to-Text Backend ModuleTTThis module provides the backend processing functionality for audio files.
Currently implements a placeholder interface for audio file processing.
"""
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

def process_audio_file(
    audio_input: Union[BinaryIO, bytes, io.BytesIO]
) -> str:
    """
    Process an audio file and return a confirmation message.

    Args:
        audio_input: A file-like object (from Streamlit's file uploader) 
                    or raw bytes containing audio data

    Returns:
        str: A confirmation message indicating successful processing.

    Note:
        This is currently a placeholder function. Actual speech-to-text
        logic will be implemented in future iterations.
    """
    
    # upload the audio file using Google Generative AI API
    audio_file = genai.upload_file(audio_input, mime_type="audio/wav")
    
    # usage of models/gemini-2.5-flash
    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
    
    # define the prompt for transcription
    prompt = """
        ROLE:
        You are a precision transcription engine specialized in academic lectures. Your sole function is to convert the provided audio stream into text with 100% fidelity.

        TASK:
        Transcribe the accompanying audio file of a university lecture exactly as spoken.

        STRICT CONSTRAINTS (MUST FOLLOW):
        1. VERBATIM ONLY: Do not summarize, condense, or capture "key points." Write down every word spoken by the lecturer.
        2. NO HALLUCINATION: If a segment is inaudible or unintelligible, mark it as [INAUDIBLE]. Do not invent words to complete sentences.
        3. NO FILLER ADDITIONS: Do not add introductory phrases like "Here is the transcript" or "The lecturer says." Start directly with the first spoken word.
        4. PRESERVE CONTEXT: Maintain the exact phrasing and terminology used by the lecturer, even if it seems grammatically imperfect. Do not "autocorrect" the lecturer's speech.
        5. FORMATTING: Output the text as a continuous stream or naturally paragraphed text based on the speaker's pauses. Do not use bullet points or markdown headers unless the speaker explicitly dictates them.

        OUTPUT:
        Produce the raw transcript only.
        
        Begin!!
    """
    
    # generate content using the uploaded audio file
    # deterministic (recommended for transcription)
    api_response = model.generate_content(
        [audio_file, prompt],
        generation_config={"temperature": 0.0},
        request_options={"timeout": 600},
        safety_settings=[
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    )

    if not api_response.parts:
        # Handle empty response (silence)
        if api_response.candidates and api_response.candidates[0].finish_reason == 1:
            return "[SILENCE]"

        raise ValueError(f"Gemini blocked the transcription. Finish reason: {api_response.candidates[0].finish_reason if api_response.candidates else 'Unknown'}")

    response = api_response.text
    
    
    # Return success message
    return response
