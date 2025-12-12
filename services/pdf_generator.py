try:
    from fpdf import FPDF
    FPDF_LIBRARY = 'fpdf'
except ImportError:
    try:
        from fpdf2 import FPDF
        FPDF_LIBRARY = 'fpdf2'
    except ImportError:
        raise ImportError("Neither fpdf nor fpdf2 libraries are available. Please install one of them.")

def preprocess_text_for_pdf(text):
    """
    Preprocess text to handle Unicode characters that may not be supported by FPDF's default encoding.
    Replaces problematic Unicode characters with ASCII equivalents.
    """
    if not text:
        return text

    # Define character replacements for common Unicode characters
    unicode_replacements = {
        '\u2014': '--',    # em dash -> double hyphen
        '\u2013': '-',     # en dash -> hyphen
        '\u2018': "'",     # left single quotation mark -> apostrophe
        '\u2019': "'",     # right single quotation mark -> apostrophe
        '\u201C': '"',     # left double quotation mark -> quote
        '\u201D': '"',     # right double quotation mark -> quote
        '\u2192': '->',    # right arrow -> hyphen +
        '\u2026': '...',   # horizontal ellipsis -> three dots
        '\u00A0': ' ',     # non-breaking space -> space
        '\u00AD': '',      # soft hyphen -> remove
        '\u200B': '',      # zero-width space -> remove
    }

    # Apply character replacements
    for unicode_char, replacement in unicode_replacements.items():
        text = text.replace(unicode_char, replacement)

    # For fpdf2, we can use Unicode directly with proper font configuration
    if FPDF_LIBRARY == 'fpdf2':
        return text

    # For original fpdf, ensure text is compatible with latin-1 encoding
    try:
        text.encode('latin-1')
        return text
    except UnicodeEncodeError:
        # If there are still problematic characters, replace them with '?'
        return text.encode('latin-1', 'replace').decode('latin-1')

class LectureNotesPDF(FPDF):
    def __init__(self, title_text):
        super().__init__()
        # Store the title passed during initialization
        self.title_text = title_text

    def header(self):
        """Standard header for every page"""
        # Set font: Helvetica bold 15
        self.set_font('Helvetica', 'B', 15)

        # Title is now handled in the body of the first page only
        pass

    def footer(self):
        """Standard footer for every page"""
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

def create_pdf(summary_text, title, output_filename="lecture_notes.pdf"):
    """
    Converts a summary string into a PDF with a dynamic header title.

    Args:
        summary_text (str): The summarized lecture text.
        title (str): The specific title of the lecture provided by the user.
        output_filename (str): The desired path/name for the PDF.
    """

    # Preprocess text to handle Unicode characters
    summary_text = preprocess_text_for_pdf(summary_text)
    title = preprocess_text_for_pdf(title)

    # Initialize PDF with the specific title
    pdf = LectureNotesPDF(title_text=title)

    pdf.alias_nb_pages()
    pdf.add_page()

    # Add Title to the first page
    pdf.set_font('Helvetica', 'B', 15)
    pdf.cell(0, 10, title, align='C')
    pdf.ln(20)

    pdf.set_font('Times', '', 12)

    def write_formatted_text(pdf_obj, text_line, line_height=6):
        """
        Parses text for **bold** markers and writes it to the PDF.
        """
        parts = text_line.split('**')
        for i, part in enumerate(parts):
            if i % 2 == 1:  # Odd indices are between ** and ** -> Bold
                pdf_obj.set_font('Times', 'B', 12)
                pdf_obj.write(line_height, part)
            else:           # Even indices are normal text
                pdf_obj.set_font('Times', '', 12)
                pdf_obj.write(line_height, part)

    # Parse and write content line by line
    lines = summary_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(4) # Small space for empty lines
            continue

        if line.startswith('# '):
            # Level 1 Header (Bold, Large)
            pdf.set_font('Helvetica', 'B', 16)
            pdf.multi_cell(0, 8, line[2:], align='L')
            pdf.set_font('Times', '', 12) # Reset to body font
        elif line.startswith('## '):
            # Level 2 Header (Bold, Medium)
            pdf.set_font('Helvetica', 'B', 14)
            pdf.multi_cell(0, 7, line[3:], align='L')
            pdf.set_font('Times', '', 12) # Reset to body font
        elif line.startswith('### '):
            # Level 3 Header (Bold, Small)
            pdf.set_font('Helvetica', 'B', 13)
            pdf.multi_cell(0, 6, line[4:], align='L')
            pdf.set_font('Times', '', 12) # Reset to body font
        else:
            # Body Text
            # Check for bullet points for indentation
            if line.startswith('- ') or line.startswith('* '):
                # Handle bullet point
                bullet_marker = line[0] + ' '
                content = line[2:]

                # Save current position
                original_x = pdf.get_x()
                original_margin = pdf.l_margin

                # Write bullet
                pdf.cell(5, 6, bullet_marker)

                # Indent for the content
                pdf.set_left_margin(original_margin + 5)

                # Write content with bold parsing
                write_formatted_text(pdf, content)

                # Restore margin and move to next line
                pdf.set_left_margin(original_margin)
                pdf.ln()
            else:
                # Normal paragraph
                write_formatted_text(pdf, line)
                pdf.ln()

    pdf.output(output_filename)
    return output_filename

'''title = "Artificial Intelligence Lecture"

summary_text = """# COURSE MODULE: Artificial intelligence

## 1. EXECUTIVE SUMMARY
Artificial Intelligence (AI) encompasses the simulation of human intelligence in machines, enabling them to think and learn. This field has evolved significantly, moving from early deterministic systems to sophisticated learning-based approaches. Initially, AI relied on explicit conditional programming, exemplified by decision trees and algorithms like Minimax in games such as Tic-Tac-Toe. However, the computational limitations of deterministic methods for complex problems spurred the development of Machine Learning. Machine Learning focuses on training computers to solve problems by learning from data, rather than explicit programming. Reinforcement Learning, a key method, allows agents to learn through feedback, balancing exploration of new possibilities with exploitation of known solutions. This progression led to Deep Learning, which frequently utilizes Neural Networks—computational models inspired by biological neural systems. Neural Networks learn parameters from vast datasets probabilistically, though their internal workings often remain a 'black box'. Modern advancements include Large Language Models (LLMs) like ChatGPT, which are built on Neural Networks and employ 'attention' mechanisms to process and generate text. LLMs are pre-trained on extensive data, but their probabilistic nature can lead to inaccuracies and 'hallucinations'.

## 2. CORE CONCEPTS & THEORETICAL FRAMEWORK

### 2.1 Defining Artificial Intelligence and its Early Manifestations
*   **CONCEPT DEFINITION:** **Artificial Intelligence (AI)** refers to the simulation of human intelligence in machines programmed to think and learn like humans. **Generative Artificial Intelligence** is a specific application that uses AI to create content.
*   **ELABORATION & MECHANICS:** AI capabilities allow for the development of applications that leverage machine intelligence for various purposes. While daily discussions about AI are recent, its presence in technology has been established for years.
*   **ILLUSTRATIVE EXAMPLES:**
    -   Context:
        -   **Spam filters** in email services (e.g., Gmail, Outlook) utilize AI algorithms to infer and filter spam, reducing the need for manual sorting.
        -   **Handwriting recognition** on tablets and phones employs AI to learn from diverse handwriting samples, adapting beyond specific individual styles.
        -   **Streaming services** (e.g., Netflix) use AI to analyze watch history and recommend similar shows or movies based on user preferences.
        -   **Voice assistants** (e.g., Siri, Alexa, Google Assistant) leverage AI to learn and respond to various human voices, adapting beyond their developers' voices.

### 2.2 Deterministic Approaches to Artificial Intelligence
*   **CONCEPT DEFINITION:** **Deterministic approaches** in early AI systems relied on explicit conditional code (e.g., if/else statements) to dictate actions, leading to predictable outcomes given specific inputs. **Decision trees** are a programming concept where a root node branches into different children based on yes/no decisions, translating human heuristics into code. The **Minimax algorithm** is a strategy used in game theory, particularly for two-player zero-sum games, where one player aims to maximize their score while the other aims to minimize it.
*   **ELABORATION & MECHANICS:** Games provide an excellent domain for discussing AI due to their well-defined rules and clear goals. Decision trees can be used to program AI behavior by mapping possible states and actions. However, the complexity of decision trees grows exponentially with the number of available moves. For games with vast numbers of possible states, such as chess or Go, deterministically calculating all future states within a reasonable timeframe becomes computationally infeasible. This limitation highlights that even advanced AI systems often rely on approximating correct answers rather than exhaustive computation.
*   **ILLUSTRATIVE EXAMPLES:**
    -   Context:
        -   **Arcade games (Pong and Breakout):** Early examples of AI. In Breakout, a decision tree might dictate paddle movement: move left if the ball is to the left, move right if it is to the right, otherwise keep it stationary. This logic translates directly into pseudocode using conditional statements.
        -   **Tic-Tac-Toe:** A 3x3 grid game where an optimal strategy can be derived using a decision tree and the Minimax algorithm. Game states are represented mathematically, with scores assigned to outcomes (e.g., -1 for an O win, +1 for an X win, 0 for a tie). The algorithm evaluates potential moves to choose the one leading to the best possible outcome. While Tic-Tac-Toe has a manageable 255,000 possible game states, more complex games like chess (over 85 billion ways to play the first four moves) or Go (266 quintillion ways) present significant challenges for deterministic computation.

### 2.3 Transition to Machine Learning: Overcoming Deterministic Limitations
*   **CONCEPT DEFINITION:** **Machine Learning** is a field aimed at writing code that teaches computers how to solve problems by learning from available training data, even when the correct answer is not explicitly known to the programmer.
*   **ELABORATION & MECHANICS:** The motivation for modern AI stems from the inherent limitations of deterministic programming. While earlier AI systems relied on explicit conditional code, true Artificial Intelligence involves machines learning and figuring out solutions independently, particularly when exhaustive deterministic computation is infeasible due to memory or time constraints. Machine Learning addresses this by enabling computers to acquire knowledge and skills through data-driven processes.
*   **ILLUSTRATIVE EXAMPLES:**
    -   Context: The general concept of a robot learning to perform a task like flipping a pancake or an agent learning to navigate a maze are introduced as examples of how machines can learn solutions rather than being explicitly programmed for every step.

### 2.4 Reinforcement Learning: Learning Through Feedback
*   **CONCEPT DEFINITION:** **Reinforcement Learning** is a method of training computers where an agent learns through feedback, such as rewards for positive behavior and punishments for negative behavior. The principle of **exploration versus exploitation** describes the dilemma an agent faces between utilizing its current knowledge to achieve known rewards (exploitation) and trying new actions to potentially discover higher rewards or better solutions (exploration).
*   **ELABORATION & MECHANICS:** In Reinforcement Learning, an agent attempts various movements or actions. Through repeated trials, it learns to infer which movements lead to positive outcomes by reinforcing good behavior and not reinforcing bad behavior. This iterative process allows the agent to gradually improve its performance without explicit programming for each specific movement. To maximize scores or find better paths, an agent needs to explore new possibilities. This can be implemented by introducing a small probability (an epsilon value, e.g., 10%) of making a random move instead of the highest-valued known move. While exploration might occasionally lead to failures, it can also uncover more optimal solutions over time.
*   **ILLUSTRATIVE EXAMPLES:**
    -   Context:
        -   **Robot pancake flipping:** A robot learns to flip a pancake by attempting various movements and inferring which ones lead to positive outcomes through reinforcement, gradually mastering the task.
        -   **Maze-like game:** A player learns to reach an exit while avoiding obstacles by trying random movements, remembering and avoiding paths that lead to negative outcomes (e.g., falling into a lava pit). This process demonstrates how exploration can lead to a solution, even if not immediately the most efficient.
        -   **Breakout game (Reinforcement Learning):** A computer can learn to play optimally. Through reinforcement learning, potentially with human feedback or a scoring system, the AI can discover sophisticated strategies, such as creating a tunnel to allow the ball to clear bricks autonomously, leading to higher scores than a purely deterministic approach.

### 2.5 Supervised, Unsupervised Learning, and Deep Learning
*   **CONCEPT DEFINITION:**
    -   **Supervised Learning:** A type of machine learning where the learning process is guided by human-provided feedback (e.g., labeling actions as 'good' or 'bad').
    -   **Unsupervised Learning:** A type of machine learning where the software is designed to learn independently without constant human labeling of correct or incorrect actions.
    -   **Deep Learning:** A field of Machine Learning that is frequently based on **Neural Networks**.
*   **ELABORATION & MECHANICS:** Reinforcement Learning often involves a human supervising the process or a predefined point system, which falls under Supervised Learning. However, when the volume of data exceeds human capacity for labeling, the transition to Unsupervised Learning becomes necessary. Deep Learning emerges as a significant approach within Unsupervised Learning, leveraging complex network architectures.
*   **ILLUSTRATIVE EXAMPLES:**
    -   Context: No specific examples are provided for Supervised or Unsupervised Learning beyond their definitional context. Deep Learning is directly linked to Neural Networks.

### 2.6 Neural Networks: Architecture and Functionality
*   **CONCEPT DEFINITION:** **Neural Networks** are computational models inspired by biological neural systems, abstracting neurons as interconnected nodes (circles) and their communications as edges in a mathematical graph.
*   **ELABORATION & MECHANICS:** Neural Networks take inputs (e.g., X and Y coordinates) and produce an output (e.g., predicting a category). This prediction is often based on a mathematical expression (e.g., AX + BY + C) where coefficients (A, B, C) are learned from training data. For instance, if the expression's result is greater than zero, it might predict one category; otherwise, another. The core function of Neural Networks is to learn these parameters from vast amounts of data to produce correct answers with high probability. A notable characteristic is their 'black box' nature; the specific meaning or value of individual nodes and edges within the network is often not explicitly understood, as the computer determines these interconnections mathematically. This probabilistic approach to finding solutions is fundamental to Machine Learning.
*   **ILLUSTRATIVE EXAMPLES:**
    -   Context:
        -   **Dot classification:** Predicting if a dot is blue or red based on its X and Y coordinates.
        -   **Meteorology:** A Neural Network can predict rainfall based on humidity and pressure levels, trained on historical data.
        -   **Advertising:** A Neural Network can predict sales based on monthly spending and the specific month, given sufficient historical data.

### 2.7 Large Language Models (LLMs): Architecture and Operation
*   **CONCEPT DEFINITION:** **Large Language Models (LLMs)**, such as ChatGPT, are built upon Neural Networks that process vast amounts of internet content to probabilistically generate responses. **GPT** stands for **Generative Pre-trained Transformer**, indicating that these AIs are designed to generate content, have been pre-trained on extensive public data, and transform user input into output. **Attention** is a feature that dynamically identifies relationships between words in a text, assigning greater weight to more relevant connections. **Hallucinations** refer to a phenomenon observed in Large Language Models where the AI generates confidently stated information that is factually incorrect or fabricated.
*   **ELABORATION & MECHANICS:** LLMs analyze patterns and frequencies in extensive text data (including search results, forums, dictionaries, and encyclopedias) to probabilistically generate responses. This probabilistic nature explains why LLMs can sometimes provide incorrect answers, potentially due to misinformation in their training data or a degree of random exploration. The 'attention' mechanism, proposed by Google in 2017, significantly advanced LLMs by allowing them to dynamically weigh the relevance of words in a text. Words within these models are represented mathematically as high-dimensional vectors (e.g., 1536 floating-point values). These word vectors, along with their attention-weighted relationships, are fed into large Neural Networks. The software navigates this network to find the most probable and correct answer, though perfect accuracy is not guaranteed. OpenAI released its GPT model in 2020, followed by ChatGPT in 2022.
*   **ILLUSTRATIVE EXAMPLES:**
    -   Context:
        -   **ChatGPT:** Mentioned as a prominent example of an LLM.
        -   **Response generation:** If asked 'How are you?', an LLM might respond 'Good, thanks, how are you?' because this is the most probable reply based on its training data.

## 3. TECHNICAL GLOSSARY
-   **Artificial Intelligence (AI):** The simulation of human intelligence in machines programmed to think and learn like humans.
-   **Generative Artificial Intelligence:** A type of AI that uses AI to create content.
-   **Decision Trees:** A programming concept where a root node branches into different children based on yes/no decisions, translating human heuristics into code.
-   **Minimax algorithm:** An algorithm employed in game theory where one player aims to maximize their score and the other aims to minimize theirs.
-   **Machine Learning:** A field where the goal is to write code that teaches computers how to solve problems by learning from available training data, even if the correct answer is not explicitly known to the programmer.
-   **Reinforcement Learning:** A method of training computers where an agent learns through feedback, such as rewards for positive behavior and punishments for negative behavior.
-   **Exploration versus exploitation:** The principle where an agent balances exploiting its current knowledge to reach a known solution with exploring new possibilities to maximize its score or find a better path.
-   **Supervised Learning:** A type of learning where humans provide feedback (e.g., 'good' or 'bad') to supervise the process.
-   **Unsupervised Learning:** A type of learning where the software is designed to learn independently without constant human labeling of correct or incorrect actions.
-   **Deep Learning:** A field of Machine Learning that is frequently based on Neural Networks.
-   **Neural Networks:** Computational models inspired by biological neural systems, abstracting neurons as interconnected nodes and their communications as edges in a mathematical graph.
-   **Large Language Models (LLMs):** Models built upon Neural Networks that process vast amounts of internet content to probabilistically generate responses.
-   **Attention:** A feature that dynamically identifies relationships between words in a text, assigning greater weight to more relevant connections.
-   **GPT (Generative Pre-trained Transformer):** An acronym indicating that AIs are designed to generate content, have been pre-trained on extensive public data, and transform user input into output.
-   **Hallucinations:** A phenomenon observed in Large Language Models where the AI generates confidently stated information that is factually incorrect or fabricated.

## 4. KEY TAKEAWAYS
-   Artificial Intelligence (AI) simulates human intelligence in machines, evolving from early deterministic, rule-based systems to sophisticated learning paradigms.
-   Early AI, exemplified by decision trees and the Minimax algorithm, faced limitations in computationally complex domains, necessitating a shift towards learning-based approaches.
-   Machine Learning, particularly Reinforcement Learning, enables AI to learn from data and feedback, utilizing a balance of exploration and exploitation to discover optimal solutions.
-   Deep Learning, built upon Neural Networks, processes vast datasets to learn parameters probabilistically, forming the foundation for advanced AI applications.
-   Large Language Models (LLMs) like ChatGPT leverage Neural Networks and 'attention' mechanisms to generate human-like text, but their probabilistic nature and training data can lead to inaccuracies and 'hallucinations'."""

create_pdf(summary_text, title, "lecture_notes.pdf")'''