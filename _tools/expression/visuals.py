#!/usr/bin/env python3
"""映像意図（visual_plan.json）→ 画面に差し込む図・写真の HTML（表現コード v1 §8）。

型（type）：
  photo       実写イメージ。ライセンス台帳にある写真だけ。色調を紺の単色に寄せ、ゆっくり寄る（3%/秒以下）
  chart_drop  自社データの図解：前→後の棒。数字（value %）は台本の数字だけを使う
  dot_grid    自社データの図解：n 個の点を並べて「回数・件数」を見せ、線で消す
  tag_strike  図解：値札と取り消し線（数字は書かない）
同期（sync）：その要素（テロップ）が出た瞬間に、図の変化を始める（CSS の :has() で、実際の表示に連動）。
色は表現コードの色だけ（白・補足・数字の黄・シリーズの色）。台本に無い数字・文字は描かない。
"""
import html as _h


def _wrap(sid, inner, cls=''):
    return f'<div class="ex-vis {cls}" data-vis="{sid}">{inner}</div>'


def photo(sid, p):
    stamp = (f'<span class="ex-stamp">{_h.escape(p["stamp"])}</span>' if p.get('stamp') else '')
    return _wrap(sid, f'<div class="ex-photo" style="background-image:url({p["file"]});'
                      f'background-position:{p.get("focus", "50% 50%")}"></div><div class="ex-photo-tint"></div>{stamp}', 'ex-vis-photo')


def chart_drop(sid, p):
    v = float(p['value'])
    after = 100 - v
    reset = ' ex-reset' if p.get('reset') else ''
    return _wrap(sid, f'''<div class="ex-chart{reset}" style="--after:{after/100:.3f}">
  <div class="ex-col"><div class="ex-bar ex-bar-a"></div><div class="ex-cap">{_h.escape(p.get("before_label", "前"))}</div></div>
  <div class="ex-col"><div class="ex-bar ex-bar-b"></div><div class="ex-cap">{_h.escape(p.get("after_label", "後"))}</div></div>
  <div class="ex-delta">−{v:g}%</div></div>''', 'ex-vis-chart')


def dot_grid(sid, p):
    n, cols = int(p['n']), int(p.get('cols', 37))
    rows = (n + cols - 1) // cols
    step, r = 28, 9
    dots = ''.join(f'<circle cx="{(i % cols) * step + 14}" cy="{(i // cols) * step + 14}" r="{r}" '
                   f'style="animation-delay:{(i // cols) * 0.05:.2f}s"/>' for i in range(n))
    w, h = cols * step, rows * step
    return _wrap(sid, f'<svg class="ex-dots" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet">'
                      f'<g class="ex-dots-g">{dots}</g>'
                      f'<line class="ex-strike" x1="0" y1="{h}" x2="{w}" y2="0" pathLength="1"/></svg>', 'ex-vis-dots')


def tag_strike(sid, p):
    return _wrap(sid, '''<svg class="ex-tag" viewBox="0 0 600 360">
  <g class="ex-tag-a"><path d="M40 60h220l70 120-70 120H40z"/><circle cx="268" cy="180" r="14" class="ex-hole"/>
    <rect x="70" y="150" width="140" height="22" rx="6" class="ex-price"/><line x1="60" y1="161" x2="222" y2="161" class="ex-cut" pathLength="1"/></g>
  <g class="ex-tag-b"><path d="M330 60h180l60 120-60 120H330z" transform="translate(0,0)"/>
    <rect x="356" y="150" width="110" height="26" rx="6" class="ex-price2"/></g></svg>''', 'ex-vis-tag')


TYPES = {'photo': photo, 'chart_drop': chart_drop, 'dot_grid': dot_grid, 'tag_strike': tag_strike}


def render(sid, p):
    return TYPES[p['type']](sid, p)


def sync_css(sid, p):
    """テロップの要素が出た瞬間（rv-* が付いた瞬間）に、図の変化を始める規則。"""
    s = p.get('sync')
    if not s:   # 同期する要素が無い（1枚目など）：スライドが出た時点から動かす。録画の頭出し 0.3秒ぶんを待つ
        return f'#{sid} .ex-vis{{--go:running;--d0:.45s}}\n'
    return f'#{sid}:has(#{s}[class*="rv-"]) .ex-vis{{--go:running}}\n'
