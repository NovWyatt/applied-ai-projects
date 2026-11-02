"""Đánh giá hai bước: chép lời (Whisper) và rút đầu việc (mô hình ngôn ngữ).

Chạy mô hình rất lâu trên CPU/GPU nhỏ, nên kết quả được lưu lại:
- data/asr_snapshot.json: biên bản Whisper chép từ ghi âm.
- data/llm_snapshot.json: câu trả lời của mô hình ngôn ngữ.

    python -m src.evaluate                # tính bảng từ bản lưu, vài giây, không cần mô hình
    python -m src.evaluate --refresh-asr  # chép lời lại (cần Whisper)
    python -m src.evaluate --refresh-llm  # rút đầu việc lại (cần Ollama đang chạy)
"""

import argparse
import json
import sys
import time

import av
import pandas as pd

from src.data import AUDIO_DIR, DATA_DIR, TRANSCRIPTS_DIR, format_transcript, load_meetings, parse_transcript
from src.extract import MeetingNotes, extract, review
from src.scoring import match_items, name_hits, same_deadline, same_person, wer

ASR_SNAPSHOT = DATA_DIR / "asr_snapshot.json"
LLM_SNAPSHOT = DATA_DIR / "llm_snapshot.json"

# (mô hình Whisper, có gợi ý tên người dự họp không)
ASR_CONFIGS = [("small", False), ("small", True), ("large-v3-turbo", False), ("large-v3-turbo", True)]
ASR_FOR_LLM = "large-v3-turbo|goi-y"
LLM_MODELS = ["qwen3.5:2b-q4_K_M", "qwen3.5:4b"]
INPUTS = {"bien-ban": "Biên bản có tên người nói", "ghi-am": "Chép từ ghi âm (Whisper)"}


def asr_key(size: str, hint: bool) -> str:
    return f"{size}|{'goi-y' if hint else 'khong-goi-y'}"


def gold_transcript(meeting: dict) -> str:
    return (TRANSCRIPTS_DIR / f"{meeting['id']}.txt").read_text(encoding="utf-8")


def refresh_asr(meetings: list[dict]) -> None:
    from src.transcribe import transcribe

    snapshot = {}
    for size, hint in ASR_CONFIGS:
        runs = snapshot[asr_key(size, hint)] = {}
        for meeting in meetings:
            start = time.perf_counter()
            lines = transcribe(AUDIO_DIR / f"{meeting['id']}.mp3", meeting["nguoi_du"], size, hint)
            runs[meeting["id"]] = {"bien_ban": format_transcript(lines), "giay": round(time.perf_counter() - start, 1)}
            print(f"{size} {'gợi ý' if hint else ''} {meeting['id']}: {runs[meeting['id']]['giay']} giây")
    ASR_SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")


def input_lines(meeting: dict, source: str, asr: dict):
    text = gold_transcript(meeting) if source == "bien-ban" else asr[ASR_FOR_LLM][meeting["id"]]["bien_ban"]
    return parse_transcript(text, meeting["nguoi_du"])


def refresh_llm(meetings: list[dict], asr: dict) -> None:
    snapshot = {}
    for model in LLM_MODELS:
        for source in INPUTS:
            runs = snapshot.setdefault(model, {})[source] = {}
            for meeting in meetings:
                start = time.perf_counter()
                notes = extract(input_lines(meeting, source, asr), meeting["nguoi_du"], meeting["tieu_de"],
                                meeting["ngay"], model=model)
                runs[meeting["id"]] = {"ket_qua": notes.model_dump(), "giay": round(time.perf_counter() - start, 1)}
                print(f"{model} {source} {meeting['id']}: {len(notes.dau_viec)} việc, {runs[meeting['id']]['giay']} giây")
    LLM_SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")


def audio_seconds(meeting: dict) -> float:
    with av.open(str(AUDIO_DIR / f"{meeting['id']}.mp3")) as container:
        return container.duration / av.time_base


def asr_table(meetings: list[dict], asr: dict) -> pd.DataFrame:
    total_seconds = sum(audio_seconds(m) for m in meetings)
    refs = [" ".join(line.text for line in parse_transcript(gold_transcript(m), m["nguoi_du"])) for m in meetings]
    rows = []
    for size, hint in ASR_CONFIGS:
        runs = asr[asr_key(size, hint)]
        hyps = [" ".join(line.text for line in parse_transcript(runs[m["id"]]["bien_ban"], m["nguoi_du"]))
                for m in meetings]
        found, total = map(sum, zip(*(name_hits(r, h, m["nguoi_du"]) for r, h, m in zip(refs, hyps, meetings))))
        rows.append({"Whisper": size, "Gợi ý tên người dự": "có" if hint else "không",
                     "Tỉ lệ lỗi từ (WER)": f"{sum(wer(r, h) * len(r.split()) for r, h in zip(refs, hyps)) / sum(len(r.split()) for r in refs):.0%}",
                     "Tên chép đúng": f"{found}/{total}",
                     "Giây xử lý / phút ghi âm": f"{sum(runs[m['id']]['giay'] for m in meetings) / total_seconds * 60:.1f}"})
    return pd.DataFrame(rows)


def score_run(meetings: list[dict], runs: dict, source: str, asr: dict) -> tuple[dict, list[dict]]:
    counts = dict.fromkeys(["dung", "tim_thay", "thua", "thua_co_co", "phu_trach", "han", "lot_luoi", "canh_bao",
                            "bao_nham"], 0)
    details = []
    for meeting in meetings:
        notes = MeetingNotes.model_validate(runs[meeting["id"]]["ket_qua"])
        lines = input_lines(meeting, source, asr)
        truth = meeting["dau_viec"]
        matched = match_items([item.viec for item in notes.dau_viec], truth)
        counts["dung"] += len(truth)
        counts["tim_thay"] += len(matched)
        counts["thua"] += len(notes.dau_viec) - len(matched)
        for t, p in matched.items():
            item, want = notes.dau_viec[p], truth[t]
            flags = review(item, lines, meeting["nguoi_du"])
            for field, same in [("phu_trach", same_person), ("han", same_deadline)]:
                ok = same(getattr(item, field), want[field])
                counts[field] += ok
                counts["canh_bao"] += field in flags
                counts["bao_nham"] += ok and field in flags
                if not ok and getattr(item, field) and field not in flags:
                    counts["lot_luoi"] += 1
                if not ok or field in flags:
                    details.append({"Họp": meeting["id"], "Việc": want["viec"], "Trường": field,
                                    "Đúng": want[field] or "(trống)", "Máy ghi": getattr(item, field) or "(trống)",
                                    "Cảnh báo": flags.get(field, "")})
        used = set(matched.values())
        for p, item in enumerate(notes.dau_viec):
            if p not in used:
                flags = review(item, lines, meeting["nguoi_du"])
                counts["thua_co_co"] += bool(flags)
                details.append({"Họp": meeting["id"], "Việc": item.viec, "Trường": "thừa", "Đúng": "(không có việc này)",
                                "Máy ghi": f"{item.phu_trach or '-'} / {item.han or '-'}",
                                "Cảnh báo": "; ".join(flags.values())})
        details += [{"Họp": meeting["id"], "Việc": truth[t]["viec"], "Trường": "bỏ sót", "Đúng": "", "Máy ghi": "",
                     "Cảnh báo": ""} for t in range(len(truth)) if t not in matched]
    return counts, details


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-asr", action="store_true")
    parser.add_argument("--refresh-llm", action="store_true")
    args = parser.parse_args()
    meetings = load_meetings()
    if args.refresh_asr:
        refresh_asr(meetings)
    asr = json.loads(ASR_SNAPSHOT.read_text(encoding="utf-8"))
    if args.refresh_llm:
        refresh_llm(meetings, asr)
    llm = json.loads(LLM_SNAPSHOT.read_text(encoding="utf-8"))

    print(f"{len(meetings)} cuộc họp mẫu, {sum(len(m['dau_viec']) for m in meetings)} đầu việc đúng.\n")
    print("== Chép lời ==")
    print(asr_table(meetings, asr).to_string(index=False))

    print(f"\n== Rút đầu việc (đầu vào ghi âm dùng {ASR_FOR_LLM}) ==")
    rows, all_details = [], {}
    for model in LLM_MODELS:
        for source, label in INPUTS.items():
            runs = llm[model][source]
            c, all_details[(model, source)] = score_run(meetings, runs, source, asr)
            rows.append({"Mô hình": model, "Đầu vào": label, "Tìm thấy": f"{c['tim_thay']}/{c['dung']}",
                         "Thừa (có cờ)": f"{c['thua']} ({c['thua_co_co']})",
                         "Phụ trách đúng": f"{c['phu_trach']}/{c['tim_thay']}",
                         "Hạn đúng": f"{c['han']}/{c['tim_thay']}", "Cảnh báo": c["canh_bao"],
                         "Báo nhầm": c["bao_nham"], "Sai lọt lưới": c["lot_luoi"],
                         "Giây/cuộc họp": f"{sum(r['giay'] for r in runs.values()) / len(runs):.0f}"})
    print(pd.DataFrame(rows).to_string(index=False))

    for (model, source), details in all_details.items():
        if model == LLM_MODELS[-1]:
            print(f"\n== {model}, {INPUTS[source]}: các chỗ sai ==")
            print(pd.DataFrame(details).to_string(index=False) if details else "(không có)")


if __name__ == "__main__":
    main()
