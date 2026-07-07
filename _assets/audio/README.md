# 音声アセット（BGM・効果音）

すべて `_tools/audio/synth_assets.py` によるプログラム合成で生成した自作素材。
第三者の録音・楽曲を一切含まないため外部の著作権は存在しない（CC0相当として扱ってよい）。
再生成: `python3 _tools/audio/synth_assets.py`

| ファイル | 用途 | 規定音量(mix時) |
|---------|------|----------------|
| bgm_calm_loop.wav | 全編BGM（76bpm・Fmaj7-Am7-Dm7-Cmaj7のループ、ループ耐性処理済み） | -21dB |
| sfx_whoosh.wav | スライド切替 | -16dB |
| sfx_pop.wav | 要素出現（rv-pop/rv-scale） | -18dB |
| sfx_ding.wav | 重要数字の出現（S1アンカー等） | -16dB |

ミックス仕様は `.claude/skills/episode-production/audio-production.md` を参照。
