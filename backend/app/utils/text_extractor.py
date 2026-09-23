import os


def extract_text(file_path: str) -> str:
    """从常见文本类文件（pdf/doc/docx/txt/md）中抽取纯文本。"""
    if not os.path.exists(file_path):
        return ""

    ext = file_path.split(".")[-1].lower() if "." in file_path else ""

    try:
        if ext == "pdf":
            return _extract_pdf(file_path)
        elif ext in ("doc", "docx"):
            return _extract_docx(file_path)
        elif ext in ("txt", "md"):
            return _extract_txt(file_path)
        return ""
    except Exception:
        return ""


def _extract_pdf(file_path: str) -> str:
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(file_path: str) -> str:
    from docx import Document

    doc = Document(file_path)
    return "\n".join(para.text for para in doc.paragraphs)


def _extract_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()