"""
Staff Explorer - Simple File Manager Interface
Browse and manage hierarchy like Windows Explorer
"""
import streamlit as st
import os
import requests
import subprocess
import sys

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
STAFF_KEY = os.getenv("STAFF_KEY")

st.set_page_config(page_title="Staff Explorer", page_icon="📂", layout="wide")

# ========== HELPER FUNCTIONS ==========

def _get(path, params=None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {str(e)}")
        return None

@st.cache_data(ttl=30)
def fetch_notes_page(module_id: int, limit: int, offset: int):
    resp = _get(f"/notes/0/0/0/{module_id}", params={"limit": limit, "offset": offset})
    if not resp:
        return {"notes": [], "total": 0}
    return resp

@st.cache_data(ttl=30)
def check_pdf_exists(url: str):
    try:
        r = requests.head(url, timeout=2, allow_redirects=True)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return None

# ========== STAFF AUTHENTICATION ==========

if STAFF_KEY:
    key = st.text_input("🔐 Enter staff key", type="password")
    if key != STAFF_KEY:
        st.stop()

# ========== INITIALIZE STATE ==========
if 'breadcrumb' not in st.session_state:
    st.session_state['breadcrumb'] = []
if 'show_create_form' not in st.session_state:
    st.session_state['show_create_form'] = False
if 'rename_item' not in st.session_state:
    st.session_state['rename_item'] = None

# ========== TOOLBAR ==========
toolbar_col1, toolbar_col2, toolbar_col3, toolbar_col4 = st.columns([1, 1, 1, 7])

with toolbar_col1:
    if st.session_state['breadcrumb']:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state['breadcrumb'].pop()
            st.session_state['show_create_form'] = False
            st.session_state['rename_item'] = None
            st.rerun()

with toolbar_col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Determine current level
if not st.session_state['breadcrumb']:
    current_level = "department"
    items_resp = _get('/departments')
    items = items_resp.get('departments', []) if items_resp else []
    create_label = "Department"
    breadcrumb_text = "This PC / Departments"
else:
    last = st.session_state['breadcrumb'][-1]
    level_type = last['type']
    level_id = last['id']
    
    if level_type == 'department':
        current_level = "semester"
        items = _get(f"/notes/{level_id}") or []
        create_label = "Semester"
    elif level_type == 'semester':
        current_level = "subject"
        dept_id = st.session_state['breadcrumb'][0]['id']
        items = _get(f"/notes/{dept_id}/{level_id}") or []
        create_label = "Subject"
    elif level_type == 'subject':
        current_level = "module"
        dept_id = st.session_state['breadcrumb'][0]['id']
        sem_id = st.session_state['breadcrumb'][1]['id']
        items = _get(f"/notes/{dept_id}/{sem_id}/{level_id}") or []
        create_label = "Module"
    elif level_type == 'module':
        current_level = "note"
        create_label = None
        if 'module_pagination' not in st.session_state or st.session_state.get('module_pagination_module') != level_id:
            st.session_state['module_pagination'] = {'limit': 10, 'offset': 0, 'items': [], 'total': None}
            st.session_state['module_pagination_module'] = level_id
        pag = st.session_state['module_pagination']
        page = fetch_notes_page(level_id, pag['limit'], pag['offset'])
        page_notes = page.get('notes', [])
        total = page.get('total', 0)
        existing_ids = {i['id'] for i in pag['items']}
        new_notes = [n for n in page_notes if n['id'] not in existing_ids]
        pag['items'].extend(new_notes)
        pag['total'] = total
        items = pag['items']
    else:
        current_level = None
        items = []
        create_label = None
    
    breadcrumb_text = "This PC / " + " / ".join([b['label'] for b in st.session_state['breadcrumb']])

with toolbar_col3:
    if create_label:
        if st.button("➕ New", use_container_width=True):
            st.session_state['show_create_form'] = True
            st.session_state['rename_item'] = None
            st.rerun()

# ========== ADDRESS BAR ==========
st.text_input("📂", value=breadcrumb_text, disabled=True, label_visibility="collapsed")

st.divider()

# ========== CREATE FORM ==========
if st.session_state.get('show_create_form'):
    st.info(f"➕ Creating new {create_label}")
    
    if current_level == "department":
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        with col1:
            name = st.text_input("Name", placeholder="e.g., Computer Science", key="new_name")
        with col2:
            code = st.text_input("Code", placeholder="e.g., CS", key="new_code")
        with col3:
            if st.button("✅ Create", use_container_width=True):
                if name and code:
                    try:
                        r = requests.post(f"{API_BASE}/api/departments", json={"name": name, "code": code}, timeout=5)
                        if r.status_code == 200:
                            st.success("✅ Created!")
                            st.session_state['show_create_form'] = False
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(r.json().get('detail'))
                    except Exception as e:
                        st.error(str(e))
        with col4:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state['show_create_form'] = False
                st.rerun()
    
    elif current_level == "semester":
        dept_id = st.session_state['breadcrumb'][0]['id']
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        with col1:
            name = st.text_input("Name", placeholder="e.g., Fall 2024", key="new_name")
        with col2:
            number = st.number_input("Number", min_value=1, max_value=12, value=1, key="new_num")
        with col3:
            if st.button("✅ Create", use_container_width=True):
                if name:
                    try:
                        r = requests.post(f"{API_BASE}/api/semesters", 
                            json={"department_id": dept_id, "semester_number": number, "name": name}, timeout=5)
                        if r.status_code == 200:
                            st.success("✅ Created!")
                            st.session_state['show_create_form'] = False
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(r.json().get('detail'))
                    except Exception as e:
                        st.error(str(e))
        with col4:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state['show_create_form'] = False
                st.rerun()
    
    elif current_level == "subject":
        sem_id = st.session_state['breadcrumb'][-1]['id']
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        with col1:
            name = st.text_input("Name", placeholder="e.g., Machine Learning", key="new_name")
        with col2:
            code = st.text_input("Code", placeholder="e.g., CS401", key="new_code")
        with col3:
            if st.button("✅ Create", use_container_width=True):
                if name and code:
                    try:
                        r = requests.post(f"{API_BASE}/api/subjects",
                            json={"semester_id": sem_id, "name": name, "code": code}, timeout=5)
                        if r.status_code == 200:
                            st.success("✅ Created!")
                            st.session_state['show_create_form'] = False
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(r.json().get('detail'))
                    except Exception as e:
                        st.error(str(e))
        with col4:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state['show_create_form'] = False
                st.rerun()
    
    elif current_level == "module":
        subj_id = st.session_state['breadcrumb'][-1]['id']
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        with col1:
            name = st.text_input("Name", placeholder="e.g., Neural Networks", key="new_name")
        with col2:
            number = st.number_input("Number", min_value=1, max_value=20, value=1, key="new_num")
        with col3:
            if st.button("✅ Create", use_container_width=True):
                if name:
                    try:
                        r = requests.post(f"{API_BASE}/api/modules",
                            json={"subject_id": subj_id, "module_number": number, "name": name}, timeout=5)
                        if r.status_code == 200:
                            st.success("✅ Created!")
                            st.session_state['show_create_form'] = False
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(r.json().get('detail'))
                    except Exception as e:
                        st.error(str(e))
        with col4:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state['show_create_form'] = False
                st.rerun()
    
    st.divider()

# ========== FILE/FOLDER LIST ==========
if not items:
    st.info("📂 This folder is empty")
else:
    # Header row
    header_cols = st.columns([5, 1, 1, 1, 2])
    with header_cols[0]:
        st.markdown("**Name**")
    with header_cols[4]:
        if current_level == "note":
            st.markdown("**Status**")
    st.divider()
    
    for item in items:
        item_id = item.get('id')
        item_type = item.get('type', 'note')
        item_label = item.get('label', 'Untitled')
        
        # Rename mode
        if st.session_state.get('rename_item') == item_id:
            st.info(f"✏️ Renaming: {item_label}")
            if item_type in ['department', 'subject']:
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                with col1:
                    new_name = st.text_input("Name", key=f"rename_name_{item_id}")
                with col2:
                    new_code = st.text_input("Code", key=f"rename_code_{item_id}")
                with col3:
                    if st.button("✅ Save", key=f"save_{item_id}", use_container_width=True):
                        if new_name:
                            payload = {"name": new_name}
                            if new_code:
                                payload["code"] = new_code
                            endpoint = f"/api/departments/{item_id}" if item_type == 'department' else f"/api/subjects/{item_id}"
                            try:
                                r = requests.put(f"{API_BASE}{endpoint}", json=payload, timeout=5)
                                if r.status_code == 200:
                                    st.success("✅ Renamed!")
                                    st.session_state['rename_item'] = None
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(r.json().get('detail'))
                            except Exception as e:
                                st.error(str(e))
                with col4:
                    if st.button("❌ Cancel", key=f"cancel_{item_id}", use_container_width=True):
                        st.session_state['rename_item'] = None
                        st.rerun()
            
            elif item_type in ['semester', 'module']:
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                with col1:
                    new_name = st.text_input("Name", key=f"rename_name_{item_id}")
                with col2:
                    new_num = st.number_input("Number", min_value=1, value=1, key=f"rename_num_{item_id}")
                with col3:
                    if st.button("✅ Save", key=f"save_{item_id}", use_container_width=True):
                        if new_name:
                            payload = {"name": new_name}
                            if new_num > 0:
                                payload["semester_number" if item_type == 'semester' else "module_number"] = new_num
                            endpoint = f"/api/semesters/{item_id}" if item_type == 'semester' else f"/api/modules/{item_id}"
                            try:
                                r = requests.put(f"{API_BASE}{endpoint}", json=payload, timeout=5)
                                if r.status_code == 200:
                                    st.success("✅ Renamed!")
                                    st.session_state['rename_item'] = None
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(r.json().get('detail'))
                            except Exception as e:
                                st.error(str(e))
                with col4:
                    if st.button("❌ Cancel", key=f"cancel_{item_id}", use_container_width=True):
                        st.session_state['rename_item'] = None
                        st.rerun()
            
            elif item_type == 'note':
                col1, col2, col3 = st.columns([5, 1, 1])
                with col1:
                    new_title = st.text_input("Title", key=f"rename_title_{item_id}")
                with col2:
                    if st.button("✅ Save", key=f"save_{item_id}", use_container_width=True):
                        if new_title:
                            try:
                                r = requests.put(f"{API_BASE}/api/notes/{item_id}", json={"title": new_title}, timeout=5)
                                if r.status_code == 200:
                                    st.success("✅ Renamed!")
                                    st.session_state['rename_item'] = None
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(r.json().get('detail'))
                            except Exception as e:
                                st.error(str(e))
                with col3:
                    if st.button("❌ Cancel", key=f"cancel_{item_id}", use_container_width=True):
                        st.session_state['rename_item'] = None
                        st.rerun()
            st.divider()
            continue
        
        # Delete confirmation mode
        if st.session_state.get(f'confirm_delete_{item_id}'):
            st.warning(f"⚠️ Delete '{item_label}'? This will CASCADE delete all children!")
            col1, col2, col3 = st.columns([6, 1, 1])
            with col2:
                if st.button("✅ Yes", key=f"yes_{item_id}", use_container_width=True):
                    endpoint_map = {
                        'department': f"/api/departments/{item_id}",
                        'semester': f"/api/semesters/{item_id}",
                        'subject': f"/api/subjects/{item_id}",
                        'module': f"/api/modules/{item_id}",
                        'note': f"/api/notes/{item_id}"
                    }
                    try:
                        r = requests.delete(f"{API_BASE}{endpoint_map[item_type]}", timeout=5)
                        if r.status_code == 200:
                            st.success("✅ Deleted!")
                            st.session_state.pop(f'confirm_delete_{item_id}', None)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(r.json().get('detail'))
                    except Exception as e:
                        st.error(str(e))
            with col3:
                if st.button("❌ No", key=f"no_{item_id}", use_container_width=True):
                    st.session_state.pop(f'confirm_delete_{item_id}', None)
                    st.rerun()
            st.divider()
            continue
        
        # Normal item row
        cols = st.columns([5, 1, 1, 1, 2])
        
        with cols[0]:
            icon = {'department':'🏛️','semester':'📅','subject':'📚','module':'📖','note':'📄'}.get(item_type, '📁')
            st.markdown(f"{icon} {item_label}")
        
        with cols[1]:
            if item_type != 'note':
                if st.button("Open", key=f"open_{item_id}", use_container_width=True):
                    st.session_state['breadcrumb'].append({'id': item_id, 'label': item_label, 'type': item_type})
                    st.session_state['show_create_form'] = False
                    st.session_state['rename_item'] = None
                    st.rerun()
        
        with cols[2]:
            if st.button("Rename", key=f"ren_{item_id}", use_container_width=True):
                st.session_state['rename_item'] = item_id
                st.session_state['show_create_form'] = False
                st.rerun()
        
        with cols[3]:
            if st.button("Delete", key=f"del_{item_id}", use_container_width=True):
                st.session_state[f'confirm_delete_{item_id}'] = True
                st.rerun()
        
        with cols[4]:
            if item_type == 'note':
                pdf_url = item.get('pdf_url')
                if pdf_url:
                    if not pdf_url.startswith('http'):
                        full_url = f"{API_BASE.rstrip('/')}/{pdf_url.lstrip('/')}"
                    else:
                        full_url = pdf_url
                    exists = check_pdf_exists(full_url)
                    if exists is True:
                        st.markdown(f"[📥 Open PDF]({full_url})")
                    elif exists is False:
                        st.markdown("❌ Missing")
                    else:
                        st.markdown("⏳ Checking...")
        
        st.divider()
    
    # Load more for notes
    if current_level == "note":
        pag = st.session_state.get('module_pagination', {})
        total = pag.get('total', 0)
        shown = len(pag.get('items', []))
        if shown < total:
            st.caption(f"Showing {shown} of {total} notes")
            if st.button("⬇️ Load More", use_container_width=True):
                pag['offset'] += pag['limit']
                st.rerun()

# ========== SIDEBAR TOOLS ==========
with st.sidebar:
    st.info("ℹ️ System is now auto-cleaning files on deletion.")

