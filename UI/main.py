import streamlit as st
import requests
import os
import time
import sys
from dotenv import load_dotenv

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.stt import process_audio_file
from services.coc import transform_transcript
from services.summarizer import generate_university_notes
from services.pdf_generator import create_pdf, create_pdf_bytes

load_dotenv()

# Configuration
API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
# Use repository-level pdfs folder (the API serves this path)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(PROJECT_ROOT, "pdfs")
# Ensure pdf dir exists
os.makedirs(PDF_DIR, exist_ok=True)

st.set_page_config(page_title="AURA-PROTO - Audio Summarizer", layout="wide")

# Initialize session state
if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None
if 'transcript' not in st.session_state:
    st.session_state['transcript'] = ""
if 'refined_transcript' not in st.session_state:
    st.session_state['refined_transcript'] = ""
if 'summarized_notes' not in st.session_state:
    st.session_state['summarized_notes'] = ""
if 'hierarchy' not in st.session_state:
    st.session_state['hierarchy'] = {
        'department': None,
        'semester': None,
        'subject': None,
        'module': None
    }

# Cache functions for hierarchy fetching
@st.cache_data(ttl=600)
def fetch_departments():
    try:
        response = requests.get(f"{API_URL}/departments", timeout=5)
        return response.json().get('departments', [])
    except Exception as e:
        st.error(f"Error fetching departments: {e}")
        return []

@st.cache_data(ttl=600)
def fetch_semesters(dept_id):
    try:
        response = requests.get(f"{API_URL}/departments/{dept_id}/semesters", timeout=5)
        return response.json().get('semesters', [])
    except Exception as e:
        st.error(f"Error fetching semesters: {e}")
        return []

@st.cache_data(ttl=600)
def fetch_subjects(sem_id):
    try:
        response = requests.get(f"{API_URL}/semesters/{sem_id}/subjects", timeout=5)
        return response.json().get('subjects', [])
    except Exception as e:
        st.error(f"Error fetching subjects: {e}")
        return []

@st.cache_data(ttl=600)
def fetch_modules(subj_id):
    try:
        response = requests.get(f"{API_URL}/subjects/{subj_id}/modules", timeout=5)
        return response.json().get('modules', [])
    except Exception as e:
        st.error(f"Error fetching modules: {e}")
        return []

# Sidebar: hierarchy selection
with st.sidebar:
    st.title("Select Hierarchy (Staff)")
    
    # Department
    departments = fetch_departments()
    dept_options = {d['label']: d for d in departments}
    selected_dept_label = st.selectbox(
        "Department",
        options=list(dept_options.keys()) if dept_options else [],
        key="dept_select"
    )
    if selected_dept_label:
        st.session_state['hierarchy']['department'] = dept_options[selected_dept_label]
        dept_id = dept_options[selected_dept_label]['id']
        
        # Semester
        semesters = fetch_semesters(dept_id)
        sem_options = {s['label']: s for s in semesters}
        selected_sem_label = st.selectbox(
            "Semester",
            options=list(sem_options.keys()) if semesters else [],
            key="sem_select"
        )
        if selected_sem_label:
            st.session_state['hierarchy']['semester'] = sem_options[selected_sem_label]
            sem_id = sem_options[selected_sem_label]['id']
            
            # Subject
            subjects = fetch_subjects(sem_id)
            subj_options = {s['label']: s for s in subjects}
            selected_subj_label = st.selectbox(
                "Subject",
                options=list(subj_options.keys()) if subjects else [],
                key="subj_select"
            )
            if selected_subj_label:
                st.session_state['hierarchy']['subject'] = subj_options[selected_subj_label]
                subj_id = subj_options[selected_subj_label]['id']
                
                # Module
                modules = fetch_modules(subj_id)
                mod_options = {m['label']: m for m in modules}
                selected_mod_label = st.selectbox(
                    "Module",
                    options=list(mod_options.keys()) if modules else [],
                    key="mod_select"
                )
                if selected_mod_label:
                    st.session_state['hierarchy']['module'] = mod_options[selected_mod_label]
    
    st.divider()
    
    # Link to explorer and management
    st.markdown("[Open Notes Explorer (Staff)](http://localhost:8502)")
    st.caption("To run explorer: streamlit run UI/explorer.py")
    
    st.markdown("[Open Hierarchy Management (Admin)](http://localhost:8503)")
    st.caption("To run management: streamlit run UI/manage.py --server.port 8503")
    
    st.divider()
    st.caption("Fetching from API (cached)")

# Main content
st.title("AURA-PROTO - Audio Summarizer")
st.markdown("Upload an audio file to process and summarize its content.")

# Input section
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Input")
    topic = st.text_input("Topic of the lecture", value="Artificial Intelligence")
    uploaded_file = st.file_uploader("Choose an audio file", type=["mp3", "wav", "m4a", "flac", "ogg"])
    
    if uploaded_file:
        st.session_state['uploaded_file'] = uploaded_file
        st.success(f"File uploaded: {uploaded_file.name}")

with col2:
    st.subheader("Processing")
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        if st.button("Transcribe", use_container_width=True):
            if st.session_state['uploaded_file']:
                try:
                    with st.spinner("Transcribing..."):
                        result = process_audio_file(st.session_state['uploaded_file'])
                        st.session_state['transcript'] = result
                        st.success("Transcription complete!")
                except Exception as e:
                    st.error(f"Error processing audio file: {e}")
            else:
                st.warning("Please upload an audio file first.")
    
    with col_b:
        if st.button("Refine", use_container_width=True):
            if st.session_state['transcript']:
                try:
                    with st.spinner("Refining..."):
                        result = transform_transcript(topic, st.session_state['transcript'])
                        st.session_state['refined_transcript'] = result
                        st.success("Refinement complete!")
                except Exception as e:
                    st.error(f"Error refining transcript: {e}")
            else:
                st.warning("Please transcribe first.")
    
    with col_c:
        if st.button("Summarize", use_container_width=True):
            if st.session_state['refined_transcript']:
                try:
                    with st.spinner("Summarizing..."):
                        result = generate_university_notes(topic, st.session_state['refined_transcript'])
                        st.session_state['summarized_notes'] = result
                        st.success("Summarization complete!")
                except Exception as e:
                    st.error(f"Error generating summary: {e}")
            else:
                st.warning("Please refine transcript first.")

# Results section
st.divider()
st.subheader("Results")

col1, col2 = st.columns([1, 1])

with col1:
    if st.session_state['transcript']:
        with st.expander("Transcript"):
            st.text(st.session_state['transcript'][:500] + "..." if len(st.session_state['transcript']) > 500 else st.session_state['transcript'])

with col2:
    if st.session_state['refined_transcript']:
        with st.expander("Refined Transcript"):
            st.text(st.session_state['refined_transcript'][:500] + "..." if len(st.session_state['refined_transcript']) > 500 else st.session_state['refined_transcript'])

if st.session_state['summarized_notes']:
    st.markdown("### Summarized Notes")
    st.markdown(st.session_state['summarized_notes'])
    
    # PDF generation and saving
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            # Build proper path in repository-level pdfs dir
            pdf_basename = f"{topic.replace(' ', '_')}_{int(time.time())}.pdf"
            pdf_filename = os.path.join(PDF_DIR, pdf_basename)

            # Generate bytes for immediate download and also save to disk
            pdf_bytes = create_pdf_bytes(st.session_state['summarized_notes'], topic)
            # Ensure bytes (fpdf may return bytearray)
            if isinstance(pdf_bytes, bytearray):
                pdf_bytes = bytes(pdf_bytes)
            with open(pdf_filename, 'wb') as f:
                f.write(pdf_bytes)

            # Persist last generated PDF in session state to avoid regenerating
            st.session_state['last_pdf_bytes'] = pdf_bytes
            st.session_state['last_pdf_filename'] = pdf_filename
            st.session_state['last_pdf_topic'] = topic

            # Auto-save to DB if module selected (default behavior)
            if st.session_state['hierarchy'].get('module'):
                try:
                    pdf_file_only = os.path.basename(pdf_filename)
                    payload = {
                        "department_id": st.session_state['hierarchy']['department']['id'],
                        "semester_id": st.session_state['hierarchy']['semester']['id'],
                        "subject_id": st.session_state['hierarchy']['subject']['id'],
                        "module_id": st.session_state['hierarchy']['module']['id'],
                        "title": topic,
                        "pdf_url": f"pdfs/{pdf_file_only}"
                    }
                    resp = requests.post(f"{API_URL}/notes", json=payload, timeout=5)
                    if resp.status_code == 201:
                        st.session_state['last_saved_note'] = resp.json()
                        st.success("✅ PDF saved to disk and recorded in the database (Explorer updated).")
                    else:
                        st.warning(f"PDF saved locally but failed to save to DB: {resp.json().get('detail','Unknown')}")
                except Exception as e:
                    st.warning(f"PDF saved locally but failed to save to DB: {e}")
            else:
                st.info("PDF generated and saved locally. Select a module in the sidebar to auto-save the note to the database.")

            st.download_button(
                label="📥 Download PDF",
                data=pdf_bytes,
                file_name=os.path.basename(pdf_filename),
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error generating PDF: {e}")
    
    with col2:
        # Determine if last generated pdf is already saved for current module
        last_saved = st.session_state.get('last_saved_note')
        last_pdf = st.session_state.get('last_pdf_filename')
        already_saved_for_module = False
        if last_saved and last_pdf and st.session_state['hierarchy'].get('module'):
            if last_saved.get('module_id') == st.session_state['hierarchy']['module']['id'] and os.path.basename(last_pdf) == os.path.basename(last_saved.get('pdf_url','')):
                already_saved_for_module = True

        if already_saved_for_module:
            st.success("✅ This PDF was already saved to the database.")
            st.info(f"Saved note: {last_saved.get('title')} (created: {last_saved.get('created_at')})")
        else:
            if st.button("Save to Database", use_container_width=True):
                # Check if module is selected
                if not st.session_state['hierarchy'].get('module'):
                    st.error("No module selected. Please select a module in the sidebar to save the note.")
                else:
                    try:
                        # Use last generated bytes if available to avoid regenerating
                        if st.session_state.get('last_pdf_bytes') and st.session_state.get('last_pdf_topic') == topic:
                            pdf_bytes = st.session_state['last_pdf_bytes']
                            pdf_filename = st.session_state['last_pdf_filename']

                            # If the last saved file is not in the project PDF_DIR, try relocating it
                            try:
                                if pdf_filename and os.path.exists(pdf_filename):
                                    parent = os.path.dirname(os.path.abspath(pdf_filename))
                                    if os.path.normcase(parent) != os.path.normcase(PDF_DIR):
                                        new_path = os.path.join(PDF_DIR, os.path.basename(pdf_filename))
                                        os.replace(pdf_filename, new_path)
                                        pdf_filename = new_path
                                        st.session_state['last_pdf_filename'] = pdf_filename
                            except Exception as e:
                                st.warning(f"Could not move previous PDF into project folder: {e}")
                        else:
                            pdf_basename = f"{topic.replace(' ', '_')}_{int(time.time())}.pdf"
                            pdf_filename = os.path.join(PDF_DIR, pdf_basename)
                            pdf_bytes = create_pdf_bytes(st.session_state['summarized_notes'], topic)
                            # Ensure bytes (fpdf may return bytearray)
                            if isinstance(pdf_bytes, bytearray):
                                pdf_bytes = bytes(pdf_bytes)
                            with open(pdf_filename, 'wb') as f:
                                f.write(pdf_bytes)

                        # Extract just the filename for storage
                        pdf_file_only = os.path.basename(pdf_filename)

                        # Call POST /notes to save metadata
                        payload = {
                            "department_id": st.session_state['hierarchy']['department']['id'],
                            "semester_id": st.session_state['hierarchy']['semester']['id'],
                            "subject_id": st.session_state['hierarchy']['subject']['id'],
                            "module_id": st.session_state['hierarchy']['module']['id'],
                            "title": topic,
                            "pdf_url": f"pdfs/{pdf_file_only}"
                        }

                        response = requests.post(f"{API_URL}/notes", json=payload, timeout=5)

                        if response.status_code == 201:
                            st.session_state['last_saved_note'] = response.json()
                            st.success(f"Note saved to database and ready in Explorer!")
                            st.info(f"PDF: {os.path.abspath(pdf_filename)}")
                        else:
                            st.error(f"Failed to save note: {response.json().get('detail', 'Unknown error')}")
                    except requests.exceptions.ConnectionError:
                        st.error("Cannot connect to API. Make sure the API server is running (cd api && uvicorn main:app --reload)")
                    except Exception as e:
                        st.error(f"Error saving note: {e}")
