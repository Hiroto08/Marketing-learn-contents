import os,json,urllib.request,urllib.parse,re,datetime,glob
cid=os.environ["YT_CLIENT_ID"];csec=os.environ["YT_CLIENT_SECRET"];rt=os.environ["YT_REFRESH_TOKEN"]
data=urllib.parse.urlencode({"client_id":cid,"client_secret":csec,"refresh_token":rt,"grant_type":"refresh_token"}).encode()
tok=json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token",data=data),timeout=30))["access_token"]
def api(p,q): return json.load(urllib.request.urlopen(urllib.request.Request("https://www.googleapis.com/youtube/v3/"+p+"?"+urllib.parse.urlencode(q),headers={"Authorization":"Bearer "+tok}),timeout=30))
ch=api("channels",{"part":"snippet","mine":"true"})["items"][0]["snippet"]["title"]
def load(p):
    try: return json.load(open(p,encoding="utf-8"))
    except: return {}
ROADMAP={17:"ブランド・エクイティ",18:"LTV/CRM",19:"マーケ組織",20:"グロースハック",21:"ヒット商品",22:"V字回復",23:"失敗事例",24:"未来のマーケター"}
eps=[]; allids=set()
for d in sorted(glob.glob("0*/ep*")):
    if not os.path.isdir(d): continue
    ep=int(re.search(r"ep(\d+)",d).group(1))
    mainmf=load(f"{d}/publish_manifest.json")
    main=[v.get("videoId") for v in mainmf.values()] if mainmf else []
    shorts=[]
    for sd in sorted(glob.glob(f"{d}/shorts_build/short*/publish_manifest.json")):
        for v in load(sd).values(): shorts.append(v.get("videoId"))
    has_shorts_md=os.path.exists(f"{d}/shorts.md")
    eps.append((ep,d,main,shorts,has_shorts_md))
    allids.update([x for x in main if x]); allids.update([x for x in shorts if x])
# accurate privacy via videos.list (batches of 50)
priv={}
ids=list(allids)
for i in range(0,len(ids),50):
    r=api("videos",{"part":"status","id":",".join(ids[i:i+50])})
    for it in r["items"]: priv[it["id"]]=it["status"]["privacyStatus"]
def P(v): return priv.get(v,"削除")
now=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
o=[f"# アップロード状況（{ch}）\n\n",
   f"> 自動生成：{now} ／ ソース＝各話 publish_manifest.json の videoId を YouTube videos.list で実照会\n",
   "> ブランチにコミット済み。他セッションはこのファイルで最新の到達点を確認できる。\n\n",
   "凡例：public=公開済 / private=非公開（公開待ち） / 削除=YouTubeに無い / 未UP=未アップロード / —=対象物なし\n\n",
   "| EP | タイトル領域 | 本編 | 本編状態 | Shorts | Shorts状態 |\n|----|----|----|----|----|----|\n"]
for ep,d,main,shorts,hsm in eps:
    mv=main[0] if main else None
    mp=P(mv) if mv else "未UP"
    svs=" ".join(f"`{x}`" for x in shorts) if shorts else ("未UP" if hsm else "—")
    sp=("／".join(sorted(set(P(x) for x in shorts)))) if shorts else ("未UP" if hsm else "—")
    o.append(f"| EP{ep:02d} | `{os.path.basename(d)}` | {('`'+mv+'`') if mv else '—'} | {mp} | {svs} | {sp} |\n")
pub=sum(1 for v in priv.values() if v=='public'); pri=sum(1 for v in priv.values() if v=='private'); dele=sum(1 for v in priv.values() if v=='削除' or v not in ('public','private'))
o.append(f"\n**集計**：manifest記録 {len(priv)}本中 public={pub} / private={pri} / 削除={dele}\n")
o.append("\n## 残作業\n- private の回：Studioで公開（or 公開予約）\n- 各Short：Studioで「関連動画」に本編を設定（API不可）\n- 未UP：EP17〜24（EP20は一旦Studioから削除済み・要再UP）／ EP21〜24は未制作\n")
open("docs/upload-status.md","w",encoding="utf-8").write("".join(o))
print(f"regenerated. public={pub} private={pri} deleted={dele} tracked={len(priv)}")
