import sys
from pathlib import Path

# Ensure project root is on path when Streamlit runs from any cwd
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
  sys.path.insert(0, str(_ROOT))

import streamlit as st

from database.db import NotesDatabase
from services.ai_summarizer import SummarizerService
from services.pdf_parser import extract_text_from_pdf

st.set_page_config(
  page_title="AI Notes Summarizer",
  page_icon="📚",
  layout="wide",
)

st.markdown(
  """
  <style>
    .main-header { font-size: 2.2rem; font-weight: 700; margin-bottom: 0.2rem; }
    .sub-header { color: #6b7280; margin-bottom: 1.5rem; }
    .feature-card {
      background: linear-gradient(135deg, #667eea15, #764ba215);
      padding: 1rem 1.2rem;
      border-radius: 12px;
      border: 1px solid #e5e7eb;
      margin-bottom: 0.5rem;
    }
  </style>
  """,
  unsafe_allow_html=True,
)


@st.cache_resource
def get_db() -> NotesDatabase:
  return NotesDatabase()


@st.cache_resource
def get_summarizer() -> SummarizerService:
  return SummarizerService()


def render_header() -> None:
  st.markdown('<p class="main-header">📚 AI Notes Summarizer</p>', unsafe_allow_html=True)
  st.markdown(
    '<p class="sub-header">Upload PDF or paste notes → get short summaries, key points, '
    "chapter-wise breakdowns, and practice questions. Built for students & exam prep.</p>",
    unsafe_allow_html=True,
  )


def _reset_create_form() -> None:
  st.session_state.pop("summary_complete_note_id", None)
  st.session_state["create_form_key"] = st.session_state.get("create_form_key", 0) + 1
  st.session_state["nav_page"] = "Create"


def _render_summary_success(db: NotesDatabase, note_id: int) -> None:
  note = db.read_one(note_id)
  if not note:
    st.error("Summary not found.")
    if st.button("🏠 Return to Home", type="primary", use_container_width=True):
      _reset_create_form()
      st.rerun()
    return

  source_label = "PDF" if note["source_type"] == "pdf" else "notes"
  st.success(f"Your {source_label} was summarized and saved as **{note['title']}** (note #{note_id}).")

  with st.expander("Short summary", expanded=True):
    st.write(note.get("short_summary") or "_No summary._")
  with st.expander("Key points"):
    st.write(note.get("key_points") or "_No key points._")
  with st.expander("Chapter summary"):
    st.write(note.get("chapter_summary") or "_No chapter summary._")
  with st.expander("Practice questions"):
    st.write(note.get("practice_questions") or "_No questions._")

  c1, c2 = st.columns(2)
  with c1:
    if st.button("📖 View in My Summaries", use_container_width=True):
      st.session_state["selected_note_id"] = note_id
      st.session_state["nav_page"] = "My Summaries"
      st.rerun()
  with c2:
    if st.button("🏠 Return to Home", type="primary", use_container_width=True):
      _reset_create_form()
      st.rerun()


def page_create() -> None:
  st.subheader("➕ Create New Summary")
  summarizer = get_summarizer()
  db = get_db()

  if not summarizer.uses_ai:
    st.info(
      "No OpenAI API key detected. Using built-in fallback summarizer. "
      "Add `OPENAI_API_KEY` to a `.env` file for full AI summaries."
    )
  else:
    st.success(f"AI mode active ({summarizer.model}).")

  complete_id = st.session_state.get("summary_complete_note_id")
  if complete_id:
    _render_summary_success(db, int(complete_id))
    return

  form_key = st.session_state.get("create_form_key", 0)

  col1, col2 = st.columns([1, 1])
  with col1:
    st.markdown('<div class="feature-card">📄 PDF Upload</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload PDF", type=["pdf"], key=f"pdf_upload_{form_key}")
  with col2:
    st.markdown('<div class="feature-card">📝 Text Notes</div>', unsafe_allow_html=True)
    title = st.text_input("Title", placeholder="e.g. Biology Chapter 3", key=f"title_{form_key}")
    pasted_notes = st.text_area(
      "Paste your notes",
      height=220,
      placeholder="Paste lecture notes, textbook excerpts, or study material here...",
      key=f"notes_{form_key}",
    )

  raw_text = ""
  source_type = "text"

  if uploaded:
    try:
      raw_text = extract_text_from_pdf(uploaded.read())
      source_type = "pdf"
      if not title:
        title = uploaded.name.replace(".pdf", "")
      st.success(f"Extracted {len(raw_text.split())} words from PDF.")
      with st.expander("Preview extracted text"):
        st.text(raw_text[:3000] + ("..." if len(raw_text) > 3000 else ""))
    except Exception as exc:
      st.error(f"PDF error: {exc}")
      return

  if pasted_notes.strip() and not raw_text:
    raw_text = pasted_notes.strip()
    source_type = "text"

  if st.button("🚀 Generate & Save Summary", type="primary", use_container_width=True):
    if not raw_text.strip():
      st.warning("Upload a PDF or paste notes first.")
      return
    if not title.strip():
      st.warning("Please enter a title.")
      return

    with st.spinner("Generating summaries..."):
      results = summarizer.generate_all(raw_text)
      note_id = db.create(
        title=title.strip(),
        source_type=source_type,
        raw_content=raw_text,
        short_summary=results["short_summary"],
        key_points=results["key_points"],
        chapter_summary=results["chapter_summary"],
        practice_questions=results["practice_questions"],
      )
    st.session_state["summary_complete_note_id"] = note_id
    st.session_state["selected_note_id"] = note_id
    st.rerun()


def _note_selector(notes: list) -> int | None:
  if not notes:
    return None
  options = {f"#{n['id']} — {n['title']}": n["id"] for n in notes}
  label = st.selectbox("Select a note", list(options.keys()))
  return options[label]


def page_read() -> None:
  st.subheader("📖 My Summaries (Read)")
  db = get_db()
  notes = db.read_all()

  if not notes:
    st.info("No summaries yet. Create one from **Create** in the sidebar.")
    return

  note_id = _note_selector(notes)
  if note_id is None:
    return

  st.session_state["selected_note_id"] = note_id
  note = db.read_one(note_id)
  if not note:
    st.error("Note not found.")
    return

  st.caption(f"Source: {note['source_type']} · Updated {note['updated_at'][:10]}")

  tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Short summary", "Key points", "Chapters", "Questions", "Raw content"]
  )
  with tab1:
    st.write(note.get("short_summary") or "_No summary yet._")
  with tab2:
    st.write(note.get("key_points") or "_No key points yet._")
  with tab3:
    st.write(note.get("chapter_summary") or "_No chapter summary yet._")
  with tab4:
    st.write(note.get("practice_questions") or "_No questions yet._")
  with tab5:
    st.text_area("Original content", value=note.get("raw_content") or "", height=300, disabled=True)

  c1, c2 = st.columns(2)
  with c1:
    if st.button("✏️ Edit this note"):
      st.session_state["nav_page"] = "Edit"
      st.rerun()
  with c2:
    if st.button("🗑️ Delete this note"):
      st.session_state["nav_page"] = "Delete"
      st.rerun()


def page_update() -> None:
  st.subheader("✏️ Edit Summary (Update)")
  db = get_db()
  notes = db.read_all()

  if not notes:
    st.info("No summaries to edit.")
    return

  default_id = st.session_state.get("selected_note_id")
  options = {f"#{n['id']} — {n['title']}": n["id"] for n in notes}
  keys = list(options.keys())
  default_index = 0
  if default_id:
    for i, k in enumerate(keys):
      if options[k] == default_id:
        default_index = i
        break

  label = st.selectbox("Select note to edit", keys, index=default_index)
  note_id = options[label]
  note = db.read_one(note_id)
  if not note:
    st.error("Note not found.")
    return

  with st.form("edit_form"):
    title = st.text_input("Title", value=note["title"])
    short_summary = st.text_area("Short summary", value=note.get("short_summary") or "", height=100)
    key_points = st.text_area("Key points", value=note.get("key_points") or "", height=120)
    chapter_summary = st.text_area("Chapter summary", value=note.get("chapter_summary") or "", height=120)
    practice_questions = st.text_area("Practice questions", value=note.get("practice_questions") or "", height=120)
    submitted = st.form_submit_button("Save changes", type="primary")

  if submitted:
    ok = db.update(
      note_id,
      title=title,
      short_summary=short_summary,
      key_points=key_points,
      chapter_summary=chapter_summary,
      practice_questions=practice_questions,
    )
    if ok:
      st.success("Updated successfully.")
      st.session_state["selected_note_id"] = note_id
      st.rerun()
    else:
      st.error("Update failed.")


def page_delete() -> None:
  st.subheader("🗑️ Delete Summary")
  db = get_db()
  notes = db.read_all()

  if not notes:
    st.info("No summaries to delete.")
    return

  default_id = st.session_state.get("selected_note_id")
  options = {f"#{n['id']} — {n['title']}": n["id"] for n in notes}
  keys = list(options.keys())
  default_index = 0
  if default_id:
    for i, k in enumerate(keys):
      if options[k] == default_id:
        default_index = i
        break

  label = st.selectbox("Select note to delete", keys, index=default_index)
  note_id = options[label]
  note = db.read_one(note_id)
  if not note:
    st.error("Note not found.")
    return

  st.warning(f"Delete **{note['title']}**? This cannot be undone.")
  if st.button("Confirm delete", type="primary"):
    if db.delete(note_id):
      st.success("Deleted.")
      if st.session_state.get("selected_note_id") == note_id:
        del st.session_state["selected_note_id"]
      st.rerun()
    else:
      st.error("Delete failed.")


def main() -> None:
  render_header()

  pages = ["Create", "My Summaries", "Edit", "Delete"]
  default_page = st.session_state.get("nav_page", "Create")
  if default_page not in pages:
    default_page = "Create"

  with st.sidebar:
    st.header("Navigation")
    page = st.radio(
      "CRUD operations",
      pages,
      index=pages.index(default_page),
      label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**Features**")
    st.markdown("- PDF upload")
    st.markdown("- Key points")
    st.markdown("- Chapter summary")
    st.markdown("- Practice questions")

  st.session_state["nav_page"] = page

  if page == "Create":
    page_create()
  elif page == "My Summaries":
    page_read()
  elif page == "Edit":
    page_update()
  elif page == "Delete":
    page_delete()


if __name__ == "__main__":
  main()
