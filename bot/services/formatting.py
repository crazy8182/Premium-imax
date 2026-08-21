"""Formatting helpers for Telegram captions."""
import html
import re

_SMALL_CAPS = str.maketrans({
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ", "f": "ꜰ",
    "g": "ɢ", "h": "ʜ", "i": "ɪ", "j": "ᴊ", "k": "ᴋ", "l": "ʟ",
    "m": "ᴍ", "n": "ɴ", "o": "ᴏ", "p": "ᴘ", "q": "Q", "r": "ʀ",
    "s": "ꜱ", "t": "ᴛ", "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x", "y": "ʏ",
    "z": "ᴢ",
})
_TAG_RE = re.compile(r"(<[^>]+>)")

def small_caps(text: str) -> str:
    """Convert visible Latin letters to small caps while keeping HTML tags intact."""
    parts = _TAG_RE.split(text or "")
    for i, part in enumerate(parts):
        if not part.startswith("<"):
            parts[i] = html.escape(part).translate(_SMALL_CAPS)
    return "".join(parts)

def bold_small_caps(text: str) -> str:
    """Return HTML bold + small-caps formatted text."""
    return f"<b>{small_caps(text)}</b>"
