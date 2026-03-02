"""
ML Service - Product Summarization
Uses HuggingFace facebook/bart-large-cnn model.
Falls back to extractive summarization if model unavailable.
"""

import re
from typing import Optional

# Lazy-load to avoid slow startup if transformers not installed
_summarizer = None
_model_name  = "facebook/bart-large-cnn"


def _load_model():
    """Load the HuggingFace summarization pipeline (cached after first load)."""
    global _summarizer
    if _summarizer is None:
        try:
            from transformers import pipeline
            _summarizer = pipeline(
                "summarization",
                model=_model_name,
                tokenizer=_model_name,
                framework="pt"      # PyTorch
            )
            print(f"[ML] Model '{_model_name}' loaded successfully.")
        except Exception as e:
            print(f"[ML] Could not load transformer model: {e}")
            _summarizer = "fallback"
    return _summarizer


def _extractive_fallback(text: str, max_sentences: int = 3) -> str:
    """
    Simple extractive summarization:
    Picks most 'important' sentences by word frequency scoring.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= max_sentences:
        return text

    # Word frequency
    words = re.findall(r'\w+', text.lower())
    stop_words = {
        "the", "a", "an", "is", "it", "in", "on", "at", "to", "for",
        "of", "and", "or", "but", "with", "this", "that", "are", "was",
        "be", "by", "as", "from", "has", "have", "had"
    }
    freq = {}
    for w in words:
        if w not in stop_words and len(w) > 2:
            freq[w] = freq.get(w, 0) + 1

    # Score sentences
    scored = []
    for sent in sentences:
        score = sum(freq.get(w.lower(), 0) for w in re.findall(r'\w+', sent))
        scored.append((score, sent))

    top = sorted(scored, reverse=True)[:max_sentences]
    # Maintain original order
    top_sents = [s for _, s in sorted(
        [(sentences.index(sent), sent) for _, sent in top]
    )]
    return " ".join(top_sents)


def generate_product_summary(
    product_name: str,
    product_description: str,
    max_length: int = 130,
    min_length: int = 30
) -> dict:
    """
    Generate an AI product summary.

    1. Tries HuggingFace BART model (deep learning summarization).
    2. Falls back to extractive summarization if model not available.
    """
    if not product_description or len(product_description.strip()) < 20:
        return {
            "success": False,
            "error": "Product description too short. Provide at least 20 characters."
        }

    # Prepend product name for context
    full_text = f"Product: {product_name}. {product_description}"

    # Clamp lengths to avoid model errors
    word_count  = len(full_text.split())
    safe_max    = min(max_length, max(word_count - 10, 30))
    safe_min    = min(min_length, safe_max - 5)

    model = _load_model()

    # ── HuggingFace BART ──────────────────────────────────────
    if model != "fallback":
        try:
            result = model(
                full_text,
                max_length=safe_max,
                min_length=safe_min,
                do_sample=False
            )
            summary = result[0]["summary_text"]
            return {
                "success": True,
                "summary": summary,
                "model_used": _model_name
            }
        except Exception as e:
            print(f"[ML] Transformer inference failed: {e}. Using fallback.")

    # ── Extractive Fallback ───────────────────────────────────
    summary = _extractive_fallback(full_text, max_sentences=3)
    return {
        "success": True,
        "summary": summary,
        "model_used": "extractive-fallback"
    }
