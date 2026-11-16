import hashlib,json,unittest
from datetime import datetime,timezone
from current_data import parse_result,result_path,collect,metadata
from publish_feed import make_feed
DATE="2026-11-14"
def page(game="loto",date=DATE,values="1 - 2 - 3 - 4 - 5",chance=7):
    label="Super Loto" if game=="superloto" else "Loto"
    return f'<link rel="canonical" href="https://www.fdj.fr{result_path(date)}"><h1>Combinaison gagnante du tirage {label} du samedi 14 novembre 2026</h1><p>Combinaison gagnante : {values} ; le numéro Chance est le {chance}.</p>'
class CurrentDataTests(unittest.TestCase):
    def test_dated_loto_and_super_loto(self):
        for game in ("loto","superloto"):
            r=parse_result(page(game),game,DATE)
            self.assertEqual(r["id"],game+":"+DATE)
            self.assertEqual(r["numbers"],[1,2,3,4,5])
            self.assertEqual(r["chance"],7)
    def test_wrong_date_game_duplicate_and_ambiguous_result(self):
        for source,game,date in [(page(),"loto","2026-11-16"),(page(),"superloto",DATE),(page(values="1 - 1 - 3 - 4 - 5"),"loto",DATE),(page(chance=11),"loto",DATE),(page()+page(values="1 - 2 - 3 - 4 - 6"),"loto",DATE)]:
            with self.assertRaises(ValueError): parse_result(source,game,date)
    def test_no_script_or_second_draw_result(self):
        with self.assertRaises(ValueError): parse_result('<script>'+page()+'</script>',"loto",DATE)
        with self.assertRaises(ValueError): parse_result(page().replace("Combinaison gagnante :","Second tirage. Combinaison gagnante :"),"loto",DATE)
    def test_paris_date(self):
        self.assertEqual(metadata({"game_external_id":"draw-14","planned_at":"2026-11-13T23:30:00Z"})["date"],DATE)
    def test_collects_same_day_and_preserves_old_draw(self):
        old={"id":"loto:2026-11-11","game":"loto","date":"2026-11-11","numbers":[10,20,30,40,49],"chance":2}
        rows=[{"game_external_id":"draw-13","planned_at":d+"T20:00:00Z","processed_at":d+"T20:05:00Z"} for d in ("2026-11-11",DATE)]
        calls=[]
        def get(url):
            calls.append(url)
            if "current=false" in url: return json.dumps(rows).encode()
            if "current=true" in url: return b"[]"
            return page().encode()
        now=datetime(2026,11,14,22,tzinfo=timezone.utc)
        archive,manifest=collect({"draws":[old]},now,get)
        self.assertEqual(archive["draws"][0],old)
        self.assertEqual(manifest["lastDraw"],DATE)
        self.assertEqual(len([u for u in calls if "/resultats/" in u]),1)
        again,m=collect(archive,now,get)
        self.assertEqual(m["archiveVersion"],manifest["archiveVersion"])
        self.assertEqual(again["draws"],archive["draws"])
    def test_failed_catalog_prevents_publication(self):
        with self.assertRaises(ValueError): collect({"draws":[{"id":"loto:"+DATE,"date":DATE}]},datetime(2026,11,14,22,tzinfo=timezone.utc),lambda _:b"[]")
    def test_feed_requires_pinned_coherent_archive(self):
        raw=json.dumps({"archiveVersion":"v1","draws":[{"id":"loto:"+DATE,"date":DATE}]}).encode()
        m={"archiveVersion":"v1","drawCount":1,"lastDraw":DATE,"expectedPublishedIds":["loto:"+DATE],"coverageConfirmed":True}
        p={"archiveVersion":"v1","sha256":hashlib.sha256(raw).hexdigest(),"generatedAt":"2026-11-14T22:00:00Z"}
        url="https://github.com/Fabion80/STATORDATA/releases/download/data-v1/loto_draws.json"
        self.assertEqual(make_feed(m,p,raw,url)["archiveUrl"],url)
        for bad in (url.replace("/download/data-v1/","/latest/download/"),url.replace("Fabion80","other")):
            with self.assertRaises(ValueError): make_feed(m,p,raw,bad)
        with self.assertRaises(ValueError): make_feed(m,p,raw+b" ",url)
        with self.assertRaises(ValueError): make_feed({**m,"expectedPublishedIds":["loto:2026-11-16"]},p,raw,url)
if __name__=="__main__": unittest.main()
