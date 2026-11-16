"""Publish a small manifest only after checking the immutable public archive."""
import base64, hashlib, json, os, urllib.error, urllib.request
from pathlib import Path
REPO = "Fabion80/STATORDATA"
API = "https://api.github.com/repos/"+REPO
def request(url,data=None,method=None,authenticated=False):
    headers={"User-Agent":"STATOR49-DATA/2.0","Accept":"application/vnd.github+json"}
    if authenticated: headers["Authorization"]="Bearer "+os.environ["GH_TOKEN"]
    if data is not None:
        data=json.dumps(data).encode()
        headers["Content-Type"]="application/json"
    with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=headers,method=method),timeout=40) as response:
        return response.read()
def make_feed(manifest,published,archive,asset_url):
    if not asset_url.startswith("https://github.com/"+REPO+"/releases/download/") or not asset_url.endswith("/loto_draws.json") or "/latest/" in asset_url:
        raise ValueError("Archive must use an immutable STATORDATA URL")
    data=json.loads(archive)
    if hashlib.sha256(archive).hexdigest()!=published["sha256"]: raise ValueError("Checksum mismatch")
    if data["archiveVersion"]!=manifest["archiveVersion"] or published["archiveVersion"]!=manifest["archiveVersion"]:
        raise ValueError("Concurrent or incorrect publication")
    if len(data["draws"])!=manifest["drawCount"] or max(d["date"] for d in data["draws"])!=manifest["lastDraw"]:
        raise ValueError("Archive counts mismatch")
    if not set(manifest["expectedPublishedIds"]).issubset(d["id"] for d in data["draws"]): raise ValueError("Published results missing")
    if manifest.get("coverageConfirmed") is not True: raise ValueError("Coverage not confirmed")
    return {**manifest,"sha256":published["sha256"],"generatedAt":published["generatedAt"],"archiveUrl":asset_url}
def main():
    if os.environ.get("GITHUB_REPOSITORY")!=REPO or os.environ.get("GITHUB_REF")!="refs/heads/main":
        raise ValueError("Publication restricted to the data repository main branch")
    manifest=json.loads(Path("dist/manifest.json").read_text())
    release=json.loads(request(API+"/releases/latest",authenticated=True))
    assets={a["name"]:a["browser_download_url"] for a in release["assets"]}
    feed=make_feed(manifest,json.loads(request(assets["manifest.json"])),request(assets["loto_draws.json"]),assets["loto_draws.json"])
    endpoint=API+"/contents/feed/manifest.json"
    payload={"message":"Refresh verified draw feed "+feed["checkedAt"],"branch":"main",
        "content":base64.b64encode((json.dumps(feed,ensure_ascii=False,indent=2)+"\n").encode()).decode()}
    try: payload["sha"]=json.loads(request(endpoint+"?ref=main",authenticated=True))["sha"]
    except urllib.error.HTTPError as error:
        if error.code!=404: raise
    request(endpoint,payload,"PUT",authenticated=True)
    print("Opening feed published:",feed["lastDraw"],feed["drawCount"])
if __name__=="__main__": main()
