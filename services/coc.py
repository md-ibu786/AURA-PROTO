import google.generativeai as genai
import os
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Retrieve the API key from environment variables
LLM_KEY = os.getenv("LLM_KEY")

# Configure the Google Generative AI API with your API key
genai.configure(api_key=LLM_KEY)

def transform_transcript(topic: str, transcript: str) -> str:
    """
    Transform the given transcript using a specified generative model.

    Args:
        transcript (str): The raw transcript text to be transformed.

    Returns:
        str: The transformed transcript.
    """
    
    # usage of models/gemini-2.5-flash
    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
    
    # define the prompt for transformation
    # include the raw transcript explicitly in the prompt so the model can process it
    # limit transcript length to avoid prompt overflow (trim if very long)
    max_transcript_len = 40000
    safe_transcript = transcript
    if len(safe_transcript) > max_transcript_len:
        safe_transcript = safe_transcript[-max_transcript_len:]
        safe_transcript = "[TRUNCATED START]\n" + safe_transcript

    prompt = f"""
        SYSTEM ROLE:
        You are an Elite Academic Editor and Content Curator. Your primary function is to transform raw, noisy audio transcripts into pristine, high-fidelity lecture notes. You possess a deep understanding of academic discourse and are capable of distinguishing between core educational content and conversational noise.

        INPUT DATA:
        1. *Raw Transcript:* Begin the section below with the raw transcript provided for processing.

        RAW TRANSCRIPT:
        {safe_transcript}

        2. *Target Topic:* "{topic}"

        PROCESSING PIPELINE:
        You must process the input text through the following three distinct phases before generating output:

        PHASE 1: Speaker & Noise Isolation (The Filter)
        - *Identify the Primary Speaker (The Lecturer):* Isolate the main educational narrative.
        - *Eliminate "Student" Noise:* Aggressively remove all interruptions, questions, and comments made by the audience/students.
        - *Eliminate Administrative "Meta-Talk":* Remove all lecturer speech that is purely logistical or social (e.g., "Can you hear me?", "Turn to page 5", "The exam is on Tuesday", "Is the microphone working?").
        - *Context Handling:* If a student asks a question and the Lecturer answers with relevant educational content, retain the Lecturer's explanation but rephrase the opening so it stands alone as a declarative statement, removing the dependency on the deleted question.
        
        PHASE 2: Semantic Relevance (The Scope)
        - *Strict Topic Adherence:* Filter the remaining Lecturer text against the Target Topic: *"{topic}"*.
        - *Tangent Removal:* If the Lecturer digresses into personal anecdotes, unrelated subjects, or off-topic rants that do not contribute to the understanding of the Target Topic, excise them completely.
        
        PHASE 3: Syntactic Refinement (The Polish)
        - *Disfluency Removal:* Strip all verbal fillers (um, uh, like, you know, sort of).
        - *Grammar & Flow:* Correct sentence boundaries and grammatical errors caused by oral speech patterns. Convert run-on sentences into distinct, logical statements.
        - *Terminology Normalization:* Ensure technical terms are capitalized and spelled correctly within the context of the subject matter.
        - *NO SUMMARIZATION:* You are an Editor, not a Summarizer. Do not condense the information. Retain the full depth and detail of the lecture, but present it in written academic prose rather than spoken English.
        
        OUTPUT FORMAT:
        - *Format:* Return a single, continuous block of text (or naturally paragraphed text).
        - *Style:* Clean, professional, and textbook-quality.
        - *Forbidden Elements:*
          - DO NOT use speaker labels (e.g., "Lecturer:", "Student:").
          - DO NOT include timestamps.
          - DO NOT add introductory or concluding remarks (e.g., "Here is the cleaned text").
        
        Proceed now to process the input based on the Target Topic: *"{topic}"*.
        EXECUTION
    """
    
    # generate the transformed transcript with deterministic generation
    response = model.generate_text(prompt=prompt, temperature=0.0)

    return response.text