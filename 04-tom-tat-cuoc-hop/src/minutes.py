"""Từ bản ghi âm (hoặc biên bản .txt) ra tóm tắt và danh sách đầu việc.

Chạy từ thư mục 04-tom-tat-cuoc-hop, khi Ollama đang chạy:

    python -m src.minutes data/audio/H01.mp3 --nguoi-du Lan Minh Hùng Trang
    python -m src.minutes data/transcripts/H02.txt --nguoi-du Phong Ngọc Tuấn Vy -o output/H02.md
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.data import Line, format_time, format_transcript, parse_transcript
from src.extract import LLM_MODEL, ActionItem, MeetingNotes, extract, review

TEXT_SUFFIXES = {".txt", ".md"}


def load_lines(path: Path, attendees: list[str]) -> list[Line]:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return parse_transcript(path.read_text(encoding="utf-8"), attendees)
    from src.transcribe import transcribe

    return transcribe(path, attendees)


def review_all(notes: MeetingNotes, lines: list[Line], attendees: list[str]) -> list[dict[str, str]]:
    return [review(item, lines, attendees) for item in notes.dau_viec]


def timestamp(lines: list[Line], dong: int) -> str:
    return format_time(lines[dong - 1].start) if 0 < dong <= len(lines) else ""


def action_table(items: list[ActionItem], flags: list[dict[str, str]], lines: list[Line]) -> pd.DataFrame:
    labels = {"viec": "Việc", "phu_trach": "Phụ trách", "han": "Hạn"}
    return pd.DataFrame([{
        "Việc": item.viec, "Phụ trách": item.phu_trach, "Hạn": item.han, "Mốc": timestamp(lines, item.dong),
        "Cần kiểm tra": "; ".join(f"{labels.get(field, field)}: {reason}" for field, reason in flag.items()),
    } for item, flag in zip(items, flags)], columns=["Việc", "Phụ trách", "Hạn", "Mốc", "Cần kiểm tra"])


def to_markdown(title: str, attendees: list[str], notes: MeetingNotes, table: pd.DataFrame,
                lines: list[Line]) -> str:
    rows = ["| Việc | Phụ trách | Hạn | Mốc | Cần kiểm tra |", "|---|---|---|---|---|"]
    rows += [f"| {r['Việc']} | {r['Phụ trách'] or '—'} | {r['Hạn'] or '—'} | {r['Mốc']} | {r['Cần kiểm tra']} |"
             for _, r in table.iterrows()]
    return "\n".join([
        f"# {title or 'Biên bản họp'}", "",
        f"**Người dự:** {', '.join(attendees)}" if attendees else "", "",
        "## Tóm tắt", "", *[f"- {point}" for point in notes.tom_tat], "",
        "## Đầu việc", "", *(rows if len(table) else ["Không có đầu việc."]), "",
        "## Biên bản", "", "```", format_transcript(lines), "```", "",
    ])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Tóm tắt cuộc họp và rút đầu việc.")
    parser.add_argument("input", type=Path, help="bản ghi âm (mp3, wav, m4a...) hoặc biên bản .txt")
    parser.add_argument("--nguoi-du", nargs="*", default=[], help="tên người dự họp")
    parser.add_argument("--tieu-de", default="")
    parser.add_argument("--model", default=LLM_MODEL, help="mô hình Ollama")
    parser.add_argument("-o", "--output", type=Path, help="ghi biên bản Markdown, kèm file CSV đầu việc")
    args = parser.parse_args()

    lines = load_lines(args.input, args.nguoi_du)
    notes = extract(lines, args.nguoi_du, args.tieu_de, model=args.model)
    table = action_table(notes.dau_viec, review_all(notes, lines, args.nguoi_du), lines)
    markdown = to_markdown(args.tieu_de, args.nguoi_du, notes, table, lines)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
        # UTF-8 có BOM để Excel mở đúng tiếng Việt.
        table.to_csv(args.output.with_suffix(".csv"), index=False, encoding="utf-8-sig")
        print(f"Đã ghi {args.output} và {args.output.with_suffix('.csv')}")
    else:
        print(markdown)


if __name__ == "__main__":
    main()
