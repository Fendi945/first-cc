"""Transcribe audio with faster-whisper, save full transcript with timestamps."""
import json
import os
from faster_whisper import WhisperModel

audio_path = os.path.join(os.path.dirname(__file__), "audio.wav")
output_path = os.path.join(os.path.dirname(__file__), "transcript.json")

print(f"Transcribing {audio_path}...")
model = WhisperModel("base", device="cpu", compute_type="int8")

segments, info = model.transcribe(audio_path, beam_size=5, word_timestamps=True)

print(f"Detected language: {info.language} (p={info.language_probability:.2f})")

result = {
    "language": info.language,
    "language_probability": info.language_probability,
    "segments": [],
    "words": [],
    "full_text": "",
}

full_text_parts = []
for seg in segments:
    seg_data = {
        "start": round(seg.start, 3),
        "end": round(seg.end, 3),
        "text": seg.text.strip(),
        "words": [],
    }
    if seg.words:
        for w in seg.words:
            word_data = {
                "start": round(w.start, 3),
                "end": round(w.end, 3),
                "word": w.word.strip(),
                "probability": round(w.probability, 3) if w.probability else None,
            }
            seg_data["words"].append(word_data)
            result["words"].append(word_data)

    result["segments"].append(seg_data)
    full_text_parts.append(seg_data["text"])

result["full_text"] = " ".join(full_text_parts)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\nTranscription saved to {output_path}")
print(f"Total segments: {len(result['segments'])}")
print(f"Total words: {len(result['words'])}")
print(f"Total duration: {result['segments'][-1]['end']:.1f}s" if result['segments'] else "No segments")
