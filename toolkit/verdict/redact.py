import re

_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(authorization:\s*bearer\s+)\S+"),
    re.compile(r"(?i)(api[_-]?key|token|secret)\s*[=:]\s*\S+"),
]


def redact(text: str) -> str:
    for p in _PATTERNS:
        text = p.sub("[REDACTED]", text)
    return text
