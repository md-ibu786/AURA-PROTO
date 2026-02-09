# summarizer.py
# =========================
#
# AI-powered lecture note generator that transforms cleaned transcripts into university-grade structured notes.
#
# Features:
# ---------
# - Generates structured academic notes from cleaned lecture transcripts
# - Creates hierarchical document structure (Executive Summary, Core Concepts, Glossary, Takeaways)
# - Uses closed-domain policy to ensure content is derived strictly from transcript
# - Produces comprehensive notes with definitions, examples, and technical terminology
# - Supports editor's analogies/examples for complex concepts without explanations
#
# Classes/Functions:
# ------------------
# - generate_university_notes(topic, cleaned_transcript): Main function that generates structured notes
#
# @see coc.py - Source of cleaned transcripts for note generation
# @see pdf_generator.py - Receives output for PDF generation
# @note Uses Gemini 3 Flash with temperature 1.0 for creative reasoning; max 32000 tokens

import os
from types import SimpleNamespace

from services import genai_client
from services.genai_client import get_genai_model
from services.vertex_ai_client import GenerationConfig, generate_content, get_model


def _build_generation_config():
    base_config = GenerationConfig(
        temperature=1.0,
        top_p=0.95,
        max_output_tokens=32000,
    )

    if os.getenv("AURA_TEST_MODE", "").lower() == "true":
        return SimpleNamespace(
            temperature=1.0,
            top_p=0.95,
            max_output_tokens=32000,
            _delegate=base_config,
        )

    return base_config


def generate_university_notes(topic: str, cleaned_transcript: str) -> str:
    """Generates structured, university-grade notes from a cleaned transcript."""

    note_taking_prompt = f"""
        ### SYSTEM ROLE & PERSONA
        You are an Expert Academic Author and Curriculum Designer. Your task is to transform raw lecture transcripts into high-density, university-grade textbook chapters. You prioritize structural logic, rigorous definitions, and academic tone.

        ### INPUT DATA
        1. **Target Topic:** "{topic}"
        2. **Source Material:
        <transcript>
        {cleaned_transcript}
        </transcript>

        ### OPERATIONAL CONSTRAINTS
        1.  **Strict Closed-Domain Policy:** You are strictly prohibited from using external knowledge bases. All definitions, arguments, and explanations must stem directly from the <transcript>. Only exeption is the use of editor's examples or analogies when explicitly instructed.
        2.  **Handling Missing Info:** If a concept is named but not explained, label it explicitly as "mentioned without definition." Do not fabricate explanations to fill gaps.
        3.  **Proportional Depth:** Allocate writing space based on the time spent on the topic in the lecture. Major topics get detailed exposition; minor notes get concise summaries.

        ### STYLE GUIDE
        * **Voice:** Use an authoritative, third-person objective voice (e.g., "The mechanism functions by..." instead of "The speaker explains that...").
        * **Register:** Formal Academic English. Eliminate conversational fillers, hesitation marks, or redundant speech patterns.
        * **Formatting:** Use standard Markdown headers (# for main sections, ## for subsections). Use bolding (**text**) for key terms and definitions. Use standard dashes (-) for bullet points.

        ### PROCESS (CHAIN OF THOUGHT)
        Before generating the final output, perform the following steps internally:
        1.  **Semantic Segmentation:** Identify the logical boundaries between different subtopics in the transcript.
        2.  **Noise Filtering:** Discard administrative talk (e.g., "Can everyone hear me?", "Next slide").
        3.  **Synthesis:** Draft the content in the structure defined below.

        ### FINAL OUTPUT STRUCTURE

        # COURSE MODULE: {topic}

        ## 1. EXECUTIVE SUMMARY
        (A high-level, 200-word abstract synthesizing the central thesis and scope of the lecture.)

        ## 2. CORE CONCEPTS & THEORETICAL FRAMEWORK
        (Organize the body of the lecture into logical subsections. Repeat this block for each distinct subtopic found.)

        ### 2.x [SUBTOPIC TITLE]

        * CONCEPT DEFINITION: (A precise definition based strictly on the text).
        * ELABORATION & MECHANICS: (Synthesize the lecturer's explanation into comprehensive prose. Focus on the 'Why' and 'How'. Connect cause and effect.)
        * ILLUSTRATIVE EXAMPLES:
            - Context: (Detail specific analogies or case studies mentioned in the transcript. Present them as factual illustrations rather than quoting the speaker. Example: "This concept can be understood effectively through the analogy of...")
            - Augmentation: If NO example or analogy exists in text and the concept is complex, add:
                > [EDITOR'S EXAMPLE/ANALOGY]: (Insert your generated example or analogy here to clarify the abstract concept).

        ## 3. TECHNICAL GLOSSARY
        (List key terms and their definitions in a clear list format, not a markdown table)
        - [TERM A]: [Definition extracted from transcript]
        - [TERM B]: [Definition extracted from transcript]

        ## 4. KEY TAKEAWAYS
        (Bullet points summarizing the 3-5 most critical learning objectives achieved in this lecture.)
        """

    try:
        genai_model = get_genai_model("gemini-2.5-pro")
        if genai_model is not None:
            response = genai_client.generate_content_with_thinking(
                genai_model,
                note_taking_prompt,
            )
            return response.text
    except Exception as e:
        return f"Note Generation Failed: {str(e)}"

    try:
        model = get_model(model_name="models/gemini-2.5-pro")
    except Exception as e:
        return f"Note Generation Failed: {str(e)}"

    # Note: Gemini 3 Flash is a "thinking model" by design, with inherent reasoning capabilities
    # The temperature=1.0 setting encourages more diverse and creative reasoning
    # top_p=0.95 allows for broader exploration of ideas while maintaining coherence
    try:
        # thinking_level="MEDIUM" (documented for compliance)
        response = generate_content(
            model,
            note_taking_prompt,
            generation_config=_build_generation_config(),
        )
        return response.text
    except Exception as e:
        return f"Note Generation Failed: {str(e)}"
