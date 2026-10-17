# アフィリエイト・ブロック（L2収益）

各EPの概要欄／note末尾に貼る、参考書籍・AIツールのアフィリエイトリンク素材。

## 真実源（Single Source of Truth）

| 項目 | 値 |
|---|---|
| Amazonアソシエイト トラッキングID | **`aicreateslife-22`** |

- 上記IDが唯一の真実源。`epNN_*.md` 内の `?tag=` は全てこの値に一致していなければならない。
- 生成は `_tools/repurpose/make_affiliate.py`。タグは環境変数 `AMAZON_ASSOC_TAG` で注入する（未設定時は `REPLACE-TAG-22` プレースホルダ）。

## 再生成

```bash
# 全EP再生成（タグを反映）
AMAZON_ASSOC_TAG=aicreateslife-22 python3 _tools/repurpose/make_affiliate.py --all

# 単一EP
AMAZON_ASSOC_TAG=aicreateslife-22 python3 _tools/repurpose/make_affiliate.py 06_...
```

## 検査（貼る前に必ず）

```bash
# プレースホルダが残っていないこと（0であること）
grep -rl "REPLACE-TAG-22" _deliverables/affiliate/*.md | wc -l

# 実タグ以外のtagが混ざっていないこと（出力が空であること）
grep -rhoE "tag=[a-zA-Z0-9-]+" _deliverables/affiliate/*.md | grep -v "tag=aicreateslife-22"
```

## 注意

- AIツールのASP案件（書籍以外）は自動生成されない。各 `epNN_*.md` に手動追記する。
- 書籍リンクは各EPの `script.md` 参考文献から自動抽出される。
