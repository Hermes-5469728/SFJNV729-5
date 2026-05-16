"""ocr_med.py — 医学课本照片 OCR
安装: 双击 install_ocr.bat
用法: python ocr_med.py [图片路径或目录]
"""

import sys, json, os, re
from pathlib import Path

def ocr_image(img_path: str) -> list[dict]:
    import pytesseract
    from PIL import Image
    img = Image.open(img_path)
    data = pytesseract.image_to_data(img, lang='chi_sim+eng', output_type=pytesseract.Output.DICT)
    lines = []
    current_line = ""
    for i, text in enumerate(data['text']):
        if text.strip():
            if current_line and data['line_num'][i] != current_line_num:
                lines.append({"text": current_line.strip(), "conf": round(data['conf'][i-1] if i > 0 else 0, 1)})
                current_line = ""
            current_line += text + " "
            current_line_num = data['line_num'][i]
    if current_line.strip():
        lines.append({"text": current_line.strip(), "conf": 0})
    return lines

def batch_ocr(directory: str):
    results = {}
    for f in sorted(Path(directory).glob("*.jpg")):
        print(f"扫描: {f.name}...")
        lines = ocr_image(str(f))
        results[f.name] = lines
        for l in lines[:5]:
            print(f"  {l['text'][:60]}")
        print(f"  → {len(lines)} 行\n")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  单文件: python ocr_med.py D:\\path\\photo.jpg")
        print("  批量:   python ocr_med.py D:\\36854\\临床医学\\内科学")
        sys.exit(1)

    path = sys.argv[1]
    if not Path(path).exists():
        print(f"文件不存在: {path}")
        sys.exit(1)

    if Path(path).is_dir():
        results = batch_ocr(path)
        out = Path(path) / "_ocr_results.json"
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"全部结果已保存: {out}")
    else:
        lines = ocr_image(path)
        print(json.dumps(lines, ensure_ascii=False, indent=2))
        print(f"\n共 {len(lines)} 行")
