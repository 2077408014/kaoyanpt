"""LaTeX 公式规范化工具。

用于修复 OCR / LLM 输出中常见的 LaTeX 拼写错误，
例如 \infty 被误写为 infy / infity / infinity / \Infty 等。
在 AI 输出返回前端之前统一调用，保证 KaTeX 能正确渲染。
"""
from __future__ import annotations

import re
from typing import Pattern

LATEX_CMD_REPLACEMENTS: list[tuple[str, str]] = [
    (r"\\[Ff]rac", r"\\frac"),
    (r"\\[Ss]qrt", r"\\sqrt"),
    (r"\\[Ll]im", r"\\lim"),
    (r"\\[Ss]um", r"\\sum"),
    (r"\\[Pp]rod", r"\\prod"),
    (r"\\[Ii]nt", r"\\int"),
    (r"\\[Aa]lpha", r"\\alpha"),
    (r"\\[Bb]eta", r"\\beta"),
    (r"\\[Gg]amma", r"\\gamma"),
    (r"\\[Dd]elta", r"\\delta"),
    (r"\\[Ee]psilon", r"\\varepsilon"),
    (r"\\[Tt]heta", r"\\theta"),
    (r"\\[Pp]i", r"\\pi"),
    (r"\\[Ll]ambda", r"\\lambda"),
    (r"\\[Mm]u", r"\\mu"),
    (r"\\[Ss]igma", r"\\sigma"),
    (r"\\[Oo]mega", r"\\omega"),
    (r"\\[Rr]ightarrow", r"\\rightarrow"),
    (r"\\[Ll]eftarrow", r"\\leftarrow"),
    (r"\\[Ll]eftrightarrow", r"\\leftrightarrow"),
    (r"\\[Tt]o", r"\\to"),
    (r"\\[Nn]e", r"\\neq"),
    (r"\\[Ll]eq", r"\\leq"),
    (r"\\[Gg]eq", r"\\geq"),
    (r"\\[Cc]dot", r"\\cdot"),
    (r"\\[Tt]imes", r"\\times"),
    (r"\\[Dd]iv", r"\\div"),
    (r"\\[Pp]m", r"\\pm"),
]

INFTY_FIX_PATTERNS: list[tuple[Pattern, str]] = [
    (re.compile(r"\\[Ii]nft\s*y"), r"\\infty"),
    (re.compile(r"\\inf\s*i\s*t\s*[yi]\s*"), r"\\infty"),
    (re.compile(r"(?<![A-Za-z])inf\s*i\s*t\s*y(?!\s*[A-Za-z])"), r"\\infty"),
    (re.compile(r"(?<![A-Za-z])inf\s*it\s*y(?!\s*[A-Za-z])"), r"\\infty"),
    (re.compile(r"(?<![A-Za-z])inf\s*in\s*ity(?!\s*[A-Za-z])"), r"\\infty"),
    (re.compile(r"(\\lim_\{[^}]*?)\binf\b([^}]*\})"), r"\1\\infty\2"),
    (re.compile(r"(?<![A-Za-z])inf(?![A-Za-z])"), r"\\infty"),
]

SYMBOL_FIXES: list[tuple[Pattern, str]] = [
    (re.compile(r"\\to\s*\\to"), r"\\Rightarrow"),
    (re.compile(r"(?<!\\)->"), r"\\to"),
    (re.compile(r"→"), r"\\to"),
    (re.compile(r"⇒"), r"\\Rightarrow"),
    (re.compile(r"←"), r"\\leftarrow"),
    (re.compile(r"⇐"), r"\\Leftarrow"),
    (re.compile(r"≤"), r"\\leq"),
    (re.compile(r"≥"), r"\\geq"),
    (re.compile(r"≠"), r"\\neq"),
    (re.compile(r"×"), r"\\times"),
    (re.compile(r"÷"), r"\\div"),
    (re.compile(r"±"), r"\\pm"),
    (re.compile(r"≈"), r"\\approx"),
    (re.compile(r"°"), r"^\\circ"),
    (re.compile(r"∑"), r"\\sum"),
    (re.compile(r"∏"), r"\\prod"),
    (re.compile(r"∫"), r"\\int"),
    (re.compile(r"√"), r"\\sqrt"),
    (re.compile(r"∪"), r"\\cup"),
    (re.compile(r"∩"), r"\\cap"),
    (re.compile(r"∈"), r"\\in"),
    (re.compile(r"∉"), r"\\notin"),
    (re.compile(r"∀"), r"\\forall"),
    (re.compile(r"∃"), r"\\exists"),
    (re.compile(r"∇"), r"\\nabla"),
    (re.compile(r"∂"), r"\\partial"),
    (re.compile(r"α"), r"\\alpha"),
    (re.compile(r"β"), r"\\beta"),
    (re.compile(r"γ"), r"\\gamma"),
    (re.compile(r"δ"), r"\\delta"),
    (re.compile(r"ε"), r"\\varepsilon"),
    (re.compile(r"θ"), r"\\theta"),
    (re.compile(r"π"), r"\\pi"),
    (re.compile(r"λ"), r"\\lambda"),
    (re.compile(r"μ"), r"\\mu"),
    (re.compile(r"σ"), r"\\sigma"),
    (re.compile(r"ω"), r"\\omega"),
    (re.compile(r"∞"), r"\\infty"),
]


def _apply_pairs(text: str, pairs: list[tuple[str, str]]) -> str:
    for pattern, repl in pairs:
        text = re.sub(pattern, repl, text)
    return text


def _apply_patterns(text: str, patterns: list[tuple[Pattern, str]]) -> str:
    for pattern, repl in patterns:
        text = pattern.sub(repl, text)
    return text


def normalize_latex(text: str) -> str:
    if not text:
        return text or ""

    text = _apply_pairs(text, LATEX_CMD_REPLACEMENTS)
    text = _apply_patterns(text, INFTY_FIX_PATTERNS)
    text = _apply_patterns(text, SYMBOL_FIXES)
    text = re.sub(r"(\\infty\s*){2,}", r"\\infty", text)

    return text