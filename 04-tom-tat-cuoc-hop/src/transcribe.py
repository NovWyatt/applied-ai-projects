"""Chép lời bản ghi âm bằng faster-whisper chạy cục bộ, kèm mốc thời gian.

Chạy từ thư mục 04-tom-tat-cuoc-hop:

    python -m src.transcribe data/audio/H01.mp3 --nguoi-du Lan Minh Hùng Trang
"""

import argparse
import os
import sys
from functools import lru_cache
from pathlib import Path

from src.data import PROJECT_DIR, Line, format_transcript

# Mô hình Whisper tải về models/ của dự án thay vì ~/.cache trong thư mục người dùng.
os.environ.setdefault("HF_HOME", str(PROJECT_DIR / "models" / "huggingface"))
# Windows chưa bật symlink: Hugging Face chép file thay vì tạo liên kết, chỉ tốn thêm chỗ cho file nhỏ.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

WHISPER_MODEL = "large-v3-turbo"


@lru_cache(maxsize=2)
def get_model(size: str = WHISPER_MODEL):
    from faster_whisper import WhisperModel

    # int8 trên CPU: chạy được trên mọi máy, không cần CUDA.
    return WhisperModel(size, device="cpu", compute_type="int8")


def names_prompt(attendees: list[str]) -> str:
    """Câu mồi cho Whisper: nghe "Minh" thay vì "mình", "Trang" thay vì "trang"."""
    return f"Cuộc họp có {', '.join(attendees)}." if attendees else ""


def transcribe(audio_path: str | Path, attendees: list[str] | None = None, size: str = WHISPER_MODEL,
               hint: bool = True) -> list[Line]:
    segments, _ = get_model(size).transcribe(
        str(audio_path), language="vi", vad_filter=True,
        initial_prompt=names_prompt(attendees or []) if hint else None,
    )
    return [Line(segment.start, segment.text.strip()) for segment in segments]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Chép lời bản ghi âm, kèm mốc thời gian.")
    parser.add_argument("audio", type=Path)
    parser.add_argument("--nguoi-du", nargs="*", default=[], help="tên người dự họp, giúp nghe đúng tên")
    parser.add_argument("--model", default=WHISPER_MODEL)
    args = parser.parse_args()
    print(format_transcript(transcribe(args.audio, args.nguoi_du, args.model)))


if __name__ == "__main__":
    main()
