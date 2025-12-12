"""
Audio Summarizer Frontend

This module provides the Streamlit UI for uploading and processing audio files.
It integrates with the backend STT module for audio processing.
"""

import streamlit as st
import sys
import os

# Add the parent directory to the path to import from services module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.stt import process_audio_file
from services.coc import transform_transcript
from services.summarizer import generate_university_notes
from services.pdf_generator import create_pdf

def main():
    """Main application function."""
    # Set page configuration
    st.set_page_config(
        page_title="Audio Summarizer",
        page_icon="🎵",
        layout="centered"
    )
    
    # Application title
    st.title("Audio Summarizer")
    st.markdown("Upload an audio file to process and summarize its content.")
    
    # Topic input + file uploader (upload only allowed after entering topic)
    topic = st.text_input("Topic of the lecture", value="", help="Specify the lecture topic to improve summarization")
    is_valid_topic = len(topic.strip()) >= 3
    if is_valid_topic:
        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=["mp3", "wav", "m4a", "flac", "ogg"],
            help="Supported formats: MP3, WAV, M4A, FLAC, OGG"
        )
    else:
        st.warning("Please enter a lecture topic of at least 3 characters to enable file upload.")
        uploaded_file = None

    # Initialize session state for transcript and cleaned transcript
    if 'transcript' not in st.session_state:
        st.session_state['transcript'] = ""
    if 'clean_transcript' not in st.session_state:
        st.session_state['clean_transcript'] = ""
    if 'uploaded_name' not in st.session_state:
        st.session_state['uploaded_name'] = None
    if 'last_topic' not in st.session_state:
        st.session_state['last_topic'] = None
    if 'summarized_notes' not in st.session_state:
        st.session_state['summarized_notes'] = ""
    
    # Process uploaded file
    if uploaded_file is not None:
        # Reset session state when a new file is uploaded or topic changes
        if st.session_state['uploaded_name'] != uploaded_file.name:
            st.session_state['uploaded_name'] = uploaded_file.name
            st.session_state['transcript'] = ""
            st.session_state['clean_transcript'] = ""
        if st.session_state['last_topic'] != topic:
            st.session_state['last_topic'] = topic
            st.session_state['clean_transcript'] = ""

        # Display file information
        st.success(f"File uploaded: {uploaded_file.name}")
        
        # Display existing transcript if present
        if st.session_state['transcript']:
            st.text_area("Transcript", value=st.session_state['transcript'], height=150)
        
        # Process button
        if st.button("Process Audio"):
            with st.spinner("Processing audio file..."):
                try:
                    # Call the backend processing function and persist in session state
                    st.session_state['transcript'] = process_audio_file(uploaded_file)
                    # Display the transcript
                    st.text_area("Transcript", value=st.session_state['transcript'], height=150)
                except Exception as e:
                    st.error(f"Error processing audio file: {str(e)}")
        
        # Display file details in expander
        with st.expander("File Details"):
            st.write(f"**Filename:** {uploaded_file.name}")
            st.write(f"**File size:** {uploaded_file.size} bytes")
            st.write(f"**File type:** {uploaded_file.type}")

        # Summarize Notes button only available after transcript exists
        if st.session_state['transcript']:
            if st.button("Refine Transcript"):
                with st.spinner("Refining transcript into readable notes"):
                    try:
                        # Call the transcript transformation function and persist in session
                        st.session_state['clean_transcript'] = transform_transcript(topic, st.session_state['transcript'])
                        # Display cleaned transcript
                        st.text_area("Cleaned Transcript", value=st.session_state['clean_transcript'], height=150)

                    except Exception as e:
                        st.error(f"Error processing audio file: {str(e)}")
        # If cleaned transcript already exists, display it as well
        elif st.session_state['clean_transcript']:
            st.text_area("Cleaned Transcript", value=st.session_state['clean_transcript'], height=150)

        if st.session_state['clean_transcript']:
            if st.button("Generate Summarized Notes"):
                with st.spinner("Generating summarized notes..."):
                    try:
                        # Call the note generation function and persist in session
                        st.session_state['summarized_notes'] = generate_university_notes(
                            topic,
                            st.session_state['clean_transcript']
                        )
                    except Exception as e:
                        st.error(f"Error generating summarized notes: {str(e)}")

            if st.session_state['summarized_notes']:
                # Display summarized notes
                st.text_area("Summarized Notes", value=st.session_state['summarized_notes'], height=300)
                
                # Create PDF
                pdf_filename = "lecture_notes.pdf"
                create_pdf(st.session_state['summarized_notes'], topic, pdf_filename)
                
                with open(pdf_filename, "rb") as f:
                    st.download_button(
                        label="Download PDF",
                        data=f,
                        file_name=f"{topic}_notes.pdf",
                        mime="application/pdf"
                    )
if __name__ == "__main__":
    main()