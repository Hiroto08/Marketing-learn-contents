#!/usr/bin/env python3
"""試作の比較動画を、レビュー便（Drive）へ送る。YouTube にはアップロードしない。
  python3 _prototypes/expr_v1/send_review.py
"""
import glob
import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, '_tools', 'publish'))
import upload_review_drive as U  # noqa: E402

out = {}
tok = U.access_token()
for f in sorted(glob.glob(os.path.join(ROOT, '_prototypes/expr_v1/compare/*.mp4'))):
    name = '【試作・非公開】表現v1_' + os.path.basename(f)
    fid = U.upload(tok, f, name)
    out[name] = f'https://drive.google.com/file/d/{fid}/view'
    print(name, out[name])
json.dump(out, open(os.path.join(ROOT, '_prototypes/expr_v1/review_links.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
