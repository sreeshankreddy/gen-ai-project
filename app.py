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
  render_header(signed_in=False)
  db = get_db()
  tab1, tab2 = st.tabs(["Sign in", "Sign up"])
  with tab1:
    page_sign_in(db)
  with tab2:
    page_sign_up(db)


def _reset_create_form() -> None:
  st.session_state.pop("summary_complete_note_id", None)
  st.session_state["create_form_key"] = st.session_state.get("create_form_key", 0) + 1
  st.session_state["nav_page"] = "Create"


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

  if st.button("🚀 Generate & Save Summary", type="primary", use_container_width=True):
    if not raw_text.strip():
      st.warning("Upload a PDF or paste notes first.")
      return
    if not title.strip():
      st.warning("Please enter a title.")
      return

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
  uid = _user_id()
  notes = db.read_all(uid)

  if not notes:
    st.info("No summaries yet. Create one from **Create** in the sidebar.")
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
