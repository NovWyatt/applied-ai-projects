"""Rút tóm tắt và danh sách đầu việc từ biên bản, bằng mô hình ngôn ngữ chạy cục bộ (Ollama).

Mô hình phải trả JSON đúng schema (structured output của Ollama), nên không cần
đoán cách đọc câu trả lời. Sau đó review() soát từng đầu việc với chính biên bản.
"""

import os
import re

from pydantic import BaseModel, Field

from src.data import Line, format_transcript, normalize
from src.scoring import normalize_deadline

LLM_MODEL = os.environ.get("MEETING_LLM", "qwen3.5:4b")
# Soát người phụ trách và hạn trong dòng giao việc và NEIGHBORS dòng hai bên. Tên và hạn hay nằm
# ở dòng kề bên ("Để em làm slide." / "Ừ, xong trước thứ Ba nhé."). Trên dữ liệu mẫu: 0 dòng báo
# nhầm 2 lần, 1 dòng không lần nào, sai lọt lưới đều 0. Đổi lại, hạn của việc ở ngay dòng kề có thể lọt.
NEIGHBORS = 1
# Giữ dấu: bỏ dấu thì "mình" trùng tên "Minh", "chị" trùng "Chi".
PRONOUNS = {"em", "anh", "chị", "tôi", "mình", "bạn", "cô", "chú", "ông", "bà", "chúng tôi", "chúng ta"}
VAGUE_DEADLINES = ("khi nao tien", "khong gap", "tinh sau", "khi nao xong", "som nhat co the")


class ActionItem(BaseModel):
    # Số dòng thay vì mốc mm:ss: hỏi "mốc thời gian" thì mô hình hay ghi hạn chót ("sáng thứ Năm")
    # vào đó. Một số nguyên thì không nhầm được, và schema ép đúng kiểu khi sinh chữ.
    viec: str = Field(description="Việc cần làm, ngắn gọn, bắt đầu bằng động từ")
    phu_trach: str = Field(description="Tên người phụ trách; chuỗi rỗng nếu không rõ ai làm")
    han: str = Field(description="Hạn chót, chép đúng cách nói trong cuộc họp; chuỗi rỗng nếu không nhắc tới")
    dong: int = Field(description="Số thứ tự (trong ngoặc) của dòng giao việc trong biên bản")


class MeetingNotes(BaseModel):
    # Đầu việc đứng trước tóm tắt: mô hình sinh JSON theo thứ tự trường. Viết tóm tắt
    # trước thì có lúc nó đưa hết việc vào tóm tắt rồi trả danh sách đầu việc rỗng.
    dau_viec: list[ActionItem]
    tom_tat: list[str] = Field(description="2 đến 4 ý chính của cuộc họp")


# Cố ý không có câu "không có việc thì trả danh sách rỗng": có câu đó (viết kiểu nào cũng vậy),
# qwen3.5:4b trả rỗng cả với cuộc họp có 3 việc. Bỏ đi thì đôi khi nó bịa việc ở cuộc họp
# không giao việc gì; review() đánh dấu những việc không rõ ai làm, khi nào.
SYSTEM_PROMPT = """Bạn là thư ký cuộc họp. Đọc biên bản và trả về tóm tắt cùng danh sách đầu việc.

Quy tắc cho đầu việc:
- Chỉ ghi việc được giao hoặc được nhận làm sau cuộc họp. Bỏ qua việc đã làm xong, việc bị hủy, đề xuất bị gác lại và câu hỏi.
- Việc được giao lại cho người khác thì ghi người nhận sau cùng.
- phu_trach: chỉ ghi khi biên bản cho biết rõ ai làm. Không đoán. Không biết ai thì để chuỗi rỗng.
- han: chép đúng cách nói về hạn chót ("thứ Sáu tuần này", "15/11"). Không tự đổi ra ngày, không tự suy ra. "Khi nào tiện", "không gấp" không phải hạn chót. Không nhắc tới hạn thì để chuỗi rỗng.
- dong: số thứ tự (trong ngoặc) của dòng giao việc."""


def build_prompt(lines: list[Line], attendees: list[str], title: str = "", date: str = "") -> str:
    has_speakers = any(line.speaker for line in lines)
    who = ("Mỗi dòng có tên người nói." if has_speakers else
           'Biên bản chép từ ghi âm, KHÔNG có tên người nói: "em", "anh", "chị", "tôi" không cho biết là ai.')
    header = [f"Cuộc họp: {title}" if title else "", f"Ngày: {date}" if date else "",
              f"Người dự: {', '.join(attendees)}" if attendees else "", who]
    numbered = "\n".join(f"({i}) {format_transcript([line])}" for i, line in enumerate(lines, 1))
    return "\n".join(part for part in header if part) + "\n\nBiên bản:\n" + numbered


def extract(lines: list[Line], attendees: list[str], title: str = "", date: str = "",
            model: str = LLM_MODEL) -> MeetingNotes:
    import ollama

    response = ollama.chat(
        model=model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": build_prompt(lines, attendees, title, date)}],
        format=MeetingNotes.model_json_schema(),
        think=False,  # suy luận chậm gấp 3 lần mà không trích đúng hơn trên dữ liệu mẫu
        options={"temperature": 0, "num_ctx": 8192},
    )
    return MeetingNotes.model_validate_json(response.message.content)


def review(item: ActionItem, lines: list[Line], attendees: list[str]) -> dict[str, str]:
    """Soát một đầu việc với biên bản. Trả về {tên trường: lý do cần người kiểm tra}.

    Trường nào có trong kết quả sẽ hiện cờ "Cần kiểm tra" trên giao diện, và được
    tính là đã cảnh báo (không phải "sai lọt lưới") khi đánh giá.
    """
    filled = {field: value for field in ("phu_trach", "han") if (value := getattr(item, field).strip())}
    if not filled:
        # Để trống là đúng quy tắc, nhưng một việc không ai nhận, không hạn thì hoặc là việc
        # còn treo, hoặc là mô hình bịa ra ("hẹn họp tuần sau"); cả hai đều cần người xem.
        return {"viec": "chưa rõ ai làm và hạn khi nào"}
    nearby = lines_near(lines, item.dong)
    if nearby is None:
        return {field: f"dòng {item.dong} không có trong biên bản" for field in filled}

    flags = {}
    if owner := filled.get("phu_trach"):
        if owner.lower() in PRONOUNS:
            flags["phu_trach"] = f'"{owner}" là đại từ, không rõ là ai'
        elif normalize(owner) not in {normalize(name) for name in attendees}:
            flags["phu_trach"] = f'"{owner}" không có trong danh sách người dự'
        elif not any(said_by(line, owner) or mentions(line.text, owner) for line in nearby):
            flags["phu_trach"] = "không thấy tên này ở đoạn giao việc"
    if deadline := filled.get("han"):
        wanted = normalize_deadline(deadline)
        if any(phrase in wanted for phrase in VAGUE_DEADLINES):
            flags["han"] = f'"{deadline}" không phải hạn chót'
        elif not any(re.search(rf"(?<!\w){re.escape(wanted)}(?!\w)", normalize_deadline(line.text))
                     for line in nearby):
            flags["han"] = "không thấy hạn này ở đoạn giao việc"
    return flags


def lines_near(lines: list[Line], dong: int) -> list[Line] | None:
    """Dòng giao việc (đánh số từ 1) và NEIGHBORS dòng hai bên; None nếu không có dòng đó."""
    index = dong - 1
    if not 0 <= index < len(lines):
        return None
    return lines[max(index - NEIGHBORS, 0):index + NEIGHBORS + 1]


def said_by(line: Line, name: str) -> bool:
    """Người nói tự nhận việc ("để em làm") chỉ biết được khi biên bản có tên người nói."""
    return line.speaker is not None and normalize(line.speaker) == normalize(name)


def mentions(text: str, name: str) -> bool:
    # So cả dấu: bỏ dấu thì "mình gửi báo giá" sẽ khớp với tên "Minh".
    return re.search(rf"(?<!\w){re.escape(name.lower())}(?!\w)", text.lower()) is not None
