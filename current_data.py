"""Central collection of current FDJ results; Android only reads the published feed."""
from __future__ import annotations
import hashlib, json, re, unicodedata, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from html.parser import HTMLParser
import build_data

PARIS = ZoneInfo("Europe/Paris")
CATALOG = "https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/draws"
GAMES = {"draw-13": "loto", "draw-14": "superloto"}
DAYS = ("lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche")
MONTHS = ("janvier","fevrier","mars","avril","mai","juin","juillet","aout","septembre","octobre","novembre","decembre")

def plain(value):
    return "".join(c for c in unicodedata.normalize("NFD",value) if not unicodedata.combining(c)).lower()

def result_path(date):
    d = datetime.strptime(date,"%Y-%m-%d")
    return f"/jeux-de-tirage/loto/resultats/{DAYS[d.weekday()]}-{d.day:02d}-{MONTHS[d.month-1]}-{d.year}"

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical, self.text, self.hidden = [], [], 0
    def handle_starttag(self,tag,attrs):
        attrs = dict(attrs)
        if tag in ("script","style"): self.hidden += 1
        if tag == "link" and attrs.get("rel","").lower() == "canonical": self.canonical.append(attrs.get("href"))
    def handle_endtag(self,tag):
        if tag in ("script","style") and self.hidden: self.hidden -= 1
    def handle_data(self,data):
        if not self.hidden: self.text.append(data)

def parse_result(source,game,date):
    if game not in GAMES.values(): raise ValueError("Unknown game")
    page = Page()
    page.feed(source)
    path = result_path(date)
    if not any(url in (path,"https://www.fdj.fr"+path) for url in page.canonical):
        raise ValueError("Official page date mismatch")
    day = datetime.strptime(date,"%Y-%m-%d")
    label = "super loto" if game == "superloto" else "loto"
    heading = f"combinaison gagnante du tirage {label} du {DAYS[day.weekday()]} {day.day} {MONTHS[day.month-1]} {day.year}"
    text = re.sub(r"\s+"," ",plain(" ".join(page.text)))
    if heading not in text: raise ValueError("Official draw identity missing")
    body = text.split(heading,1)[1][:800]
    for stop in ("2nd tirage","second tirage","prochain tirage"): body = body.split(stop,1)[0]
    pattern = r"combinaison gagnante(?:[^.;]{0,80}?)(\d{1,2})\s*[-–]\s*(\d{1,2})\s*[-–]\s*(\d{1,2})\s*[-–]\s*(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(?:;|,|et)\s*le numero chance(?: est le)?\s+(\d{1,2})\b"
    found = set()
    for match in re.finditer(pattern,body):
        values = list(map(int,match.groups()))
        numbers,chance = sorted(values[:5]),values[5]
        if len(set(numbers)) != 5 or not all(1 <= n <= 49 for n in numbers) or not 1 <= chance <= 10:
            raise ValueError("Invalid official result")
        found.add((tuple(numbers),chance))
    if len(found) != 1: raise ValueError("Missing or ambiguous official result")
    numbers,chance = found.pop()
    return {"id":f"{game}:{date}","game":game,"date":date,"numbers":list(numbers),"chance":chance}

def get_bytes(url):
    req = urllib.request.Request(url,headers={"User-Agent":"STATOR49-DATA/2.0","Accept":"application/json, text/html"})
    with urllib.request.urlopen(req,timeout=40) as response: data = response.read(4_000_001)
    if len(data) > 4_000_000: raise ValueError("Official response too large")
    return data

def metadata(row):
    game = GAMES.get(row.get("game_external_id"))
    if game is None: return None
    at = row.get("planned_at","")
    stamp = datetime.fromisoformat(at.replace("Z","+00:00"))
    if stamp.tzinfo is None: raise ValueError("Official time has no timezone")
    date = stamp.astimezone(PARIS).date().isoformat()
    return {"id":f"{game}:{date}","game":game,"date":date,"plannedAt":at}

def catalog(from_date,now,get=get_bytes):
    start = (datetime.strptime(from_date,"%Y-%m-%d").replace(tzinfo=PARIS)-timedelta(days=1)).isoformat()
    published,seen = {},set()
    for page in range(501):
        params = {"game_name":"loto,superloto","current":"false","from_planned_at":start,"to_planned_at":"now","sort":"planned_at:asc","page":page}
        rows = json.loads(get(CATALOG+"?"+urllib.parse.urlencode(params)))
        if not isinstance(rows,list): raise ValueError("Invalid official catalog")
        signature = json.dumps(rows,sort_keys=True)
        if rows and signature in seen: raise ValueError("Repeated official catalog page")
        seen.add(signature)
        for row in rows:
            if not row.get("processed_at"): continue
            target = metadata(row)
            if target and from_date <= target["date"] <= now.astimezone(PARIS).date().isoformat():
                if datetime.fromisoformat(target["plannedAt"].replace("Z","+00:00")) > now:
                    raise ValueError("Future published result")
                published[target["id"]] = target
        if len(rows) < 20: break
    else: raise ValueError("Official pagination limit exceeded")
    if not published: raise ValueError("No official published draw to verify")
    params = {"game_name":"loto,superloto","current":"true","sort":"planned_at:asc"}
    rows = json.loads(get(CATALOG+"?"+urllib.parse.urlencode(params)))
    if not isinstance(rows,list): raise ValueError("Invalid official calendar")
    upcoming = []
    for row in rows:
        if row.get("processed_at"): continue
        target = metadata(row)
        if target and target["date"] >= now.astimezone(PARIS).date().isoformat() and target["id"] not in published:
            upcoming.append(target)
    upcoming.sort(key=lambda x:(x["plannedAt"],x["id"]))
    return published,upcoming[0] if upcoming else None

def collect(archive,now=None,get=get_bytes):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError("Clock must include timezone")
    by_id = {d["id"]:d for d in archive["draws"]}
    published,next_draw = catalog(max(d["date"] for d in by_id.values()),now,get)
    for ident,target in sorted(published.items(),key=lambda item:(item[1]["date"],item[0])):
        if ident not in by_id:
            source = get("https://www.fdj.fr"+result_path(target["date"])).decode("utf-8")
            by_id[ident] = parse_result(source,target["game"],target["date"])
    if set(published)-set(by_id): raise ValueError("Missing published draw")
    last = max(d["date"] for d in by_id.values())
    if not {d["id"] for d in by_id.values() if d["date"] == last}.issubset(published):
        raise ValueError("Archive and official catalog disagree")
    draws = sorted(by_id.values(),key=lambda d:(d["date"],d["game"]))
    digest = hashlib.sha256()
    for d in draws: digest.update(f"{d['game']}|{d['date']}|{','.join(map(str,d['numbers']))}|{d['chance']}\n".encode())
    version = f"stator49-fdj-{last}-{digest.hexdigest()[:12]}"
    checked = now.replace(microsecond=0).isoformat().replace("+00:00","Z")
    archive = {"schemaVersion":1,"archiveVersion":version,"source":"FDJ — archives et résultats officiels Loto et Super Loto","generatedAt":checked,"draws":draws}
    raw = json.dumps(archive,ensure_ascii=False,separators=(",",":")).encode()
    manifest = {"schemaVersion":1,"feedVersion":1,"archiveVersion":version,"lastDraw":last,"drawCount":len(draws),
        "drawCounts":{g:sum(d["game"]==g for d in draws) for g in GAMES.values()},
        "archiveAsset":"loto_draws.json","sha256":hashlib.sha256(raw).hexdigest(),"generatedAt":checked,
        "checkedAt":checked,"coverageConfirmed":True,"expectedPublishedIds":sorted(published),"nextDraw":next_draw,
        "source":"FDJ — collecte centralisée STATORDATA"}
    return archive,manifest

def main():
    archive,_ = build_data.build()
    archive,manifest = collect(archive)
    build_data.OUT.mkdir(parents=True,exist_ok=True)
    (build_data.OUT/"loto_draws.json").write_text(json.dumps(archive,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (build_data.OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Validated {manifest['drawCount']} results through {manifest['lastDraw']}")

if __name__ == "__main__": main()
