import os
import re
from collections import Counter

from dotenv import load_dotenv

load_dotenv()


class SummarizerService:
  def __init__(self) -> None:
    self.api_key = (
      os.getenv("GOOGLE_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
    )
    self.model = os.getenv("GENAI_MODEL", "chat-bison-001")
    self.last_ai_error: str | None = None

  @property
  def uses_ai(self) -> bool:
    return bool(self.api_key)

  def generate_all(self, text: str) -> dict[str, str]:
    if self.uses_ai:
      try:
        self.last_ai_error = None
        return self._generate_with_sdk(text)
      except Exception as exc:
        self.last_ai_error = self._extract_openai_error(exc)
        if self.last_ai_error:
          return self._generate_fallback(text)
        raise
    return self._generate_fallback(text)

  def _extract_openai_error(self, exc: Exception) -> str | None:
    if isinstance(exc, ImportError):
      return str(exc)

    msg = str(exc).strip()
    if not msg:
      return None

    if (
      "Incorrect API key" in msg
      or "invalid_api_key" in msg
      or "401" in msg
      or "AuthenticationError" in type(exc).__name__
    ):
      return msg

    try:
      from openai.error import AuthenticationError
      if isinstance(exc, AuthenticationError):
        return msg
    except ImportError:
      pass

    return None

  def _generate_with_sdk(self, text: str) -> dict[str, str]:
    from google.genai import Client

    client = Client(api_key=self.api_key)
    clipped = text[:12000]

    prompt = f"""You are an expert study assistant for students preparing for exams.
Analyze the following notes and respond in this exact format with clear section headers:

SHORT SUMMARY:
(3-5 sentences)

KEY POINTS:
- point 1
- point 2
(5-10 bullet points)

CHAPTER-WISE SUMMARY:
Chapter 1: ...
Chapter 2: ...
(Split content into logical chapters/sections; if no chapters exist, create thematic sections)

PRACTICE QUESTIONS:
1. Question?
2. Question?
(8-12 exam-style questions with brief answers on a new line prefixed with "Answer:")

NOTES:
{clipped}
"""

    response = client.chats.create(
      model=self.model,
      history=[
        {"author": "system", "content": "You help students summarize study material concisely."},
        {"author": "user", "content": prompt},
      ],
      temperature=0.4,
    )

    content = ""
    if hasattr(response, "output") and response.output:
      first_output = response.output[0]
      if hasattr(first_output, "content") and first_output.content:
        content = " ".join(part.text for part in first_output.content if hasattr(part, "text"))
      elif isinstance(first_output, dict):
        content_parts = [segment.get("text", "") for segment in first_output.get("content", []) if isinstance(segment, dict)]
        content = " ".join(content_parts)

    return self._parse_sections(content)

  def _parse_sections(self, content: str) -> dict[str, str]:
    sections = {
      "short_summary": "",
      "key_points": "",
      "chapter_summary": "",
      "practice_questions": "",
    }
    markers = {
      "SHORT SUMMARY:": "short_summary",
      "KEY POINTS:": "key_points",
      "CHAPTER-WISE SUMMARY:": "chapter_summary",
      "PRACTICE QUESTIONS:": "practice_questions",
    }
    current = None
    lines: list[str] = []
    for line in content.splitlines():
      matched = False
      for marker, key in markers.items():
        if line.strip().upper().startswith(marker):
          if current:
            sections[current] = "\n".join(lines).strip()
          current = key
          lines = []
          remainder = line.split(":", 1)
          if len(remainder) > 1 and remainder[1].strip():
            lines.append(remainder[1].strip())
          matched = True
          break
      if not matched and current:
        lines.append(line)
    if current:
      sections[current] = "\n".join(lines).strip()
    if not any(sections.values()):
      sections["short_summary"] = content.strip()
    return sections

  def _generate_fallback(self, text: str) -> dict[str, str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if len(s.split()) > 4]
    short = " ".join(sentences[:3]) if sentences else text[:500]

    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    common = [w for w, _ in Counter(words).most_common(12) if w not in _STOPWORDS]
    key_points = "\n".join(f"- Important concept: {word.title()}" for word in common[:8])

    chunks = _chunk_text(text, 3)
    chapter_lines = [f"Section {i + 1}: {chunk[:280]}..." for i, chunk in enumerate(chunks)]
    chapter_summary = "\n".join(chapter_lines)

    questions = []
    for i, sentence in enumerate(sentences[:6], start=1):
      topic = sentence[:80].rstrip(".") + "?"
      questions.append(f"{i}. What is the main idea of: {topic}")
      questions.append(f"   Answer: {sentence[:200]}")
    practice_questions = "\n".join(questions)

    return {
      "short_summary": short,
      "key_points": key_points or "- Review the uploaded content carefully.",
      "chapter_summary": chapter_summary or "Section 1: " + text[:300],
      "practice_questions": practice_questions or "1. Summarize the main topic in your own words.",
    }


_STOPWORDS = {
  "that", "this", "with", "from", "have", "will", "been", "were", "they",
  "their", "about", "which", "when", "where", "there", "these", "those",
  "into", "than", "then", "also", "only", "some", "such", "what", "your",
}


def _chunk_text(text: str, parts: int) -> list[str]:
  size = max(len(text) // parts, 1)
  return [text[i : i + size].strip() for i in range(0, len(text), size) if text[i : i + size].strip()]
