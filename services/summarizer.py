import google.generativeai as genai
import os
import dotenv

dotenv.load_dotenv()

# Retrieve the API key from environment variables
LLM_KEY = os.getenv("LLM_KEY")

# Configure the Google Generative AI API with your API key
genai.configure(api_key=LLM_KEY)

def generate_university_notes(topic: str, cleaned_transcript: str) -> str:
    """
    Generates structured, university-grade notes from a cleaned transcript.
    """
    # Use 2.5 Flash for superior text synthesis and formatting
    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
    
    # Define the detailed prompt for note generation
    note_taking_prompt = f"""
        ### SYSTEM ROLE & PERSONA
        You are an Expert Academic Author and Curriculum Designer. Your task is to transform raw lecture transcripts into high-density, university-grade textbook chapters. You prioritize structural logic, rigorous definitions, and academic tone.

        ### INPUT DATA
        1. **Target Topic:** "{topic}"
        2. **Source Material:**
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
        response = model.generate_content(
            note_taking_prompt,
            generation_config={"temperature": 0.3}, # Low temp = strict adherence to facts
            request_options={"timeout": 600}
        )
        return response.text
        
    except Exception as e:
        return f"Note Generation Failed: {str(e)}"