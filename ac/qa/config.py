# AC · Q 层配置
# s_5 实测评分: ω=0.05, 目标=80

SCORE_WEIGHTS = {
    "s1_coverage": 0.30,
    "s2_trigger_accuracy": 0.25,
    "s3_rule_clarity": 0.25,
    "s4_fallback_safety": 0.15,
    "s5_empirical": 0.05,
}

S5_TARGET = 80

QA_CONFIG = {
    "pipeline": {
        "cleaner": {
            "strip_html": True,
            "normalize_unicode": True,
            "collapse_whitespace": True,
            "min_text_length": 10,
            "max_text_length": 10000,
        },
        "deduplicator": {
            "minhash_num_perm": 128,
            "minhash_threshold": 0.8,
            "simhash_fingerprint_bits": 64,
            "simhash_hamming_threshold": 3,
        },
        "language_filter": {
            "min_zh_ratio": 0.5,
            "confidence_threshold": 0.6,
        },
        "quality_filter": {
            "ppl_threshold": 100,
            "ppl_model_name": "Qwen/Qwen2.5-0.5B",
            "fallback_ppl_model": "gpt2",
        },
    },
    "scoring": {
        "test_pass_weight": 0.4,
        "coverage_weight": 0.3,
        "precision_weight": 0.2,
        "speed_weight": 0.1,
    },
}
