import math
import os

from ac.qa.config import QA_CONFIG

# Offline-first: no remote downloads
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "5"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


def _model_available(model_name: str) -> bool:
    try:
        from transformers import AutoTokenizer
        AutoTokenizer.from_pretrained(model_name, local_files_only=True)
        return True
    except Exception:
        return False


def _compute_ppl(text: str, model_name: str) -> float | None:
    try:
        if not _model_available(model_name):
            return None
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name, local_files_only=True, torch_dtype="auto", device_map="auto"
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs, labels=inputs["input_ids"])
        loss = outputs.loss.item()
        return math.exp(loss)
    except Exception:
        return None


def compute_perplexity(text: str) -> float | None:
    ppl = _compute_ppl(text, QA_CONFIG["pipeline"]["quality_filter"]["ppl_model_name"])
    if ppl is not None:
        return ppl
    ppl = _compute_ppl(text, QA_CONFIG["pipeline"]["quality_filter"]["fallback_ppl_model"])
    if ppl is not None:
        return ppl
    return None


def is_quality_text(text: str) -> tuple[bool, float | None]:
    ppl = compute_perplexity(text)
    if ppl is None:
        return (True, None)
    threshold = QA_CONFIG["pipeline"]["quality_filter"]["ppl_threshold"]
    return (ppl <= threshold, round(ppl, 2))
