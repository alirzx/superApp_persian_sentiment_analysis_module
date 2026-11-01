"""Stable softmax and strict mapping from the model's *actual* class IDs."""
from __future__ import annotations
import numpy as np

SENTIMENT_IDS = {"negative": "منفی", "neutral": "خنثی", "positive": "مثبت"}
TOPIC_EN = {
    "اجتماعی": "social", "اقتصادی": "economics", "بین الملل": "international",
    "سیاسی": "politics", "علمی فناوری": "science_technology",
    "فرهنگی هنری": "culture_art", "ورزشی": "sports", "پزشکی": "medical",
}


def make_prediction(task: str, logits, labels: list[str], meta: dict) -> dict:
    a = np.asarray(logits, dtype=np.float64).reshape(-1)
    if len(a) != len(labels) or not np.isfinite(a).all():
        raise ValueError("Invalid model logits")
    probs = np.exp(a - a.max())
    probs /= probs.sum()
    best = int(np.argmax(probs))
    pairs = [{"id": i, "label": str(name), "score": round(float(p), 6)} for i, (name, p) in enumerate(zip(labels, probs))]
    label = labels[best]
    english = label.lower() if task == "sentiment" else TOPIC_EN.get(label, label)
    return {
        "task": task,
        "label": english,
        "label_fa": SENTIMENT_IDS.get(english, label) if task == "sentiment" else label,
        "confidence": round(float(probs[best]), 6),
        "scores": pairs,
        "model": meta["repo"],
        "revision": meta["revision"],
        "runtime": "onnxruntime-cpu",
        "confidence_calibrated": False,
    }
