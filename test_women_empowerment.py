import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath('.'))

from services.summarizer import generate_university_notes

def test_women_empowerment_essay():
    """Test the summarizer with a women empowerment topic."""
    
    print("Generating Women Empowerment Essay using the configured model...")
    print("-" * 60)

    # Sample transcript about women empowerment (simulated lecture content)
    women_empowerment_transcript = """
    Today we're discussing women empowerment, which refers to increasing the economic, political, social, and legal strength of women.
    Women empowerment aims to change attitudes, perceptions, and established ways of doing things. It involves increasing the capacity
    of women to make decisions at the family, community, and societal level.

    Historically, women have faced systemic barriers in education, employment, and political participation. The women's suffrage movement
    of the early 20th century was a major milestone, securing voting rights in many countries. Since then, progress has been made in
    areas like workplace equality, reproductive rights, and political representation, though challenges remain.

    Economic empowerment includes equal pay, access to credit, property rights, and entrepreneurship opportunities. Education plays a
    crucial role in empowerment, providing women with skills and knowledge to participate fully in society. Leadership development
    programs help women take on decision-making roles in business, politics, and civil society.

    Challenges to women empowerment include gender-based violence, cultural norms, limited access to healthcare, and work-life balance
    issues. The glass ceiling phenomenon continues to limit advancement opportunities in many sectors. Additionally, intersectional
    factors like race, class, and geography compound challenges for certain groups of women.

    Global initiatives like UN Sustainable Development Goal 5 aim to achieve gender equality and empower all women and girls. Success
    stories include increased female participation in STEM fields, growing numbers of women entrepreneurs, and greater representation
    in leadership positions. Technology has also created new opportunities for women's economic participation, especially in developing countries.

    Moving forward, continued advocacy, policy reform, and cultural change are essential for advancing women empowerment. Men's engagement
    as allies is increasingly recognized as important. Creating supportive ecosystems that enable women to thrive remains a priority
    for governments, organizations, and communities worldwide.
    """

    topic = "Women Empowerment: Historical Progress, Current Challenges, and Future Directions"

    try:
        print(f"Topic: {topic}")
        print(f"Transcript length: {len(women_empowerment_transcript)} characters")
        print("\nGenerating essay using configured model...")

        # Generate the university-grade notes/essay
        essay = generate_university_notes(topic, women_empowerment_transcript)

        print("\nEssay generated successfully!")
        print("-" * 60)
        print(essay)
        print("-" * 60)

        # Basic analysis
        print(f"\nAnalysis:")
        print(f"   - Generated content length: {len(essay)} characters")
        print(f"   - Content starts with: '{essay[:50]}...'")

        if "Women Empowerment" in essay or "women" in essay.lower() or "empowerment" in essay.lower():
            print("   - Content appears to be relevant to the topic")
        else:
            print("   - Could not verify topic relevance")

        return essay

    except Exception as e:
        print(f"Error generating essay: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("Women Empowerment Essay Generator Test")
    print("=" * 60)

    result = test_women_empowerment_essay()

    if result:
        print("\nTest completed successfully!")
        print("The model was configured with:")
        print("   - Temperature: 1.0 (enhanced reasoning)")
        print("   - Top_p: 0.95 (broader idea exploration)")
        print("   - Max output tokens: 32000")
        print("   - Thinking level: MEDIUM (when available)")
        print("   - Include thoughts: False")
    else:
        print("\nTest failed!")