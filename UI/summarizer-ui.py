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
    
    # File uploader widget
    uploaded_file = st.file_uploader(
        "Choose an audio file",
        type=["mp3", "wav", "m4a", "flac", "ogg"],
        help="Supported formats: MP3, WAV, M4A, FLAC, OGG"
    )
    
    # Process uploaded file
    if uploaded_file is not None:
        # Display file information
        st.success(f"File uploaded: {uploaded_file.name}")
        
        # Process button
        if st.button("Process Audio", type="primary"):
            with st.spinner("Processing audio file..."):
                try:
                    # Call the backend processing function
                    result = process_audio_file(uploaded_file)
                    
                    # Display result
                    st.text_area("Transcript", result, height=300)
                    
                except Exception as e:
                    st.error(f"Error processing audio file: {str(e)}")
        
        # Display file details in expander
        with st.expander("File Details"):
            st.write(f"**Filename:** {uploaded_file.name}")
            st.write(f"**File size:** {uploaded_file.size} bytes")
            st.write(f"**File type:** {uploaded_file.type}")


if __name__ == "__main__":
    main()