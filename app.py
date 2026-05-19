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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root {
      color-scheme: dark;
      font-family: 'Inter', sans-serif;
    }
    html, body, [data-testid='stAppViewContainer'] {
      background: radial-gradient(circle at 10% 5%, rgba(6,182,212,0.14), transparent 12%),
                  radial-gradient(circle at 90% 10%, rgba(124,58,237,0.18), transparent 16%),
                  linear-gradient(180deg, #020617 0%, #070d1a 100%) !important;
      color: #F8FAFC;
      min-height: 100vh;
      overflow-x: hidden;
    }
    .stApp, .main, .block-container {
      background: transparent !important;
    }
    .glass-shell {
      border-radius: 36px;
      background: rgba(10, 14, 28, 0.72);
      border: 1px solid rgba(255,255,255,0.08);
      box-shadow: 0 48px 120px rgba(0, 0, 0, 0.35);
      backdrop-filter: blur(24px);
      padding: 1.5rem;
    }
    .dashboard-layout { display: grid; grid-template-columns: minmax(260px, 320px) 1fr; gap: 1.75rem; }
    .sidebar-panel {
      position: relative;
      height: calc(100vh - 3rem);
      padding: 1.8rem 1.4rem;
      background: rgba(15, 23, 42, 0.75);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 32px;
      box-shadow: 0 30px 80px rgba(0,0,0,0.28);
      backdrop-filter: blur(22px);
    }
    .sidebar-top { display: grid; gap: 1rem; margin-bottom: 1.6rem; }
    .brand-logo {
      width: 48px;
      height: 48px;
      border-radius: 16px;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, rgba(139,92,246,0.95), rgba(6,182,212,0.95));
      color: #fff;
      font-weight: 800;
      font-size: 1.1rem;
      box-shadow: 0 18px 40px rgba(124,58,237,0.32);
    }
    .sidebar-profile { display: grid; gap: 0.4rem; }
    .profile-name { font-size: 0.95rem; font-weight: 700; }
    .profile-status { color: #94A3B8; font-size: 0.87rem; }
    .signout-btn {
      width: 100%;
      padding: 0.85rem 1rem;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.04);
      color: #F8FAFC;
      font-weight: 600;
      transition: transform .2s ease, background .2s ease;
    }
    .signout-btn:hover { transform: translateY(-1px); background: rgba(255,255,255,0.08); }
    .nav-group { margin-top: 2rem; display: grid; gap: 0.55rem; }
    .nav-item {
      display: flex;
      align-items: center;
      gap: 0.85rem;
      padding: 0.95rem 1rem;
      border-radius: 18px;
      color: #CBD5E1;
      background: rgba(255,255,255,0.02);
      border: 1px solid transparent;
      cursor: pointer;
      transition: all .2s ease;
      font-weight: 600;
    }
    .nav-item:hover { background: rgba(255,255,255,0.08); transform: translateX(2px); }
    .nav-item.active {
      background: rgba(124,58,237,0.18);
      border-color: rgba(124,58,237,0.45);
      color: #fff;
      box-shadow: 0 0 18px rgba(124,58,237,0.18);
    }
    .nav-icon { width: 2rem; height: 2rem; display: grid; place-items: center; border-radius: 14px; background: rgba(255,255,255,0.06); }
    .feature-list { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.08); }
    .feature-chip { display: inline-flex; align-items: center; gap: 0.5rem; background: rgba(255,255,255,0.06); color: #F8FAFC; padding: 0.7rem 0.85rem; border-radius: 14px; font-size: 0.88rem; margin-bottom: 0.65rem; }
    .main-panel { padding: 1.5rem; background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); border-radius: 32px; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 24px 80px rgba(0,0,0,0.2); min-height: calc(100vh - 3rem); }
    .hero-box { display: grid; gap: 1rem; padding: 2rem; border-radius: 28px; border: 1px solid rgba(255,255,255,0.09); background: rgba(10,14,28,0.85); box-shadow: inset 0 0 28px rgba(255,255,255,0.03); margin-bottom: 1.75rem; }
    .hero-top { display: flex; align-items: center; gap: 0.95rem; }
    .hero-logo { width: 54px; height: 54px; border-radius: 18px; display: grid; place-items: center; background: linear-gradient(135deg, #8B5CF6, #06B6D4); color: #fff; font-weight: 800; box-shadow: 0 18px 40px rgba(139,92,246,0.22); }
    .hero-title { font-size: clamp(2.1rem, 3vw, 3rem); line-height: 1.05; margin: 0; font-weight: 800; }
    .hero-subtitle { color: #CBD5E1; line-height: 1.75; font-size: 1rem; max-width: 820px; }
    .status-banner { display: inline-flex; align-items: center; gap: 0.6rem; margin-top: 0.85rem; padding: 0.8rem 1rem; border-radius: 16px; background: rgba(34,197,94,0.12); color: #D9F99D; border: 1px solid rgba(34,197,94,0.2); font-weight: 600; }
    .cards-row { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 1.25rem; margin-top: 1.75rem; }
    .upload-card, .note-card, .panel-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 28px; padding: 1.8rem; box-shadow: 0 24px 60px rgba(0,0,0,0.18); transition: transform .2s ease, border-color .2s ease;
      backdrop-filter: blur(16px);
    }
    .upload-card:hover, .note-card:hover, .panel-card:hover { transform: translateY(-2px); border-color: rgba(124,58,237,0.35); }
    .card-title { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.4rem; font-size: 1.05rem; font-weight: 700; }
    .card-title .card-icon { width: 2.4rem; height: 2.4rem; display: grid; place-items: center; background: rgba(124,58,237,0.14); border-radius: 16px; }
    .upload-area { display: grid; gap: 1rem; border: 2px dashed rgba(255,255,255,0.14); border-radius: 28px; padding: 2.2rem; text-align: center; color: #94A3B8; background: rgba(255,255,255,0.03); }
    .upload-area:hover { border-color: rgba(6,182,212,0.45); }
    .upload-area .upload-icon { width: 64px; height: 64px; margin: 0 auto; border-radius: 24px; display: grid; place-items: center; background: rgba(6,182,212,0.18); color: #A5F3FC; font-size: 1.9rem; }
    .upload-footer { display: flex; justify-content: space-between; gap: 1rem; align-items: center; color: #94A3B8; font-size: 0.95rem; margin-top: 1rem; }
    .file-highlight { color: #fff; }
    .floating-particles { position: absolute; inset: 0; pointer-events: none; z-index: 0; }
    .floating-particles span { position: absolute; border-radius: 999px; background: rgba(124,58,237,0.18); box-shadow: 0 0 40px rgba(124,58,237,0.3); }
    .particle-1 { width: 18px; height: 18px; top: 12%; left: 18%; }
    .particle-2 { width: 12px; height: 12px; top: 34%; left: 75%; background: rgba(6,182,212,0.2); box-shadow: 0 0 28px rgba(6,182,212,0.26); }
    .particle-3 { width: 24px; height: 24px; top: 72%; left: 45%; }
    .panel-card h3 { margin-top: 0; margin-bottom: 0.65rem; color: #fff; }
    .panel-card .panel-line { color: #94A3B8; margin-bottom: 1rem; font-size: 0.95rem; }
    .panel-row { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 1rem; margin-top: 1rem; }
    @media (max-width: 1080px) {
      .dashboard-layout { grid-template-columns: 1fr; }
      .main-panel { min-height: auto; }
      .cards-row { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
      .sidebar-panel { height: auto; padding: 1.25rem; }
      .hero-title { font-size: 2rem; }
      .cards-row { gap: 1rem; }
    }
  </style>
  """,
  unsafe_allow_html=True,
)


def get_db() -> NotesDatabase:
  """Not cached: Streamlit resource cache can keep a stale class after deploy (missing new methods)."""
  return NotesDatabase()


@st.cache_resource
def get_summarizer() -> SummarizerService:
  return SummarizerService()


def render_header(*, signed_in: bool = True) -> None:
  st.markdown('<p class="main-header">📚 AI Notes Summarizer</p>', unsafe_allow_html=True)
  if signed_in:
    st.markdown(
      '<p class="sub-header">Upload PDF or paste notes → get short summaries, key points, '
      "chapter-wise breakdowns, and practice questions. Built for students & exam prep.</p>",
      unsafe_allow_html=True,
    )
  else:
    st.markdown(
      '<p class="sub-header">Sign in or create an account to save and manage your summaries.</p>',
      unsafe_allow_html=True,
    )


def _user_id() -> int:
  return int(st.session_state["auth_user_id"])


def _sign_out() -> None:
  for key in (
    "auth_user_id",
    "auth_username",
    "nav_page",
    "selected_note_id",
    "summary_complete_note_id",
    "create_form_key",
  ):
    st.session_state.pop(key, None)


def page_sign_in(db: NotesDatabase) -> None:
  st.subheader("Sign in")
  with st.form("sign_in_form"):
    username = st.text_input("Username", autocomplete="username")
    password = st.text_input("Password", type="password", autocomplete="current-password")
    submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
  if submitted:
    user = db.authenticate(username, password)
    if user:
      st.session_state["auth_user_id"] = user["id"]
      st.session_state["auth_username"] = user["username"]
      st.session_state["nav_page"] = "Create"
      st.rerun()
    else:
      st.error("Invalid username or password.")


def page_sign_up(db: NotesDatabase) -> None:
  st.subheader("Create account")
  with st.form("sign_up_form"):
    username = st.text_input("Choose a username", key="su_user", autocomplete="username")
    password = st.text_input("Password", type="password", key="su_pw", autocomplete="new-password")
    password2 = st.text_input("Confirm password", type="password", key="su_pw2", autocomplete="new-password")
    submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
  if submitted:
    u = username.strip()
    if len(u) < 2:
      st.error("Username must be at least 2 characters.")
      return
    if len(password) < 6:
      st.error("Password must be at least 6 characters.")
      return
    if password != password2:
      st.error("Passwords do not match.")
      return
    new_id = db.register_user(u, password)
    if new_id is None:
      st.error("That username is already taken.")
      return
    st.session_state["auth_user_id"] = new_id
    st.session_state["auth_username"] = u
    st.session_state["nav_page"] = "Create"
    st.rerun()


def page_auth() -> None:
  db = get_db()
  st.markdown('<div class="auth-layout">', unsafe_allow_html=True)
  col1, col2 = st.columns([1.1, 0.95], gap='large')
  with col1:
    st.markdown(
      """
      <div class="auth-left glass-card">
        <div class="hero-badge">AI Notes Summarizer</div>
        <h1 class="hero-title">Transform your notes into smart summaries instantly.</h1>
        <p class="hero-copy">Build faster review sessions with AI-generated summaries, flashcards, quizzes, and study insights—all in one premium workspace.</p>
        <div class="feature-grid">
          <div class="feature-pill">AI Summaries</div>
          <div class="feature-pill">PDF Upload</div>
          <div class="feature-pill">Flashcards</div>
          <div class="feature-pill">Quiz Generator</div>
        </div>
        <div class="ai-illustration"></div>
        <div class="dashboard-preview">
          <div class="mini-card">
            <div class="mini-card-title">Weekly Notes Saved</div>
            <div class="mini-card-value">18</div>
            <div class="mini-card-note">Smart summaries processed automatically.</div>
          </div>
          <div class="mini-card">
            <div class="mini-card-title">Completion Rate</div>
            <div class="mini-card-value">93%</div>
            <div class="mini-card-note">Study sessions powered by AI insights.</div>
          </div>
        </div>
      </div>
      """,
      unsafe_allow_html=True,
    )
  with col2:
    st.markdown('<div class="glass-card auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="form-heading">Welcome back</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-subtitle">Sign in to unlock instant note summaries and study boosters.</div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Sign in", "Sign up"])
    with tab1:
      page_sign_in(db)
    with tab2:
      page_sign_up(db)
    st.markdown('<div style="margin: 1rem 0; text-align: center; color: #94A3B8;">or continue with</div>', unsafe_allow_html=True)
    st.markdown(
      """
      <a class="social-btn" href="#"><span>Google</span></a>
      <a class="social-btn" href="#"><span>GitHub</span></a>
      """,
      unsafe_allow_html=True,
    )
    st.markdown('<div style="margin-top: 0.75rem; color: #94A3B8; font-size: 0.92rem;">Forgot your password? <a href="#">Reset it here</a></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
  st.markdown('</div>', unsafe_allow_html=True)


DASHBOARD_MENU = [
  ("Create Summary", "📝"),
  ("My Summaries", "📚"),
  ("AI Flashcards", "💡"),
  ("Quiz Generator", "🧠"),
  ("Analytics", "📊"),
  ("Settings", "⚙️"),
  ("Trash", "🗑️"),
]


def _reset_create_form() -> None:
  st.session_state.pop("summary_complete_note_id", None)
  st.session_state["create_form_key"] = st.session_state.get("create_form_key", 0) + 1
  st.session_state["dashboard_page"] = "Create Summary"


def _render_summary_success(db: NotesDatabase, note_id: int, user_id: int) -> None:
  note = db.read_one(note_id, user_id)
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

  if st.session_state.get("ai_fallback_warning"):
    st.warning(st.session_state.pop("ai_fallback_warning"))

  if not summarizer.uses_ai:
    st.info(
      "No OpenAI API key detected. Using built-in fallback summarizer. "
      "Add `OPENAI_API_KEY` to a `.env` file for full AI summaries."
    )
  else:
    st.success(f"AI mode active ({summarizer.model}).")

  complete_id = st.session_state.get("summary_complete_note_id")
  if complete_id:
    _render_summary_success(db, int(complete_id), _user_id())
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

  if source_type == "text" and not title.strip() and raw_text:
    auto_title = raw_text.splitlines()[0].strip()
    title = auto_title[:70] if auto_title else "Text note"

  action = st.radio(
    "Choose action",
    ["Generate AI summary", "Save plain note only"],
    horizontal=True,
    key=f"action_{form_key}",
  )
  is_plain_save = action == "Save plain note only"
  button_label = "Save note" if is_plain_save else "🚀 Generate & Save Summary"

  if st.button(button_label, type="primary", use_container_width=True):
    if not raw_text.strip():
      st.warning("Upload a PDF or paste notes first.")
      return
    if not title.strip():
      st.warning("Please enter a title.")
      return

    if is_plain_save:
      note_id = db.create(
        title=title.strip(),
        source_type=source_type,
        raw_content=raw_text,
        user_id=_user_id(),
      )
      st.success("Plain note saved.")
    else:
      with st.spinner("Generating summaries..."):
        results = summarizer.generate_all(raw_text)
        if summarizer.last_ai_error:
          st.session_state["ai_fallback_warning"] = (
            "OpenAI authentication failed. Using built-in fallback summarizer. "
            "Update `OPENAI_API_KEY` in `.env` to enable AI summaries."
          )
        else:
          st.session_state.pop("ai_fallback_warning", None)
        note_id = db.create(
          title=title.strip(),
          source_type=source_type,
          raw_content=raw_text,
          user_id=_user_id(),
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
  summarizer = get_summarizer()
  uid = _user_id()
  notes = db.read_all(uid)

  query = st.text_input("Search notes", placeholder="Search titles or content...")
  source_filter = st.selectbox("Source", ["All", "Text", "PDF"], index=0)

  if query.strip() or source_filter != "All":
    query_lower = query.strip().lower()
    notes = [
      n for n in notes
      if (
        (not query_lower)
        or query_lower in n["title"].lower()
        or query_lower in (n.get("raw_content") or "").lower()
      )
      and (
        source_filter == "All"
        or (source_filter == "Text" and n["source_type"] == "text")
        or (source_filter == "PDF" and n["source_type"] == "pdf")
      )
    ]

  if not notes:
    st.info("No summaries match your search or filters. Create one from **Create** in the sidebar.")
    return

  note_id = _note_selector(notes)
  if note_id is None:
    return

  st.session_state["selected_note_id"] = note_id
  note = db.read_one(note_id, uid)
  if not note:
    st.error("Note not found.")
    return

  st.caption(f"Source: {note['source_type']} · Updated {note['updated_at'][:10]}")

  ctop, cbot = st.columns([1, 1])
  with ctop:
    st.download_button(
      "📥 Download raw note",
      note.get("raw_content") or "",
      file_name=f"note_{note_id}.txt",
      mime="text/plain",
    )
  with cbot:
    if st.button("🔄 Regenerate summary", use_container_width=True):
      if note.get("raw_content"):
        with st.spinner("Regenerating summary..."):
          results = summarizer.generate_all(note["raw_content"])
          if summarizer.last_ai_error:
            st.warning(
              "AI authentication failed. Saved previous content instead. Update `OPENAI_API_KEY` in `.env` to enable summaries."
            )
          else:
            db.update(
              note_id,
              uid,
              short_summary=results["short_summary"],
              key_points=results["key_points"],
              chapter_summary=results["chapter_summary"],
              practice_questions=results["practice_questions"],
            )
            st.success("Summary regenerated successfully.")
            st.rerun()
      else:
        st.warning("No raw content available to regenerate.")

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
  uid = _user_id()
  notes = db.read_all(uid)

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
  note = db.read_one(note_id, uid)
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
      uid,
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
  uid = _user_id()
  notes = db.read_all(uid)

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
  note = db.read_one(note_id, uid)
  if not note:
    st.error("Note not found.")
    return

  st.warning(f"Delete **{note['title']}**? This cannot be undone.")
  if st.button("Confirm delete", type="primary"):
    if db.delete(note_id, uid):
      st.success("Deleted.")
      if st.session_state.get("selected_note_id") == note_id:
        del st.session_state["selected_note_id"]
      st.rerun()
    else:
      st.error("Delete failed.")


def _dashboard_sidebar() -> str:
  if "dashboard_page" not in st.session_state:
    st.session_state["dashboard_page"] = "Create Summary"

  current = st.session_state["dashboard_page"]
  menu_labels = [f"{icon} {label}" for label, icon in DASHBOARD_MENU]
  index = [label for label, _ in DASHBOARD_MENU].index(current)

  st.markdown(
    """
    <div class='sidebar-top'>
      <div style='display:flex;align-items:center;gap:0.9rem;'>
        <div class='brand-logo'>AI</div>
        <div>
          <div style='font-size:0.95rem;font-weight:700;color:#fff;'>AI Notes Summarizer</div>
          <div style='color:#94A3B8;font-size:0.85rem;'>Premium workspace</div>
        </div>
      </div>
      <div class='sidebar-profile'>
        <div class='profile-name'>Signed in as {st.session_state.get('auth_username', 'User')}</div>
        <div class='profile-status'>Productivity AI dashboard</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
  )

  selected = st.radio(
    "",
    menu_labels,
    index=index,
    key="dashboard_menu",
    label_visibility="collapsed",
  )
  selected_page = selected.split(" ", 1)[1]
  st.session_state["dashboard_page"] = selected_page

  st.markdown("<div class='feature-list'><div class='feature-chip'>AI summaries</div><div class='feature-chip'>Flashcards</div><div class='feature-chip'>Quiz generator</div><div class='feature-chip'>Analytics</div></div>", unsafe_allow_html=True)
  if st.button("Sign Out", key="signout_top", use_container_width=True):
    _sign_out()
    st.rerun()

  return selected_page


def page_flashcards() -> None:
  st.markdown("<div class='hero-title'>AI Flashcards</div><p class='hero-subtitle'>Convert your summaries into memory-friendly flashcards and review prompts.</p>", unsafe_allow_html=True)
  col1, col2 = st.columns(2, gap='large')
  with col1:
    st.markdown("<div class='panel-card'><h3>Active decks</h3><div class='panel-line'>Smart flashcard previews using AI.</div><div style='font-size:2rem;font-weight:800;color:#8B5CF6;'>12</div></div>", unsafe_allow_html=True)
  with col2:
    st.markdown("<div class='panel-card'><h3>Cards generated</h3><div class='panel-line'>Flashcards created from your notes.</div><div style='font-size:2rem;font-weight:800;color:#06B6D4;'>184</div></div>", unsafe_allow_html=True)
  st.info("Flashcard generation is available for any saved note or summary.")


def page_quiz_generator() -> None:
  st.markdown("<div class='hero-title'>Quiz Generator</div><p class='hero-subtitle'>Create practice quizzes from your notes and summaries in seconds.</p>", unsafe_allow_html=True)
  st.markdown("<div class='panel-card'><h3>Instant quiz preview</h3><div class='panel-line'>AI suggests exam-style questions based on your content.</div><div class='panel-row'><div class='panel-card' style='padding:1rem;'>Question accuracy<br><strong style='font-size:1.4rem;color:#06B6D4;'>92%</strong></div><div class='panel-card' style='padding:1rem;'>Difficulty mix<br><strong style='font-size:1.4rem;color:#8B5CF6;'>Easy / Medium / Hard</strong></div></div></div>", unsafe_allow_html=True)


def page_analytics() -> None:
  st.markdown("<div class='hero-title'>Analytics</div><p class='hero-subtitle'>Monitor your note usage, AI summaries, and study progress visually.</p>", unsafe_allow_html=True)
  st.markdown("<div class='cards-row'><div class='panel-card'><h3>Weekly summary count</h3><div class='panel-line'>Track your AI-generated note sessions.</div><div style='font-size:1.7rem;font-weight:800;color:#06B6D4;'>24</div></div><div class='panel-card'><h3>Study streak</h3><div class='panel-line'>Consistent productivity unlocks better learning.</div><div style='font-size:1.7rem;font-weight:800;color:#22C55E;'>7 days</div></div></div>", unsafe_allow_html=True)


def page_settings() -> None:
  st.markdown("<div class='hero-title'>Settings</div><p class='hero-subtitle'>Configure your AI preferences, security options, and dashboard choices.</p>", unsafe_allow_html=True)
  st.markdown("<div class='panel-card'><h3>Theme</h3><div class='panel-line'>Dark mode is enabled for premium focus.</div><div style='font-weight:700;color:#fff;'>Futuristic dark theme</div></div>", unsafe_allow_html=True)


def page_trash() -> None:
  st.markdown("<div class='hero-title'>Trash</div><p class='hero-subtitle'>Recover deleted notes or permanently remove old sessions.</p>", unsafe_allow_html=True)
  st.warning("No trashed notes right now. Deleted summaries will appear here.")


def page_dashboard() -> None:
  st.markdown('<div class="floating-particles"><span class="particle-1"></span><span class="particle-2"></span><span class="particle-3"></span></div>', unsafe_allow_html=True)
  with st.container():
    st.markdown('<div class="glass-shell dashboard-layout">', unsafe_allow_html=True)
    sidebar_col, main_col = st.columns([0.9, 2.3], gap='large')
    with sidebar_col:
      st.markdown('<div class="sidebar-panel">', unsafe_allow_html=True)
      selected_page = _dashboard_sidebar()
      st.markdown('</div>', unsafe_allow_html=True)
    with main_col:
      st.markdown('<div class="main-panel">', unsafe_allow_html=True)
      if selected_page == "Create Summary":
        st.markdown('<div class="hero-box"><div class="hero-top"><div class="hero-logo">N</div><div><div class="hero-title">Welcome back, ready to summarize?</div><div class="hero-subtitle">Upload PDFs or notes to generate AI-powered summaries, key points, chapter breakdowns, and practice questions.</div></div></div><div class="status-banner">AI mode active (GPT-4o-mini)</div></div>', unsafe_allow_html=True)
        page_create()
      elif selected_page == "My Summaries":
        page_read()
      elif selected_page == "AI Flashcards":
        page_flashcards()
      elif selected_page == "Quiz Generator":
        page_quiz_generator()
      elif selected_page == "Analytics":
        page_analytics()
      elif selected_page == "Settings":
        page_settings()
      elif selected_page == "Trash":
        page_trash()
      st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def page_expense_tracker() -> None:
  st.subheader("💰 Expense Tracker")
  db = get_db()
  uid = _user_id()
  expenses = db.read_expenses(uid)

  with st.expander("Add a new expense", expanded=True):
    with st.form("expense_form"):
      description = st.text_input("Description", placeholder="Lunch, taxi, subscription")
      amount = st.number_input("Amount", min_value=0.0, format="%.2f")
      category = st.selectbox(
        "Category",
        ["Food", "Transport", "Bills", "Health", "Subscription", "Other"],
      )
      expense_date = st.date_input("Date")
      notes = st.text_area("Notes", height=90)
      submitted = st.form_submit_button("Save expense", type="primary")

    if submitted:
      if not description.strip():
        st.warning("Enter a description for the expense.")
      elif amount <= 0:
        st.warning("Amount must be greater than 0.")
      else:
        db.create_expense(
          uid,
          description,
          float(amount),
          category,
          expense_date.isoformat(),
          notes,
        )
        st.success("Expense added.")
        st.rerun()

  if not expenses:
    st.info("No expenses recorded yet.")
    return

  total_spent = sum(exp["amount"] for exp in expenses)
  by_category: dict[str, float] = {}
  for exp in expenses:
    by_category[exp["category"]] = by_category.get(exp["category"], 0.0) + exp["amount"]

  st.metric("Total spent", f"${total_spent:,.2f}")

  c1, c2 = st.columns(2)
  with c1:
    st.subheader("Recent expenses")
    for exp in expenses[:10]:
      st.write(
        f"**{exp['description']}** — ${exp['amount']:.2f} | {exp['category']} | {exp['expense_date']}"
      )
      if exp.get("notes"):
        st.caption(exp["notes"])
  with c2:
    st.subheader("Spending by category")
    st.bar_chart(by_category)

  with st.expander("All expenses"):
    for exp in expenses:
      cols = st.columns([3, 1, 1, 2])
      cols[0].write(exp["description"])
      cols[1].write(f"${exp['amount']:.2f}")
      cols[2].write(exp["category"])
      cols[3].write(exp["expense_date"])
      if cols[0].button("Delete", key=f"delete_{exp['id']}"):
        db.delete_expense(exp["id"], uid)
        st.success("Expense deleted.")
        st.rerun()


def main() -> None:
  if not st.session_state.get("auth_user_id"):
    page_auth()
    return

  render_header()

  pages = ["Create", "My Summaries", "Expense Tracker", "Edit", "Delete"]
  default_page = st.session_state.get("nav_page", "Create")
  if default_page not in pages:
    default_page = "Create"

  with st.sidebar:
    user = st.session_state.get("auth_username", "User")
    st.caption(f"Signed in as **{user}**")
    if st.button("Sign out", use_container_width=True):
      _sign_out()
      st.rerun()
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
    st.markdown("- Text notes + plain note save")
    st.markdown("- Search and filter summaries")
    st.markdown("- Key points")
    st.markdown("- Chapter summary")
    st.markdown("- Practice questions")
    st.markdown("- Expense tracker")
    st.markdown("- Monthly spending overview")

  st.session_state["nav_page"] = page

  if page == "Create":
    page_create()
  elif page == "My Summaries":
    page_read()
  elif page == "Edit":
    page_update()
  elif page == "Delete":
    page_delete()
  elif page == "Expense Tracker":
    page_expense_tracker()


if __name__ == "__main__":
  main()
