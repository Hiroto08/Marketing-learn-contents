{
  "case_no": "01", "subject": "コメダ珈琲", "watermark": "KOMEDA",
  "accent": "#E0884A", "glow": "rgba(224,136,74,.28)", "accent_name": "copper",
  "title": "コメダ珈琲は、なぜ長居されても儲かる？【ビジネスモデル】",
  "chapters": ["謎", "証拠", "種明かし", "あなたの店"],
  "slides": [
    # ── S1 表紙（録画は最初のフレームから全表示） ──
    {"chapter": None, "body": "cover",
     "html": """
    <div class="se cf-badge" id="s1-badge">CASE FILE 01</div>
    <div class="se cf-title t-lg" id="s1-head">コメダ珈琲は、<br>なぜ<span class="a">長居</span>されても儲かる？</div>
    <div class="se t-md" id="s1-ans" style="margin-top:.5em;"><span class="cf-ans">国内売上の約75%は、加盟店から</span></div>
    <div class="se cf-series" id="s1-series" style="margin-top:.7em;">売れる仕組みの裏側</div>
""",
     "steps": [["s1-badge", "rv-fade"], ["s1-head", "rv-up"], ["s1-ans", "rv-pop"], ["s1-series", "rv-fade"]]},

    # ── S2 謎 ──
    {"chapter": 0,
     "html": """
    <div class="se cf-kick" id="s2-kick">THE MYSTERY</div>
    <div class="se cf-title t-xl" id="s2-title">長居を歓迎する<br>仕掛けだらけの店</div>
    <div class="cf-row" style="margin-top:.3em;">
      <div class="se cf-paper" id="s2-quote" style="flex:1.25;">
        <div class="lbl">会社が自分の商売を呼ぶ言葉</div>
        <div class="txt" style="font-family:var(--serif);font-size:3.1cqw;margin-top:.2em;">「時間消費型の<br>ビジネス」</div>
        <div class="cf-src">出典：コメダHD 有価証券報告書（2026年2月期）</div>
      </div>
      <div style="display:flex;flex-direction:column;gap:.45em;justify-content:center;">
        <div class="se cf-col" id="s2-c1"><div class="nm" style="font-size:2.3cqw;margin:0;">ソファ席</div></div>
        <div class="se cf-col" id="s2-c2"><div class="nm" style="font-size:2.3cqw;margin:0;">新聞・雑誌を多数</div></div>
        <div class="se cf-col" id="s2-c3"><div class="nm" style="font-size:2.3cqw;margin:0;">朝はトースト無料</div></div>
      </div>
    </div>
    <div class="se t-md" id="s2-plan" style="margin-top:.35em;color:var(--muted2);"><span class="a">3つの証拠</span>で解く → <span class="k">あなたの商売</span>に当てはめる</div>
""",
     "steps": [["s2-title", "rv-fade"], ["s2-quote", "rv-up"], ["s2-c1", "rv-left"], ["s2-c2", "rv-left"],
               ["s2-c3", "rv-left"], ["s2-plan", "rv-up"]]},

    # ── S3 証拠① お金の入り口 ──
    {"chapter": 1,
     "html": """
    <div class="se cf-kick" id="s3-kick">EVIDENCE 01 ｜ お金の入り口</div>
    <div class="se cf-title t-xl" id="s3-title">売上の4分の3は<br>「<span class="a">卸売</span>」だった</div>
    <div class="se cf-paper" id="s3-card" style="margin-top:.2em;">
      <div class="lbl">国内事業の売上 約514億円のうち、卸売 約385億円</div>
      <div class="big"><span class="a">75</span><small>%</small></div>
      <div class="cf-bar"><div class="se cf-seg main" id="s3-bar" style="width:74.9%;">卸売（加盟店へのコーヒー豆・パン等）</div><div class="cf-seg rest" style="width:25.1%;">直営店ほか</div></div>
      <div class="cf-src">出典：コメダHD 有価証券報告書（2026年2月期）注記22「収益の分解」 国内事業 卸売38,490百万円／合計51,374百万円</div>
      <div class="se cf-stamp" id="s3-stamp">有報で確認</div>
    </div>
    <div class="se t-md" id="s3-key" style="text-align:center;margin-top:.3em;">お客さんのコーヒー代ではなく、<span class="k">お店の仕入れ代</span></div>
""",
     "steps": [["s3-title", "rv-fade"], ["s3-card", "rv-up"], ["s3-bar", "rv-grow"], ["s3-stamp", "rv-stamp"],
               ["s3-key", "rv-up"]]},

    # ── S4 証拠② 店の持ち主 ──
    {"chapter": 1,
     "html": """
    <div class="se cf-kick" id="s4-kick">EVIDENCE 02 ｜ 店の持ち主</div>
    <div class="se cf-title t-xl" id="s4-title">1030店のうち<br>直営は<span class="a">22店</span>だけ</div>
    <div class="se cf-paper r" id="s4-card" style="margin-top:.2em;">
      <div class="lbl">国内のコメダ珈琲店（2026年2月末）</div>
      <div class="cf-bar" style="height:4.4cqw;"><div class="se cf-seg main" id="s4-bar" style="width:97.9%;">加盟店 1,008店（地元のオーナーが経営）</div><div class="cf-seg rest" style="width:2.1%;padding:0;background:#3B3A37;"></div></div>
      <div class="cf-legend"><span>加盟店 97.9%</span><span>直営 22店 ＝ 2.1% →</span></div>
      <div class="cf-src">出典：コメダHD 有価証券報告書（2026年2月期）国内ブランド別店舗数</div>
    </div>
    <div class="cf-row" style="margin-top:.35em;">
      <div class="se t-md" id="s4-r1" style="text-align:center;">店員を雇うのは<span class="a">オーナー</span></div>
      <div class="se t-md" id="s4-r2" style="text-align:center;">本部の投資は<span class="k">小さく済む</span></div>
    </div>
""",
     "steps": [["s4-title", "rv-fade"], ["s4-card", "rv-up"], ["s4-bar", "rv-grow"], ["s4-r1", "rv-up"],
               ["s4-r2", "rv-up"]]},

    # ── S5 証拠③ 使用料 ──
    {"chapter": 1,
     "html": """
    <div class="se cf-kick" id="s5-kick">EVIDENCE 03 ｜ 使用料の決め方</div>
    <div class="se cf-title t-xl" id="s5-title">使用料は<br>「<span class="a">席数×定額</span>」</div>
    <div class="cf-row" style="margin-top:.3em;">
      <div class="se cf-col" id="s5-a"><div class="hd">よく知られる決め方</div><div class="nm">売上の◯%</div>
        <ul><li>売上が増えると使用料も増える</li></ul></div>
      <div class="se cf-col win" id="s5-b"><div class="hd">コメダ</div><div class="nm">席の数に比例した定額</div>
        <ul><li>売上が増えても変わらない</li></ul></div>
    </div>
    <div class="se cf-ask t-md" id="s5-ask" style="margin-top:.5em;"><i>?</i>本部と加盟店、それぞれ何を一番望む？</div>
""",
     "steps": [["s5-title", "rv-fade"], ["s5-a", "rv-right"], ["s5-b", "rv-left"], ["s5-ask", "rv-pop"]]},

    # ── S6 種明かし：お金の流れ ──
    {"chapter": 2,
     "html": """
    <div class="se cf-kick" id="s6-kick">THE TRICK</div>
    <div class="se cf-title t-xl" id="s6-title">稼ぐのは「回転」<br>ではなく「<span class="k">回数</span>」</div>
    <div class="cf-flow" style="margin-top:.4em;">
      <div class="se cf-node" id="s6-n1"><div class="nm">お客さん</div><div class="ds">何度も来る</div></div>
      <div class="se cf-arrow" id="s6-a1"><div class="lb">コーヒー代</div><div class="ln"></div><div class="lb2">来るたびに</div></div>
      <div class="se cf-node" id="s6-n2"><div class="nm">加盟店</div><div class="ds">売上が増えるほど<br>収入が増える</div></div>
      <div class="se cf-arrow" id="s6-a2"><div class="lb">豆・パンの仕入れ<br>＋定額の使用料</div><div class="ln"></div><div class="lb2">減った分が次の卸売</div></div>
      <div class="se cf-node hq" id="s6-n3"><div class="nm">本部</div><div class="ds">卸売で稼ぐ</div></div>
    </div>
    <div class="se hl-banner" id="s6-ban" style="margin-top:.6em;">長居はコストではなく、<span class="k">また来る理由</span>への投資</div>
""",
     "steps": [["s6-title", "rv-fade"], ["s6-n1", "rv-pop"], ["s6-a1", "rv-draw"], ["s6-n2", "rv-pop"],
               ["s6-a2", "rv-draw"], ["s6-n3", "rv-pop"], ["s6-ban", "rv-up"]]},

    # ── S7 種明かし：店の側 ──
    {"chapter": 2,
     "html": """
    <div class="se cf-kick" id="s7-kick">THE TRICK ｜ 店の側</div>
    <div class="se cf-title t-xl" id="s7-title">席を回さなくても<br>利益が<span class="a">残る設計</span></div>
    <div class="cf-row" style="margin-top:.35em;">
      <div class="se cf-paper" id="s7-c1"><div class="lbl">立地</div><div class="txt">郊外の住宅街<br>地代・家賃が低め<br>広い駐車場</div></div>
      <div class="se cf-paper r" id="s7-c2"><div class="lbl">メニュー</div><div class="txt">定番が中心<br>食材を共通で使う</div></div>
      <div class="se cf-paper" id="s7-c3"><div class="lbl">作業</div><div class="txt">店の作業を軽く<br>人件費を抑えやすい</div></div>
    </div>
    <div class="se t-sm" id="s7-city" style="text-align:center;margin-top:.2em;">都心では 駅前の1階でなく<span class="a">駅近ビルの2階</span>などで家賃を抑える</div>
    <div class="se t-md" id="s7-key" style="text-align:center;margin-top:.2em;">営業利益 約94億円＝売上の<span class="k">約16%</span>が残る</div>
    <div class="se cf-src dark" id="s7-src" style="text-align:center;">出典：コメダHD 有価証券報告書（2026年2月期）「事業の内容」「経営成績」 営業利益9,424百万円／売上収益57,225百万円</div>
""",
     "steps": [["s7-title", "rv-fade"], ["s7-c1", "rv-up"], ["s7-c2", "rv-up"], ["s7-c3", "rv-up"], ["s7-city", "rv-fade"], ["s7-key", "rv-up"], ["s7-src", "rv-fade"]]},

    # ── S8 型 ──
    {"chapter": 2,
     "html": """
    <div class="se cf-kick" id="s8-kick">THE PATTERN</div>
    <div class="se cf-title t-xl" id="s8-title">稼ぎ方を決めると<br><span class="k">我慢</span>が決まる</div>
    <div class="cf-row" style="margin-top:.3em;">
      <div class="se cf-col" id="s8-a"><div class="hd">TYPE A</div><div class="nm">回転型</div>
        <ul><li>1回の来店で回す</li><li>長居＝損</li></ul></div>
      <div class="se cf-col win" id="s8-b"><div class="hd">TYPE B</div><div class="nm">来店頻度型</div>
        <ul><li>同じ客が何回来るか</li><li>長居＝また来る理由</li></ul>
        <div class="se t-sm" id="s8-ltv" style="margin-top:.4em;color:var(--accent);">＝ <b>LTV</b>（長い付き合いの売上）を伸ばす</div></div>
    </div>
    <div class="se t-sm" id="s8-note" style="text-align:center;margin-top:.25em;">どちらが正しい、という話ではない</div>
    <div class="se t-md" id="s8-key" style="text-align:center;margin-top:.15em;">コメダは頻度型。だから長居を<span class="k">歓迎できる</span></div>
""",
     "steps": [["s8-title", "rv-fade"], ["s8-a", "rv-right"], ["s8-b", "rv-left"], ["s8-ltv", "rv-fade"], ["s8-note", "rv-fade"], ["s8-key", "rv-up"]]},

    # ── S9 あなたの店 ──
    {"chapter": 3,
     "html": """
    <div class="se cf-kick" id="s9-kick">YOUR CASE</div>
    <div class="se cf-title t-xl" id="s9-title">あなたの商売は<br><span class="k">どちら側</span>？</div>
    <div class="cf-row" style="margin-top:.3em;">
      <div class="se cf-col" id="s9-a"><div class="hd">例：美容室</div><div class="nm" style="font-size:2.6cqw;">1回の単価より<br><span class="a">次の予約</span></div></div>
      <div class="se cf-col" id="s9-b"><div class="hd">例：学習塾</div><div class="nm" style="font-size:2.6cqw;">入会の数より<br><span class="a">続く年数</span></div></div>
    </div>
    <div class="se cf-ask t-md" id="s9-ask" style="margin-top:.5em;"><i>?</i>長くいるほど、得をする？損をする？</div>
""",
     "steps": [["s9-title", "rv-fade"], ["s9-a", "rv-up"], ["s9-b", "rv-up"], ["s9-ask", "rv-pop"]]},

    # ── S10 明日やる1つ ──
    {"chapter": 3,
     "html": """
    <div class="se cf-kick" id="s10-kick">TOMORROW ｜ 明日やる1つ</div>
    <div class="se cf-memo" id="s10-memo" style="margin-top:.2em;">
      <div class="se ln" id="s10-l1">① 売上の入り口を<b>3つ</b>書き出す</div>
      <div class="se ln" id="s10-l2">② 横に「何に比例？」 人数／<b>回数</b>／金額</div>
      <div class="se ln" id="s10-l3">③ 一番大きい入り口に<b>丸</b>をつける</div>
    </div>
    <div class="se t-md" id="s10-key" style="text-align:center;margin-top:.45em;">回数なら、<span class="k">急がせる仕組み</span>を見直す</div>
""",
     "steps": [["s10-memo", "rv-fade"], ["s10-l1", "rv-draw"], ["s10-l2", "rv-draw"], ["s10-l3", "rv-draw"],
               ["s10-key", "rv-up"]]},

    # ── S11 次の問い（下半分はエンドスクリーン用に空ける） ──
    {"chapter": 3, "body": "center",
     "html": """
    <div style="display:flex;flex-direction:column;align-items:center;gap:.5em;margin-bottom:18%;">
      <div class="se cf-kick" id="s11-kick">NEXT CASE</div>
      <div class="se cf-title t-lg" id="s11-q">インクより安いプリンター本体。<br>本当に<span class="k">損をしている</span>？</div>
      <div class="se t-md" id="s11-ltv" style="color:var(--muted2);">回数で稼ぐ考え方は 教科書「<span class="a">CPAとLTV</span>」の回で</div>
    </div>
""",
     "steps": [["s11-kick", "rv-fade"], ["s11-q", "rv-up"], ["s11-ltv", "rv-fade"]]},
  ],
}
