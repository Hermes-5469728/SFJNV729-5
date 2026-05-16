SAMPLE_DIRTY_HTML = """<!DOCTYPE html>
<html>
<body>
<h1>标题</h1>
<p>这是一段<p>嵌套标签</p>的文本。</p>
<p>含有&amp;实体&nbsp;字符。</p>
<script>alert('xss')</script>
<div>广告：联系微信 abc123 了解更多</div>
</body>
</html>"""

SAMPLE_CLEANED = "标题\n这是一段嵌套标签的文本。\n含有 实体 字符。\n"

SAMPLE_DUPLICATES = [
    "今天天气真好，适合出去散步。",
    "今天天气真好，适合出去散步。",
    "今日天气不错，宜外出散步。",
    "Python是一种流行的编程语言。",
    "Python 是一种广泛使用的编程语言。",
    "机器学习是人工智能的一个子领域。",
]

SAMPLE_NON_DUPLICATES = [
    "今天天气真好，适合出去散步。",
    "量子计算是计算技术的前沿领域。",
    "Python是一种流行的编程语言。",
]

SAMPLE_MIXED_LANG = [
    "今天天气真好，适合出去散步。",
    "The weather is nice today, perfect for a walk.",
    "今日の天気は本当にいいですね。",
    "Python是一种编程语言。",
    "This is a test sentence in English.",
    "これはテストです。",
]

SAMPLE_LOW_QUALITY = [
    "的 了 是 在 有 和 就 不 人 都 一 个 上 也 很 到 说 要 去 你 会 着 没 看 好 自己 这 他 她 们 我",
    "今天天气真好，适合出去散步。公园里有很多人在跑步，还有一些人在打太极拳。生活真美好。",
    "啊 哦 嗯 呃 喂 嗨 哈 嘿 哟 啦 呗 吗 吧 呀 呢 嘛 呵 哈",
]

SAMPLE_DIRTY_JSONL = """{"text": "  <p>前  后  有  空  格</p>  "}
{"text": "Normal text without issues."}
{"text": "重复的文档。重复的文档。重复的文档。"}"""

PIPELINE_EXPECTATIONS = {
    "strip_html": {
        "input": "<p>Hello</p><div>World</div>",
        "expected": "HelloWorld",
    },
    "normalize_unicode": {
        "input": "Ｈｅｌｌｏ\u3000世界\r\n",
        "expected": "Hello 世界\n",
    },
    "collapse_whitespace": {
        "input": "a    b   c\n\n\n\nd",
        "expected": "a b c\n\nd",
    },
}
