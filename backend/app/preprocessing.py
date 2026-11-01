"""Conservative Persian normalization; never silently remove negation or punctuation."""
import re
import unicodedata

CHAR_MAP = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "هٔ", "ـ": "", "\ufeff": ""})
WS = re.compile(r"[ \t\r\n\f\v]+")
ZERO_WIDTH = re.compile(r"[\u200b\u200d\u2060]")


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    text = unicodedata.normalize("NFC", text).translate(CHAR_MAP)
    # Preserve U+200C ZWNJ; it can carry morphological meaning in Persian.
    text = ZERO_WIDTH.sub("", text)
    text = WS.sub(" ", text).strip()
    if not text or all(unicodedata.category(c).startswith("C") for c in text):
        raise ValueError("Text must contain visible characters")
    return text
