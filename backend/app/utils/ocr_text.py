"""OCR 结果后处理：文本清洗、格式化与学科/知识点分类。

被 RapidOCR 与 PaddleOCR 两套引擎共用，避免重复实现。
"""

import re
from typing import Optional, Tuple

SUBJECT_KEYWORDS = {
    "数学": [
        "极限", "导数", "微分", "积分", "级数", "矩阵", "行列式",
        "向量", "概率", "随机变量", "方程", "不等式", "数列",
        "函数", "泰勒", "拉格朗日", "柯西", "偏导", "线性方程组",
        "特征值", "特征向量", "二次型", "分布", "期望", "方差",
    ],
    "英语": [
        "reading", "passage", "vocabulary", "grammar", "translation",
        "cloze", "essay", "writing", "verb", "noun", "adjective",
        "sentence", "paragraph", "comprehension", "blank",
    ],
    "政治": [
        "马克思", "唯物", "辩证", "毛泽东", "中国特色社会主义",
        "政治经济学", "哲学", "价值观", "矛盾", "实践", "认识论",
        "剩余价值", "资本", "共产主义", "改革开放", "社会主义",
    ],
}

KNOWLEDGE_POINTS = {
    "数学": {
        "高等数学-极限": ["极限", "收敛", "发散", "洛必达"],
        "高等数学-导数": ["导数", "微分", "偏导", "链式法则"],
        "高等数学-积分": ["积分", "定积分", "不定积分", "换元"],
        "线性代数": ["矩阵", "行列式", "特征值", "特征向量", "线性方程组"],
        "概率统计": ["概率", "分布", "期望", "方差", "随机变量"],
    },
    "英语": {
        "阅读理解": ["passage", "reading", "main idea", "author"],
        "完形填空": ["cloze", "blank", "fill"],
        "翻译": ["translate", "translation"],
        "写作": ["writing", "essay", "letter"],
    },
    "政治": {
        "马克思主义原理": ["马克思", "唯物", "辩证", "哲学"],
        "毛中特": ["毛泽东", "中国特色社会主义", "改革开放"],
        "政治经济学": ["剩余价值", "资本", "商品"],
    },
}

INVALID_PATTERNS = [
    r'^[\s\W]{3,}$',
    r'^[><=\-\+\*/\|\(\)\[\]{}]{2,}$',
    r'^[\d]{5,}$',
    r'^[a-zA-Z]{10,}$',
    r'^[^\w\u4e00-\u9fff]{4,}$',
    r'^[`~!@#$%^&*()_+\-=\[\]{}|;:,.<>?]{3,}$',
]

INVALID_KEYWORDS = [
    'undefined', 'null', 'NaN', 'error', 'failed', 'loading', 'list',
    'http://', 'https://', '.com', '.cn', '.org', '.net',
    'www.', 'mailto:', 'tel:', 'javascript:', 'function',
    'class', 'import', 'export', 'const', 'let', 'var',
    'console.', 'alert(', 'debugger', 'return', 'if(', 'for(', 'while(',
]

PUNCTUATION_END = ['。', '；', '！', '？', '.', ';', '!', '?', ':', '：']
PUNCTUATION_CONTINUE = [',', '，', '、', '—', '-', '…', '.', '·']
NUMBER_PREFIX = [
    '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '0.',
    '①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩',
    '一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、',
    '（1）', '（2）', '（3）', '（4）', '（5）',
    '(1)', '(2)', '(3)', '(4)', '(5)',
    '1)', '2)', '3)', '4)', '5)',
    '【', '[', '(',
]

HEADING_KEYWORDS = [
    '第一节', '第二节', '第三节', '第四节', '第五节',
    '第一章', '第二章', '第三章', '第四章', '第五章',
    '一、', '二、', '三、', '四、', '五、',
    '1.', '2.', '3.', '4.', '5.',
    '（一）', '（二）', '（三）', '（四）', '（五）',
    '(一)', '(二)', '(三)', '(四)', '(五)',
]

EMPHASIS_PATTERNS = [
    (r'【([^】]+)】', r'◆ \1'),
    (r'\[([^\]]+)\]', r'◇ \1'),
    (r'「([^」]+)」', r'▶ \1'),
    (r'《([^》]+)》', r'★ 《\1》'),
]

KEY_CONCEPTS = [
    '【背', '【选择题', '【简答题', '【辨析题', '【新增',
    '口诀', '注意', '重点', '核心', '关键',
    '决定', '制约', '作用', '功能', '影响',
    '特征', '规律', '原则', '方法', '理论',
]

LIST_INDICATORS = [
    '①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩',
    '⑴', '⑵', '⑶', '⑷', '⑸',
    '（1）', '（2）', '（3）', '（4）', '（5）',
    '(1)', '(2)', '(3)', '(4)', '(5)',
    '1)', '2)', '3)', '4)', '5)',
]


def _is_invalid_line(line: str) -> bool:
    line = line.strip()
    if not line or len(line) <= 1:
        return True

    for pattern in INVALID_PATTERNS:
        if re.match(pattern, line):
            return True

    line_lower = line.lower()
    for kw in INVALID_KEYWORDS:
        if kw in line_lower:
            return True

    char_count = sum(1 for c in line if '\u4e00' <= c <= '\u9fff')
    eng_count = sum(1 for c in line if c.isalpha())
    num_count = sum(1 for c in line if c.isdigit())
    total = len(line)

    if total > 0 and char_count == 0 and eng_count == 0:
        return True
    if total >= 5 and char_count == 0 and num_count >= total * 0.8:
        return True

    return False


def _is_heading(line: str) -> bool:
    line = line.strip()
    if not line:
        return False

    if re.match(r'^第[一二三四五六七八九十]+[章节节]', line):
        return True
    if re.match(r'^第[一二三四五六七八九十]+[、\.）)]', line):
        return True
    if re.match(r'^[\d]+[\.\uff0e][\s]*[\u4e00-\u9fff]{2,}', line):
        rest = line.split('.', 1)[1].strip()
        if len(rest) <= 40:
            return True
    if re.match(r'^[一二三四五六七八九十]+[、]', line):
        rest = line[2:].strip()
        if len(rest) <= 40:
            return True
    for kw in HEADING_KEYWORDS:
        if line.startswith(kw):
            rest = line[len(kw):].strip()
            if rest and len(rest) <= 50:
                return True
    if len(line) <= 30 and line.isupper():
        return True

    return False


def _emphasize_key_points(line: str) -> str:
    for pattern, replacement in EMPHASIS_PATTERNS:
        line = re.sub(pattern, replacement, line)

    for concept in KEY_CONCEPTS:
        if concept in line:
            idx = line.index(concept)
            if idx > 0 and line[idx - 1] != ' ':
                line = line[:idx] + ' ' + line[idx:]

    for kw in INVALID_KEYWORDS:
        if len(kw) <= 5:
            line = re.sub(r'\b' + re.escape(kw) + r'\b', '', line)

    return line


def format_text(text: str) -> str:
    """清洗并格式化 OCR 原始文本。"""
    text = text.replace('\r\n', '\n')

    cleaned_lines = []
    for line in text.split('\n'):
        line = line.strip().replace('\u3000', ' ')
        if _is_invalid_line(line):
            continue
        cleaned_lines.append(_emphasize_key_points(line))

    if not cleaned_lines:
        return ""

    result = []
    for line in cleaned_lines:
        if not line:
            continue
        if re.match(r'^\d+[.．、)]\s*$', line):
            continue
        if re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*$', line):
            continue
        if line.startswith('◆'):
            parts = re.split(r'(◆)', line)
            for part in parts:
                if part == '◆':
                    if result and result[-1] != '':
                        result.append('')
                    result.append('◆')
                elif part.strip():
                    result.append(f"  {part.strip()}")
            result.append('')
            continue
        if _is_heading(line):
            if result and result[-1] != '':
                result.append('')
            result.append(line)
            result.append('')
            continue
        if re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', line):
            result.append(f"  {line}")
            continue
        if re.match(r'^\d+[.．、)]\s+', line):
            result.append(f"  {line}")
            continue
        result.append(line)

    if result and result[-1] == '':
        result.pop()

    formatted = '\n'.join(result)
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    formatted = re.sub(r'^\s*list\s*$', '', formatted, flags=re.MULTILINE)
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    formatted = re.sub(r'\s{2,}', ' ', formatted)

    lines = formatted.split('\n')
    unique_lines = []
    seen = set()
    for line in lines:
        if line.strip() and line.strip() not in seen:
            seen.add(line.strip())
            unique_lines.append(line)

    formatted = '\n'.join(unique_lines)
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)

    return formatted.strip()


def classify_subject(text: str) -> Tuple[Optional[str], float]:
    if not text:
        return None, 0.0

    text_lower = text.lower()
    scores = {}
    for subject, keywords in SUBJECT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw.lower() in text_lower)
        if hits > 0:
            scores[subject] = hits

    if not scores:
        return None, 0.0

    best_subject = max(scores, key=scores.get)
    total_hits = sum(scores.values())
    return best_subject, scores[best_subject] / total_hits


def detect_knowledge_point(text: str, subject: Optional[str]) -> Optional[str]:
    if not text:
        return None

    text_lower = text.lower()

    if subject and subject in KNOWLEDGE_POINTS:
        search_dict = KNOWLEDGE_POINTS[subject]
    else:
        search_dict = {}
        for sub_points in KNOWLEDGE_POINTS.values():
            search_dict.update(sub_points)

    best_point = None
    best_hits = 0
    for point, keywords in search_dict.items():
        hits = sum(1 for kw in keywords if kw.lower() in text_lower)
        if hits > best_hits:
            best_hits = hits
            best_point = point

    return best_point