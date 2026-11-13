#!/usr/bin/env python3
"""映像意図（visual_plan.json）→ 画面に差し込む図・写真の HTML（表現コード v1 §8）。

型の一覧は TYPES（下）。どの型をいつ使うかは `.claude/skills/yt-expression/SKILL.md` の表が正。
同期（sync）：その要素（テロップ）が出た瞬間に、図の変化を始める（CSS の :has() で、実際の表示に連動）。
色は表現コードの色だけ（白・補足・数字の黄・シリーズの色）。**台本に無い数字・文字は描かない**（check_visual_plan.py が検査）。
"""
import html as _h


def _wrap(sid, inner, cls=''):
    return f'<div class="ex-vis {cls}" data-vis="{sid}">{inner}</div>'


def photo(sid, p):
    stamp = (f'<span class="ex-stamp">{_h.escape(p["stamp"])}</span>' if p.get('stamp') else '')
    return _wrap(sid, f'<div class="ex-photo" style="background-image:url({p["file"]});'
                      f'background-position:{p.get("focus", "50% 50%")}"></div><div class="ex-photo-tint"></div>{stamp}', 'ex-vis-photo')


def chart_drop(sid, p):
    """value % 減った（direction=up なら増えた）。左＝前、右＝後"""
    v = float(p['value'])
    up = p.get('direction') == 'up'
    after = (100 + v) if up else (100 - v)
    hi = max(100.0, after)
    reset = ' ex-reset' if p.get('reset') else ''
    sign = '+' if up else '−'
    return _wrap(sid, f'''<div class="ex-chart{reset}" style="--before:{100/hi:.3f};--after:{after/hi:.3f}">
  <div class="ex-col"><div class="ex-bar ex-bar-a"></div><div class="ex-cap">{_h.escape(p.get("before_label", "前"))}</div></div>
  <div class="ex-col"><div class="ex-bar ex-bar-b"></div><div class="ex-cap">{_h.escape(p.get("after_label", "後"))}</div></div>
  <div class="ex-delta">{sign}{v:g}%</div></div>''', 'ex-vis-chart')


def compare_bars(sid, p):
    """同じ単位の2つの数字を、棒の長さで比べる。a・b は数値、a_text・b_text は画面に出す表記（台本の表記）"""
    a, b = float(p['a']), float(p['b'])
    m = max(a, b)
    return _wrap(sid, f'''<div class="ex-cmp">
  <div class="ex-row"><div class="ex-cap">{_h.escape(p["a_label"])}</div><div class="ex-hbar ex-hbar-a" style="--w:{a/m:.3f}"></div><div class="ex-val">{_h.escape(p["a_text"])}</div></div>
  <div class="ex-row"><div class="ex-cap">{_h.escape(p["b_label"])}</div><div class="ex-hbar ex-hbar-b" style="--w:{b/m:.3f}"></div><div class="ex-val">{_h.escape(p["b_text"])}</div></div></div>''', 'ex-vis-cmp')


def dot_grid(sid, p):
    """n 個の点（回数・件数。n は 1000 まで）。strike=false なら線で消さない"""
    n = int(p['n'])
    cols = int(p.get('cols') or max(8, min(37, round((n * 2.3) ** 0.5))))
    rows = (n + cols - 1) // cols
    step, r = 28, 9
    dots = ''.join(f'<circle cx="{(i % cols) * step + 14}" cy="{(i // cols) * step + 14}" r="{r}" '
                   f'style="animation-delay:{(i // cols) * 0.05:.2f}s"/>' for i in range(n))
    w, h = cols * step, rows * step
    strike = '' if p.get('strike') is False else f'<line class="ex-strike" x1="0" y1="{h}" x2="{w}" y2="0" pathLength="1"/>'
    cls = 'ex-dots' + ('' if strike else ' ex-nostrike')
    return _wrap(sid, f'<svg class="{cls}" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet">'
                      f'<g class="ex-dots-g">{dots}</g>{strike}</svg>', 'ex-vis-dots')


def tag_strike(sid, p):
    return _wrap(sid, '''<svg class="ex-tag" viewBox="0 0 600 360">
  <g class="ex-tag-a"><path d="M40 60h220l70 120-70 120H40z"/><circle cx="268" cy="180" r="14" class="ex-hole"/>
    <rect x="70" y="150" width="140" height="22" rx="6" class="ex-price"/><line x1="60" y1="161" x2="222" y2="161" class="ex-cut" pathLength="1"/></g>
  <g class="ex-tag-b"><path d="M330 60h180l60 120-60 120H330z"/>
    <rect x="356" y="150" width="110" height="26" rx="6" class="ex-price2"/></g></svg>''', 'ex-vis-tag')


def timeline(sid, p):
    """年の位置を線の上に示す。year は台本にある西暦"""
    return _wrap(sid, f'''<div class="ex-tl"><div class="ex-tl-line"></div><div class="ex-tl-fill"></div>
  <div class="ex-tl-dot"></div><div class="ex-tl-year">{_h.escape(str(p["year"]))}</div></div>''', 'ex-vis-tl')


def question(sid, p):
    return _wrap(sid, '''<svg class="ex-sym" viewBox="0 0 300 300"><path class="ex-sym-q" pathLength="1"
  d="M95 105c0-38 26-62 58-62 34 0 58 22 58 54 0 44-56 46-56 96"/><circle class="ex-sym-dot" cx="155" cy="248" r="13"/></svg>''', 'ex-vis-sym')


def check(sid, p):
    return _wrap(sid, '''<svg class="ex-sym" viewBox="0 0 300 300"><circle class="ex-sym-ring" cx="150" cy="150" r="104" pathLength="1"/>
  <path class="ex-sym-c" pathLength="1" d="M98 152l38 38 70-78"/></svg>''', 'ex-vis-sym')


def quote(sid, p):
    return _wrap(sid, '''<svg class="ex-sym ex-sym-quote" viewBox="0 0 600 300">
  <path class="ex-q1" d="M70 60h110v60h-50v120" /><path class="ex-q2" d="M530 240H420v-60h50V60" /></svg>''', 'ex-vis-sym')


def none(sid, p):
    return ''


# 型 → (生成関数, 自作か, Shorts で使えるか, 長尺で使えるか)
TYPES = {
    'photo':        (photo, False, True, True),
    'chart_drop':   (chart_drop, True, True, False),
    'compare_bars': (compare_bars, True, True, False),
    'dot_grid':     (dot_grid, True, True, True),
    'tag_strike':   (tag_strike, True, True, False),
    'timeline':     (timeline, True, True, False),
    'question':     (question, True, True, False),
    'check':        (check, True, True, False),
    'quote':        (quote, True, True, False),
    'bar_cells':    (none, True, False, True),      # 長尺：既にある数字のカード（.jcell）の下に棒を足す
    'none':         (none, True, False, True),      # 長尺だけ：その1枚には絵を足さない（理由を intent に書く）
}


def render(sid, p):
    return TYPES[p['type']][0](sid, p)


def sync_css(sid, p):
    """テロップの要素が出た瞬間（rv-* が付いた瞬間）に、図の変化を始める規則。"""
    s = p.get('sync')
    if not s:   # 同期する要素が無い（1枚目など）：スライドが出た時点から動かす。録画の頭出し 0.3秒ぶんを待つ
        return f'#{sid} .ex-vis,#{sid} .ex-bg,#{sid} .jmini{{--go:running;--d0:.45s}}\n'
    return (f'#{sid}:has(#{s}[class*="rv-"]) .ex-vis,#{sid}:has(#{s}[class*="rv-"]) .ex-bg,'
            f'#{sid}:has(#{s}[class*="rv-"]) .jmini{{--go:running}}\n')
