import json
import re

from services.vertex_ai_client import (
    GenerationConfig,
    block_none_safety_settings,
    generate_content,
    get_model,
)


def clean_and_parse_json(text: str) -> dict:
    """
    Robustly parse JSON from LLM output that may contain markdown or extra text.
    
    Args:
        text: The raw text from the LLM which may contain JSON.
        
    Returns:
        Parsed JSON as a dictionary.
        
    Raises:
        json.JSONDecodeError: If no valid JSON can be extracted.
    """
    # First, try parsing directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Remove markdown code blocks if present
    # Pattern matches ```json ... ``` or ``` ... ```
    code_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(code_block_pattern, text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find raw JSON object by matching outermost braces
    brace_start = text.find('{')
    brace_end = text.rfind('}')
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start:brace_end + 1])
        except json.JSONDecodeError:
            pass
    
    # If all else fails, raise the original error
    raise json.JSONDecodeError("Could not extract valid JSON from response", text, 0)


def transform_transcript(topic: str, transcript: str) -> str:
    """
    Transform the given transcript using a specified generative model.

    Args:
        transcript (str): The raw transcript text to be transformed.

    Returns:
        str: The transformed transcript.
    """
    
    # usage of models/gemini-3-flash-preview
    model = get_model(model_name="models/gemini-3-flash-preview")

    
    # define the prompt for transformation
    # include the raw transcript explicitly in the prompt so the model can process it
    prompt = f"""
        SYSTEM ROLE:
        You are an Elite Academic Editor and Content Curator. Your primary function is to transform raw, noisy audio transcripts into pristine, high-fidelity lecture notes. You possess a deep understanding of academic discourse and are capable of distinguishing between core educational content and conversational noise.

        INPUT DATA:
        1. *Raw Transcript:* Begin the section below with the raw transcript provided for processing.

        RAW TRANSCRIPT:
        {transcript}

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
    response = generate_content(
        model,
        prompt,
        generation_config=GenerationConfig(temperature=0.0, max_output_tokens=32000),
        safety_settings=block_none_safety_settings(),
    )

    response_text = getattr(response, "text", None)
    if not response_text:
        if getattr(response, "prompt_feedback", None) and getattr(response.prompt_feedback, "block_reason", None):
            raise ValueError(f"Gemini blocked the prompt. Reason: {response.prompt_feedback.block_reason}")

        # Handle empty response (likely due to strict filtering)
        candidates = getattr(response, "candidates", None) or []
        if candidates and getattr(candidates[0], "finish_reason", None) == 1:
            return "The model filtered out all content. The input might not match the strict academic criteria or the target topic."

        finish_reason = getattr(candidates[0], "finish_reason", None) if candidates else "Unknown"
        raise ValueError(f"Gemini returned no content. Finish reason: {finish_reason}")

    clean_transcript = response_text

    # prompt for audit (build schema separately to avoid f-string brace issues)
    schema_text = json.dumps(
            {
                    "final_text": "string (The fully polished, approved text content)",
                    "flags": [
                            {
                                    "type": "student_interruption | off_topic | administrative_chatter | logical_break | grammar_fix",
                                    "snippet": "string (The exact text segment you removed or fixed)",
                                    "severity": "low | high",
                                    "message": "string (Why this was flagged/removed)",
                            }
                    ],
                    "is_clean": "boolean (true if flags is empty or only contains minor grammar fixes; false if major deletions occurred)",
                    "confidence_score": "float (0.0 to 1.0, representing the semantic coherence of the final result)",
            },
            indent=2,
    )
    audit_prompt = f"""
            ### SYSTEM ROLE
            You are a Senior Academic QA Specialist and Logic Auditor. Your mandate is to rigorously validate processed lecture transcripts for structural integrity, thematic relevance, and absolute cleanliness. You are the final quality gate before publication.
            ### INPUT DATA
            1. **Target Topic:** "{topic}"
            2. **Candidate Transcript:** A text block processed by a cleaning algorithm.
            ### AUDIT PROTOCOL
            You must analyze the text against three strict quality vectors:
            #### 1. The "Ghost" Vector (Artifact Detection)
            - Scan for residual traces of unauthorized speakers (students, audience).
            - Detect and flag administrative logistical chatter (e.g., "Can everyone see the board?", "Assignment due dates", "Is this on the exam?").
            - **Constraint:** A clean transcript contains ZERO administrative or conversational metadata.
            #### 2. The Relevance Vector (Topic Fidelity)
            - Measure the semantic distance between the text and the **Target Topic**.
            - Flag substantial deviations (e.g., a 200-word story about the lecturer's vacation).
            - **Note:** Brief illustrative examples *are* permitted; total topic drift is not.
            #### 3. The Logic Vector (Cohesion Analysis)
            - Detect "Frankenstein sentences" (sentences stitched together incorrectly during cleaning).
            - Identify logical gaps where an important premise seems missing (likely due to over-aggressive filtering).
            - Check for sentence fragments or grammar failures.
            ### PROCESSING & REPAIR RULES
            - **If the text is clean:** Return it exactly as is.
            - **If minor issues exist (punctuation, obvious fragments):** You are authorized to silently repair them in the `final_text` output.
            - **If major issues exist (student interruptions, off-topic rants):** You must EXCISE the offending segment from `final_text` and log it in the `flags` array.
            ### OUTPUT CONFIGURATION (Strict JSON)
            You must return **valid, parsable JSON**. Do not include markdown fencing (```json) or conversational preamble.
            **JSON Schema:**
            {schema_text}
            ### BEGIN AUDIT
            candidate_transcript:
            {clean_transcript}
            """
        
    # perform the audit
    audit_response = generate_content(
        model,
        audit_prompt,
        generation_config=GenerationConfig(temperature=0.0, max_output_tokens=32000),
        safety_settings=block_none_safety_settings(),
    )

    audit_text = getattr(audit_response, "text", None)
    if not audit_text:
        candidates = getattr(audit_response, "candidates", None) or []
        finish_reason = getattr(candidates[0], "finish_reason", None) if candidates else "Unknown"
        raise ValueError(f"Gemini blocked the audit content. Finish reason: {finish_reason}")

    response = audit_text

    try:
        result = clean_and_parse_json(response)


        # This 'final_text' is what goes into your database
        final_output = result['final_text']

        return final_output

    except json.JSONDecodeError:
        return "Error: Model failed to return valid JSON."
