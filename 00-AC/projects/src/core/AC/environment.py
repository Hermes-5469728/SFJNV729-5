"""动态环境注入 — 解决 Prompt 中 <time_location> 时空僵化问题"""

import platform
import socket
from datetime import datetime, timezone, timedelta
from typing import Optional


def inject_dynamic_context(prompt_template: str) -> str:
    now = datetime.now(timezone(timedelta(hours=8)))
    template_vars = {
        "{{datetime}}": now.strftime("%Y-%m-%d %H:%M:%S CST"),
        "{{date_iso}}": now.strftime("%Y-%m-%d"),
        "{{time_iso}}": now.strftime("%H:%M:%S"),
        "{{weekday}}": (
            "\u5468\u4e00", "\u5468\u4e8c", "\u5468\u4e09",
            "\u5468\u56db", "\u5468\u4e94", "\u5468\u516d", "\u5468\u65e5"
        )[now.weekday()],
        "{{unix_ts}}": str(int(now.timestamp())),
        "{{hostname}}": socket.gethostname(),
        "{{os}}": f"{platform.system()} {platform.release()}",
        "{{timezone}}": "Asia/Shanghai",
        "{{tz_offset}}": "+08:00",
        "{{geo_info}}": _get_geo_info(),
    }

    result = prompt_template
    for placeholder, value in template_vars.items():
        result = result.replace(placeholder, value)

    return result


def _get_geo_info() -> str:
    try:
        import json
        import urllib.request

        with urllib.request.urlopen(
            "http://ip-api.com/json/", timeout=3
        ) as resp:
            data = json.loads(resp.read())
            return (
                f"{data.get('city', '')}, "
                f"{data.get('regionName', '')}, "
                f"{data.get('country', '')}"
            )
    except Exception:
        return "\u672a\u77e5\u4f4d\u7f6e"


if __name__ == "__main__":
    template = (
        "\u4f60\u662f\u4e00\u4f4d\u4e34\u5e8a\u51b3\u7b56\u52a9\u624b\u3002\n"
        "\u5f53\u524d\u65f6\u95f4: {{datetime}} ({{weekday}})\n"
        "\u8fd0\u884c\u73af\u5883: {{os}} @ {{hostname}}\n"
        "\u65f6\u533a: {{timezone}}\n"
        "\u4f4d\u7f6e: {{geo_info}}\n"
    )
    filled = inject_dynamic_context(template)
    print(filled)
