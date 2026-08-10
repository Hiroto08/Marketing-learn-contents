import os,json,urllib.request,urllib.parse,re,datetime,glob
cid=os.environ["YT_CLIENT_ID"];csec=os.environ["YT_CLIENT_SECRET"];rt=os.environ["YT_REFRESH_TOKEN"]
data=urllib.parse.urlencode({"client_id":cid,"client_secret":csec,"refresh_token":rt,"grant_type":"refresh_token"}).encode()
tok=json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token",data=data),timeout=30))["access_token"]
def api(p,q): return json.load(urllib.request.urlopen(urllib.request.Request("https://www.googleapis.com/youtube/v3/"+p+"?"+urllib.parse.urlencode(q),headers={"Authorization":"Bearer "+tok}),timeout=30))
chinfo=api("channels",{"part":"snippet,contentDetails","mine":"true"})["items"][0]
ch=chinfo["snippet"]["title"]
def load(p):
    try: return json.load(open(p,encoding="utf-8"))
    except: return {}
# --- YouTube実体から「第NN回」本編を補完（ローカルmanifestが無いブランチ対策）---
def _is_short(dur):
    m=re.match(r"PT(?:(\d+)M)?(?:(\d+)S)?",dur or "");
    return (int(m.group(1) or 0)*60+int(m.group(2) or 0))<=60 if m else False
_uploads_pl=chinfo["contentDetails"]["relatedPlaylists"]["uploads"]
_yt=[]; _pg=None
while True:
    _q={"part":"snippet","playlistId":_uploads_pl,"maxResults":"50"}
    if _pg:_q["pageToken"]=_pg
    _r=api("playlistItems",_q)
    _yt+= [(it["snippet"]["resourceId"]["videoId"],it["snippet"]["title"]) for it in _r["items"]]
    _pg=_r.get("nextPageToken")
    if not _pg:break
# durations for isShort
_dur={}
_allids=[v for v,_ in _yt]
for i in range(0,len(_allids),50):
    for it in api("videos",{"part":"contentDetails","id":",".join(_allids[i:i+50])})["items"]:
        _dur[it["id"]]=it["contentDetails"]["duration"]
_kanji={1:"一",2:"二",3:"三",4:"四",5:"五",6:"六",7:"七",8:"八",9:"九",10:"十",11:"十一",12:"十二",13:"十三",14:"十四",15:"十五",16:"十六",17:"十七",18:"十八",19:"十九",20:"二十",21:"二十一",22:"二十二",23:"二十三",24:"二十四"}
yt_main={}
for vid,title in _yt:
    if _is_short(_dur.get(vid)): continue
    for ep in range(1,25):
        if re.search(rf"第\s*({ep}|{_kanji.get(ep,'')})\s*回",title):
            yt_main[ep]=vid  # 後勝ち＝最新
            break
ROADMAP={17:"ブランド・エクイティ",18:"LTV/CRM",19:"マーケ組織",20:"グロースハック",21:"ヒット商品",22:"V字回復",23:"失敗事例",24:"未来のマーケター"}
eps=[]; allids=set()
for d in sorted(glob.glob("0*/ep*")):
    if not os.path.isdir(d): continue
    ep=int(re.search(r"ep(\d+)",d).group(1))
    mainmf=load(f"{d}/publish_manifest.json")
    main=[v.get("videoId") for v in mainmf.values()] if mainmf else []
    main_src="manifest"
    if not main and ep in yt_main:      # ローカルmanifest欠落→YouTube実体で補完
        main=[yt_main[ep]]; main_src="youtube"
    shorts=[]
    for sd in sorted(glob.glob(f"{d}/shorts_build/short*/publish_manifest.json")):
        for v in load(sd).values(): shorts.append(v.get("videoId"))
    has_shorts_md=os.path.exists(f"{d}/shorts.md")
    eps.append((ep,d,main,shorts,has_shorts_md,main_src))
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
for ep,d,main,shorts,hsm,msrc in eps:
    mv=main[0] if main else None
    mp=P(mv) if mv else "未UP"
    if mv and msrc=="youtube": mp+="※YT補完"
    svs=" ".join(f"`{x}`" for x in shorts) if shorts else ("未UP" if hsm else "—")
    sp=("／".join(sorted(set(P(x) for x in shorts)))) if shorts else ("未UP" if hsm else "—")
    o.append(f"| EP{ep:02d} | `{os.path.basename(d)}` | {('`'+mv+'`') if mv else '—'} | {mp} | {svs} | {sp} |\n")
pub=sum(1 for v in priv.values() if v=='public'); pri=sum(1 for v in priv.values() if v=='private'); dele=sum(1 for v in priv.values() if v=='削除' or v not in ('public','private'))
o.append(f"\n**集計**：manifest記録 {len(priv)}本中 public={pub} / private={pri} / 削除={dele}\n")
pubeps=sorted([ep for ep,d,main,shorts,hsm,msrc in eps if main and P(main[0])=="public"])
nextep=(max(pubeps)+1) if pubeps else 1
o.append("\n## 公開順序（絶対則：飛び級厳禁）\n")
o.append(f"- 現在 public 済みの最大EP＝**EP{max(pubeps):02d}**／次に公開してよいのは**EP{nextep:02d}のみ**。\n" if pubeps else "- まだpublicの本編なし。\n")
o.append("- ※本編は必ずEP番号の昇順で公開。先のEPが非公開UP済みでも飛ばして公開しない（詳細 docs/autonomous-operation.md §3.1）。\n")
o.append("\n## 残作業\n- 次に公開：上記「次に公開してよいEP」を public 化（or 次の土曜18:00 JSTに公開予約）\n- private の後続回：EP順を守って順次公開\n- 各Short：Studioで「関連動画」に本編を設定（API不可・docs/shorts-related-video-checklist.md）\n- 未制作：EP21〜24（L3新規制作）\n")
open("docs/upload-status.md","w",encoding="utf-8").write("".join(o))
print(f"regenerated. public={pub} private={pri} deleted={dele} tracked={len(priv)}")
