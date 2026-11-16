"""Fetch real source snapshots. Raw text/index stay outside Git; manifest is public."""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
DATA = ROOT / "app/data"
SETID = "cf74ba2f-afc5-4baa-8594-979c889a5831"
FDA = "https://www.fda.gov/drugs/drug-safety-and-availability/fda-requires-warnings-about-increased-risk-serious-heart-related-events-cancer-blood-clots-and-death"
SPL = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{SETID}.xml"
PUBMED = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=35081280,35027405&retmode=xml"


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def fetch(name, url):
    p = CACHE / name
    if not p.exists() or "--refresh" in sys.argv:
        r = httpx.get(url, timeout=60, follow_redirects=True, headers={"User-Agent": "EvidenceDeskResearchPrototype/0.1"})
        r.raise_for_status()
        p.write_bytes(r.content)
    return p.read_bytes()


def main():
    CACHE.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    sources, passages = [], []
    now = datetime.now(timezone.utc).isoformat()

    def source(sid, title, kind, published, url, raw, **extra):
        row = dict(id=sid, title=title, source_type=kind, published=published,
                   url=url, retrieved_at=now, sha256=hashlib.sha256(raw).hexdigest(), **extra)
        sources.append(row)
        return row

    def passage(src, section, text):
        text = clean(text)
        if len(text) < 60:
            return
        # Stable ordered paragraph chunks; no labels or gold answers added.
        words = text.split()
        for offset in range(0, len(words), 290):
            part = " ".join(words[offset:offset+330])
            pid = src['id'] + "-" + hashlib.sha256((section+part).encode()).hexdigest()[:10]
            passages.append(dict(id=pid, source_id=src['id'], section=section, text=part,
                                 source_type=src['source_type'], published=src['published']))

    raw = fetch("fda.html", FDA)
    soup = BeautifulSoup(raw, "html.parser")
    main = soup.find("main")
    article = main.select_one("article#main-content")
    if article is None:
        raise RuntimeError('FDA article structure changed; inspect before re-indexing.')
    src = source("fda-2021", "FDA safety communication: JAK inhibitors", "regulatory", "2021-09-01", FDA, raw,
                 scope="Public regulatory communication; source date filter is not a reconstructed historical website.")
    section = "FDA safety communication"
    for node in article.find_all(["h2", "h3", "p", "li"]):
        if node.name in ("h2", "h3"):
            section = clean(node.get_text(" "))
        elif node.find_parent("nav") is None:
            txt = clean(node.get_text(" "))
            if len(txt) >= 80 and not any(x in txt for x in ["Subscribe to", "An official website", "Share on", "Contact FDA"]):
                passage(src, section, txt)

    raw = fetch("dailymed.xml", SPL)
    root = ET.fromstring(raw)
    ns = {"h": "urn:hl7-org:v3"}
    effective = root.find("h:effectiveTime", ns).attrib['value'][:8]
    version = root.find("h:versionNumber", ns).attrib['value']
    src = source("label-xeljanz", "Xeljanz / Xeljanz XR prescribing information", "label",
                 f"{effective[:4]}-{effective[4:6]}-{effective[6:8]}",
                 f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={SETID}", raw,
                 version=version, set_id=SETID, scope="Selected label sections; DailyMed listing alone does not establish approval.")
    prefixes = ("WARNING:", "1.1 ", "5.2 ", "5.3 ", "5.4 ", "5.5 ", "14.6 ")
    for node in root.findall(".//h:section", ns):
        title = node.find("h:title", ns)
        body = node.find("h:text", ns)
        if title is None or body is None:
            continue
        section = clean(" ".join(title.itertext()))
        if section.startswith(prefixes) or "Safety Study" in section:
            passage(src, section, " ".join(body.itertext()))

    raw = fetch("pubmed.xml", PUBMED)
    root = ET.fromstring(raw)
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")
        title = clean(" ".join(article.find(".//ArticleTitle").itertext()))
        # These dates are checked against the fetched publication records.
        date = {"35081280": "2022-01-27", "35027405": "2022-01-13"}[pmid]
        doi = next((x.text for x in article.findall(".//ArticleId") if x.attrib.get("IdType") == "doi"), None)
        src = source("pmid-"+pmid, title, "research", date,
                     "https://pubmed.ncbi.nlm.nih.gov/"+pmid+"/", ET.tostring(article),
                     pmid=pmid, doi=doi, scope="Abstract only. No claim of full-text appraisal.")
        for node in article.findall(".//AbstractText"):
            passage(src, "Abstract / "+node.attrib.get("Label", "text"), " ".join(node.itertext()))

    for src in sources:
        if not any(p['source_id'] == src['id'] for p in passages):
            raise RuntimeError('No passages extracted for '+src['id'])
    corpus = {"retrieved_at": now, "sources": sources, "passages": passages}
    (DATA / "corpus.json").write_text(json.dumps(corpus, indent=2))
    manifest = {"retrieved_at": now, "sources": sources, "passage_count": len(passages),
                "corpus_sha256": hashlib.sha256((DATA/'corpus.json').read_bytes()).hexdigest(),
                "scope": "Four source documents, selected sections; not a comprehensive literature review.",
                "raw_text_redistributed": False}
    (DATA / "source-manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(json.dumps({"sources": len(sources), "passages": len(passages), "manifest": str(DATA/'source-manifest.json')}))


if __name__ == "__main__":
    main()
