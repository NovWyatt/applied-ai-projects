"""Đọc cuộc họp mẫu và đọc/ghi biên bản dạng "[mm:ss] Tên: lời nói"."""

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
MEETINGS_JSON = DATA_DIR / "meetings.json"
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"


@dataclass
class Line:
    start: float              # giây tính từ đầu bản ghi
    text: str
    speaker: str | None = None  # None khi chép lời từ âm thanh (không biết ai nói)


def load_meetings() -> list[dict]:
    return json.loads(MEETINGS_JSON.read_text(encoding="utf-8"))


def normalize(text: str) -> str:
    """Chữ thường, bỏ dấu, bỏ dấu câu: "Thứ Sáu," -> "thu sau"."""
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^\w/]+", " ", text).split())


def format_time(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def format_transcript(lines: list[Line]) -> str:
    return "\n".join(f"[{format_time(line.start)}] " + (f"{line.speaker}: " if line.speaker else "") + line.text
                     for line in lines)


LINE_RE = re.compile(r"^\[(\d+):(\d{2})\]\s*(.*)$")


def parse_transcript(text: str, attendees: list[str] | None = None) -> list[Line]:
    """Đọc biên bản dạng "[mm:ss] Tên: lời nói" (tên người nói không bắt buộc).

    Phần trước dấu hai chấm chỉ được coi là tên khi nằm trong danh sách người dự
    (nếu có), để "[00:05] Lưu ý: ..." không bị hiểu thành người tên "Lưu ý".
    """
    known = {normalize(name) for name in attendees or []}
    lines = []
    for raw in text.splitlines():
        match = LINE_RE.match(raw.strip())
        if not match:
            continue
        minutes, secs, rest = match.groups()
        speaker, sep, said = rest.partition(":")
        if sep and (normalize(speaker) in known if known else len(speaker.split()) <= 3):
            lines.append(Line(int(minutes) * 60 + int(secs), said.strip(), speaker.strip()))
        else:
            lines.append(Line(int(minutes) * 60 + int(secs), rest.strip()))
    return lines
