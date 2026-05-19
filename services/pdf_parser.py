from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
  reader = PdfReader(BytesIO(file_bytes))
  pages: list[str] = []
  for page in reader.pages:
    text = page.extract_text() or ""
    if text.strip():
      pages.append(text.strip())
  if not pages:
    raise ValueError("No readable text found in this PDF.")
  return "\n\n".join(pages)
