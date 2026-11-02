"""Giao diện tóm tắt cuộc họp.

Chạy từ thư mục 04-tom-tat-cuoc-hop, khi Ollama đang chạy:

    streamlit run app.py
"""

import tempfile
from pathlib import Path

import streamlit as st

from src.data import AUDIO_DIR, TRANSCRIPTS_DIR, Line, format_transcript, load_meetings, parse_transcript
from src.extract import LLM_MODEL, MeetingNotes, extract
from src.minutes import action_table, review_all, to_markdown

st.set_page_config(page_title="Tóm tắt cuộc họp", page_icon="📝", layout="wide")


@st.cache_data(show_spinner="Đang chép lời bằng Whisper...")
def cached_transcribe(audio: bytes, suffix: str, attendees: tuple[str, ...]) -> str:
    from src.transcribe import transcribe

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / f"ghi-am{suffix}"
        path.write_bytes(audio)
        return format_transcript(transcribe(path, list(attendees)))


@st.cache_data(show_spinner=f"Đang rút đầu việc bằng {LLM_MODEL}...")
def cached_extract(transcript: str, attendees: tuple[str, ...], title: str, date: str) -> dict:
    return extract(parse_transcript(transcript, list(attendees)), list(attendees), title, date).model_dump()


st.title("📝 Tóm tắt cuộc họp")
st.caption("Chép lời bằng Whisper, rút đầu việc bằng mô hình ngôn ngữ chạy trên máy (Ollama). "
           "Không có thông tin thì để trống; ô đáng ngờ được đánh dấu để người kiểm tra.")

meetings = {m["id"]: m for m in load_meetings()}
left, right = st.columns([1, 3], gap="large")
with left:
    upload = st.file_uploader("Bản ghi âm hoặc biên bản .txt",
                              type=["mp3", "wav", "m4a", "ogg", "webm", "txt"])
    sample_id = st.selectbox("...hoặc chọn cuộc họp mẫu", meetings,
                             format_func=lambda i: f"{i} · {meetings[i]['tieu_de']}", disabled=upload is not None)
    sample = None if upload else meetings[sample_id]
    source = "Ghi âm"
    if sample:
        source = st.radio("Đầu vào", ["Ghi âm", "Biên bản có tên người nói"], horizontal=True,
                          help="Biên bản có tên người nói giống bản xuất từ Teams hay Google Meet.")
    attendees_text = st.text_input("Người dự (cách nhau bằng dấu phẩy)",
                                   ", ".join(sample["nguoi_du"]) if sample else "")
    attendees = tuple(name.strip() for name in attendees_text.split(",") if name.strip())
    title = sample["tieu_de"] if sample else (upload.name if upload else "")
    date = sample["ngay"] if sample else ""

    if upload and upload.name.lower().endswith(".txt"):
        transcript = upload.getvalue().decode("utf-8-sig")
    elif upload:
        st.audio(upload)
        transcript = None
    else:
        st.audio(str(AUDIO_DIR / f"{sample_id}.mp3"))
        transcript = ((TRANSCRIPTS_DIR / f"{sample_id}.txt").read_text(encoding="utf-8")
                      if source != "Ghi âm" else None)
    run = st.button("Tóm tắt", type="primary", width="stretch")

with right:
    if not run and "result" not in st.session_state:
        st.info("Chọn bản ghi rồi bấm **Tóm tắt**. Lần đầu nạp mô hình mất khoảng một phút.")
        st.stop()
    if run:
        if transcript is None:
            audio = upload.getvalue() if upload else (AUDIO_DIR / f"{sample_id}.mp3").read_bytes()
            suffix = Path(upload.name).suffix if upload else ".mp3"
            transcript = cached_transcribe(audio, suffix, attendees)
        try:
            notes = cached_extract(transcript, attendees, title, date)
        except ConnectionError:
            st.error("Không kết nối được Ollama. Mở Ollama (hoặc chạy `ollama serve`) rồi thử lại.")
            st.stop()
        st.session_state["result"] = (transcript, notes, attendees, title)

    transcript, notes, attendees, title = st.session_state["result"]
    notes = MeetingNotes.model_validate(notes)
    lines: list[Line] = parse_transcript(transcript, list(attendees))
    table = action_table(notes.dau_viec, review_all(notes, lines, list(attendees)), lines)

    st.subheader("Tóm tắt")
    st.markdown("\n".join(f"- {point}" for point in notes.tom_tat))
    st.subheader(f"Đầu việc ({len(table)})")
    flagged = table["Cần kiểm tra"].astype(bool).sum()
    if flagged:
        st.warning(f"{flagged} đầu việc cần kiểm tra lại. Nghe đoạn ghi âm tại cột **Mốc** rồi sửa trực tiếp trong bảng.")
    edited = st.data_editor(table, num_rows="dynamic", width="stretch", hide_index=True, column_config={
        "Việc": st.column_config.TextColumn(width="medium"),
        "Phụ trách": st.column_config.TextColumn(width="small"),
        "Hạn": st.column_config.TextColumn(width="small"),
        "Mốc": st.column_config.TextColumn(width="small", disabled=True),
        "Cần kiểm tra": st.column_config.TextColumn(width="medium", disabled=True),
    })
    st.download_button("Tải CSV đầu việc", edited.to_csv(index=False).encode("utf-8-sig"),
                       "dau-viec.csv", "text/csv")
    st.download_button("Tải biên bản Markdown", to_markdown(title, list(attendees), notes, edited, lines),
                       "bien-ban.md", "text/markdown")
    with st.expander("Biên bản đầy đủ"):
        st.code(transcript, language=None)
