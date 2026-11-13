#!/usr/bin/env python3
"""その回を、表現コード v1 で作るか・現行の表現で作るかを決める（run_shorts.sh／run_episode.sh が呼ぶ）。

  python3 _tools/expression/expr_gate.py <回のフォルダ> [--short shortN]
    出力：v1 ／ current（標準出力の1語）。決められないときは終了コード 1（理由を標準エラーに出す）。

決まり（社長決裁 2026-11-13）：
  - 本適用は series.json の expression.apply_from（2026-12-06 の週の制作バッチ）から。
    Shorts は同週のバッチから、長尺は次のケースファイル c03 から。
  - それより前の日は、visual_plan.json があっても現行の表現で作る（試作だけは EXPR_FORCE=1 で v1）。
  - 適用日以降：visual_plan.json がある回は v1。無い回は、旧表現の回（expr_legacy.txt）なら現行、そうでなければ不合格。
"""
import datetime
import fnmatch
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))


def plan_path(ep, short=None):
    return os.path.join(ep, 'shorts_build', short, 'visual_plan.json') if short else os.path.join(ep, 'visual_plan.json')


def decide(ep, short=None, today=None):
    cfg = json.load(open(os.path.join(ROOT, 'series.json'), encoding='utf-8')).get('expression') or {}
    start = datetime.date.fromisoformat(cfg.get('apply_from', '9999-12-31'))
    today = today or datetime.date.fromisoformat(os.environ.get('EXPR_TODAY', datetime.date.today().isoformat()))
    has = os.path.exists(plan_path(ep, short))
    if os.environ.get('EXPR_FORCE') == '1':
        return ('v1', '試作（EXPR_FORCE=1）') if has else (None, 'EXPR_FORCE=1 だが visual_plan.json が無い')
    if today < start:
        return 'current', f'本適用（{start}）より前なので現行の表現'
    if has:
        return 'v1', 'visual_plan.json あり'
    name = os.path.basename(os.path.normpath(ep))
    pats = [l.split('#')[0].strip() for l in open(os.path.join(HERE, 'expr_legacy.txt'), encoding='utf-8')]
    if any(p and fnmatch.fnmatch(name, p) for p in pats):
        return 'current', '旧表現の回（expr_legacy.txt）'
    return None, (f'{plan_path(ep, short)} が無い。本適用（{start}）以降に作る回は、映像意図が必須。'
                  '`.claude/skills/yt-expression/SKILL.md` の手順で作る')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    short = sys.argv[sys.argv.index('--short') + 1] if '--short' in sys.argv else None
    if short in args:
        args.remove(short)
    mode, why = decide(args[0].rstrip('/'), short)
    print(f'[expr_gate] {why}', file=sys.stderr)
    if mode is None:
        return 1
    print(mode)
    return 0


if __name__ == '__main__':
    sys.exit(main())
