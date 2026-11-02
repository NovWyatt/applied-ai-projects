"""Đọc kịch bản họp thành bản ghi âm, bằng Piper chạy cục bộ.

Piper chỉ có một giọng tiếng Việt đủ rõ (vais1000, giọng nữ). Mỗi người được đổi
cao độ khác nhau bằng cách kéo giãn tín hiệu, rồi bù lại tốc độ nói, để nghe ra
nhiều người. Có thêm chút tiếng ồn nền như phòng họp thật.

Ghi ra:
- data/audio/Hxx.mp3: bản ghi âm.
- data/transcripts/Hxx.txt: biên bản chuẩn "[mm:ss] Tên: lời nói", mốc thời gian thật.

Lần đầu cần tải giọng đọc (~63 MB) vào models/piper:

    python -m src.make_audio --download
    python -m src.make_audio
"""

import argparse
import io
import random
import sys
import urllib.request
import wave

import av
import numpy as np

from src.data import AUDIO_DIR, PROJECT_DIR, TRANSCRIPTS_DIR, Line, format_transcript, load_meetings

VOICE = "vi_VN-vais1000-medium"
VOICE_DIR = PROJECT_DIR / "models" / "piper"
VOICE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN/vais1000/medium/"
SAMPLE_RATE = 16000  # Whisper cần 16 kHz

# (độ giãn, tốc độ nói). Giãn > 1 làm giọng trầm như giọng nam.
SPEAKERS = {
    "Lan": (1.00, 1.00), "Trang": (0.94, 1.05), "Ngọc": (0.97, 0.95), "Vy": (0.92, 1.08),
    "Hà": (1.03, 1.00), "Mai": (0.95, 0.97), "Thảo": (1.02, 1.05), "Nhi": (0.93, 1.00),
    "Minh": (1.18, 1.00), "Hùng": (1.24, 0.95), "Phong": (1.20, 1.05), "Tuấn": (1.15, 1.03),
    "Quân": (1.22, 1.00), "Bình": (1.17, 0.96), "Long": (1.26, 1.04),
}


def download_voice() -> None:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    for ext in (".onnx", ".onnx.json"):
        target = VOICE_DIR / f"{VOICE}{ext}"
        if not target.exists():
            print(f"Tải {target.name}...")
            urllib.request.urlretrieve(VOICE_URL + target.name, target)


def resample(audio: np.ndarray, factor: float) -> np.ndarray:
    n = int(len(audio) * factor)
    return np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.float32)


def speak(voice, text: str, stretch: float, speed: float) -> np.ndarray:
    from piper import SynthesisConfig

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        voice.synthesize_wav(text, wav, syn_config=SynthesisConfig(length_scale=1 / (stretch * speed)))
    buffer.seek(0)
    with wave.open(buffer) as wav:
        rate = wav.getframerate()
        audio = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return resample(audio, stretch * SAMPLE_RATE / rate)


def write_mp3(path, audio: np.ndarray) -> None:
    with av.open(str(path), "w") as container:
        stream = container.add_stream("mp3", rate=SAMPLE_RATE, layout="mono")
        stream.bit_rate = 48_000
        samples = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
        frame = av.AudioFrame.from_ndarray(samples[None, :], format="s16", layout="mono")
        frame.sample_rate = SAMPLE_RATE
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)


def make_meeting(voice, meeting: dict, rng: random.Random) -> tuple[np.ndarray, list[Line]]:
    pieces, lines, t = [np.zeros(int(0.5 * SAMPLE_RATE), np.float32)], [], 0.5
    for speaker, text in meeting["loi_thoai"]:
        lines.append(Line(t, text, speaker))
        speech = speak(voice, text, *SPEAKERS[speaker])
        pause = np.zeros(int(rng.uniform(0.5, 1.0) * SAMPLE_RATE), np.float32)
        pieces += [speech, pause]
        t += (len(speech) + len(pause)) / SAMPLE_RATE
    audio = np.concatenate(pieces)
    noise = np.random.default_rng(rng.randrange(1 << 30)).normal(0, 0.004, len(audio)).astype(np.float32)
    return audio * 0.8 + noise, lines


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Đọc kịch bản họp thành bản ghi âm.")
    parser.add_argument("--download", action="store_true", help="tải giọng đọc Piper rồi thoát")
    args = parser.parse_args()
    if args.download:
        download_voice()
        return

    from piper import PiperVoice

    voice = PiperVoice.load(str(VOICE_DIR / f"{VOICE}.onnx"))
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(4)
    for meeting in load_meetings():
        audio, lines = make_meeting(voice, meeting, rng)
        write_mp3(AUDIO_DIR / f"{meeting['id']}.mp3", audio)
        (TRANSCRIPTS_DIR / f"{meeting['id']}.txt").write_text(format_transcript(lines) + "\n", encoding="utf-8")
        print(f"{meeting['id']}: {len(audio) / SAMPLE_RATE:.0f} giây, {len(lines)} lượt nói")


if __name__ == "__main__":
    main()
