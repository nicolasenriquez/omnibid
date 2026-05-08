from __future__ import annotations

import re
import unicodedata


def normalize_annotation_text(value: str | None) -> str | None:
    if value is None:
        return None

    text = unicodedata.normalize("NFKC", str(value))
    text = text.strip().lower()
    if text == "":
        return None

    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    if text == "":
        return None
    return text
