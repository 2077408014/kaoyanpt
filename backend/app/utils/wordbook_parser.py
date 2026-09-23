import re
from typing import List, Dict


POS_MARKERS = ['n.', 'v.', 'adj.', 'adv.', 'prep.', 'conj.', 'pron.', 'art.', 'num.', 'vt.', 'vi.', 'aux.', 'abbr.', 'interj.', 'det.', 'modal.', 'particle.']

PHONETIC_CHARS = set('æɪɔːʊəʃθðŋɜːʌɑːɒɛːɔɪəʊˈˌˑʼʽˀʾʿ˴ːˌ:')
# 移除 ASCII j, u（来自 juː 的误入），它们是普通字母不是音标


def parse_wordbook_text(text: str) -> List[Dict]:
    """从词书文本中提取单词列表。

    支持多行格式（每行一个字段）：
    plastic
    'plæstik
    adj.可塑料的 可塑的 n.塑料
    """
    if not text:
        return []

    lines = text.split('\n')
    # 过滤空行和表头
    filtered = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if _is_header_line(line):
            continue
        # 跳过纯页码数字
        if line.isdigit() and len(line) <= 5:
            continue
        filtered.append(line)

    words = []
    seen = set()
    i = 0

    while i < len(filtered):
        line = filtered[i]

        # 尝试提取单词
        word = _try_extract_word(line)
        if not word:
            i += 1
            continue

        j = i + 1

        # 检查断行单词（如 recommendati + on）
        if j < len(filtered):
            next_line = filtered[j]
            if _is_all_english(next_line) and not _is_phonetic_line(next_line):
                if j + 1 < len(filtered) and _is_phonetic_line(filtered[j + 1]):
                    word += next_line
                    j += 1

        # 收集音标（取下一行，如果不是中文/POS开头）
        phonetic_parts = []
        if j < len(filtered):
            line_j = filtered[j]
            if not _has_chinese(line_j) and not _starts_with_pos(line_j):
                phonetic_parts.append(line_j)
                j += 1
                # 检查多行音标（下一行也有音标字符）
                while j < len(filtered):
                    next_j = filtered[j]
                    if _is_phonetic_line(next_j) and not _has_chinese(next_j) and not _starts_with_pos(next_j):
                        phonetic_parts.append(next_j)
                        j += 1
                    else:
                        break

        # 收集释义（直到遇到下一个单词行）
        meaning_parts = []
        while j < len(filtered):
            line_j = filtered[j]
            if _is_new_word_line(line_j):
                break
            meaning_parts.append(line_j)
            j += 1
            if len(meaning_parts) >= 10:
                break  # 安全限制

        phonetic_raw = ' '.join(phonetic_parts).strip()
        meaning = ' '.join(meaning_parts).strip()

        if word and meaning:
            key = word.lower()
            if key not in seen:
                seen.add(key)
                if phonetic_raw and not phonetic_raw.startswith('/'):
                    phonetic_raw = f'/{phonetic_raw}/'
                words.append({
                    'word': word,
                    'phonetic': phonetic_raw,
                    'meaning': meaning,
                    'example_sentence': ''
                })

        i = j if j > i else i + 1

    return words


def _is_header_line(line: str) -> bool:
    """检查是否为表头行。"""
    header_keywords = ['序号', '单词', '注音', '音标', '释义', '英文', '中文']
    for kw in header_keywords:
        if kw in line:
            return True
    return False


def _has_chinese(text: str) -> bool:
    return any('\u4e00' <= c <= '\u9fff' for c in text)


def _has_phonetic_chars(text: str) -> bool:
    count = sum(1 for ch in text if ch in PHONETIC_CHARS)
    return count > 0


def _is_phonetic_line(line: str) -> bool:
    """判断是否为音标行。"""
    if _has_phonetic_chars(line):
        return True
    stripped = line.strip()
    if stripped.startswith("'") and not _has_chinese(stripped):
        return True
    if stripped.startswith('.') and not _has_chinese(stripped) and len(stripped) > 2:
        return True
    return False


def _starts_with_pos(text: str) -> bool:
    """判断是否以词性标记开头。"""
    text_lower = text.lower().strip()
    for marker in POS_MARKERS:
        if text_lower.startswith(marker):
            return True
    return False


def _is_all_english(text: str) -> bool:
    """判断是否纯英文字母（无中文、无音标、无数字、无空格）。"""
    if not text or len(text) > 20:
        return False
    if _has_chinese(text):
        return False
    if _has_phonetic_chars(text):
        return False
    return all(c.isalpha() for c in text)


def _try_extract_word(line: str) -> str:
    """尝试从行中提取单词。"""
    cleaned = line.strip()
    if not cleaned:
        return None

    # 移除开头的数字序号（如 "100 affair" → "affair"）
    match = re.match(r'^(\d+)[\s\.]+([a-zA-Z].*)', cleaned)
    if match:
        cleaned = match.group(2)

    if not cleaned or not cleaned[0].isalpha():
        return None

    # 包含中文 → 不是单词行
    if _has_chinese(cleaned):
        return None

    # 包含音标字符 → 不是单词行
    if _has_phonetic_chars(cleaned):
        return None

    # 以撇号或点开头 → 是音标行
    if cleaned.startswith("'") or cleaned.startswith('.'):
        return None

    # 以词性标记开头 → 是释义行
    if _starts_with_pos(cleaned):
        return None

    # 提取第一个词
    parts = cleaned.split()
    word = parts[0]

    # 清理单词
    word = re.sub(r'[^\w\-\'\.]', '', word)

    if len(word) >= 2:
        return word

    return None


def _is_new_word_line(line: str) -> bool:
    """判断是否为新单词行（用于在释义收集中检测下一个单词）。"""
    word = _try_extract_word(line)
    return word is not None
