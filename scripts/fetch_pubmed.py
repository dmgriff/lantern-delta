
import urllib.parse, urllib.request, urllib.error, json, html, re
from xml.etree import ElementTree as ET

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
UA = "LanternDelta/1.0 (+github)"

def _req(url, data=None, headers=None, timeout=30):
    headers = {"User-Agent": UA, **(headers or {})}
    if data is not None and isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def _esearch(term, retmax=100):
    params = {"db":"pubmed","term":term,"retmax":str(retmax),"retmode":"json","sort":"most+recent"}
    raw = _req(f"{EUTILS}/esearch.fcgi?{urllib.parse.urlencode(params)}")
    return json.loads(raw.decode("utf-8"))

def _efetch(pmids):
    params = {"db":"pubmed","id":",".join(pmids),"retmode":"xml"}
    raw = _req(f"{EUTILS}/efetch.fcgi", data=params)
    return raw.decode("utf-8")

def _text(x): return "".join(x.itertext()).strip() if x is not None else ""

def _month(m):
    M = {"Jan":"01","Feb":"02","Mar":"03","Apr":"04","May":"05","Jun":"06","Jul":"07","Aug":"08","Sep":"09","Oct":"10","Nov":"11","Dec":"12"}
    if m in M: return M[m]
    return m if re.fullmatch(r"\d{2}", m or "") else "01"

def _day(d): return d.zfill(2) if (d or "").isdigit() else "01"

def _abstract_to_html(abs_root):
    if abs_root is None: return ""
    import html as _html, re as _re
    blocks = []
    for sec in abs_root.findall(".//AbstractText"):
        label = sec.get("Label") or sec.get("NlmCategory") or ""
        body = _html.unescape(_text(sec))
        body = _html.escape(_re.sub(r"\s+"," ", body))
        if label:
            blocks.append(f'<div class="abs-section"><div class="abs-heading">{_html.escape(label)}</div><div class="abs-body">{body}</div></div>')
        else:
            blocks.append(f'<div class="abs-section"><div class="abs-body">{body}</div></div>')
    return "\n".join(blocks)

def fetch_pubmed(spec, limit=60):
    term = spec.get("query","").strip()
    if not term: return []
    data = _esearch(term, retmax=limit)
    pmids = data.get("esearchresult",{}).get("idlist",[]) or []
    if not pmids: return []
    xml = _efetch(pmids)
    root = ET.fromstring(xml)
    recs = []
    for art in root.findall(".//PubmedArticle"):
        pmid = _text(art.find(".//PMID"))
        title = re.sub(r"\s+"," ", _text(art.find(".//ArticleTitle")))
        journal = _text(art.find(".//Journal/Title"))
        year = _text(art.find(".//Journal/JournalIssue/PubDate/Year"))
        month = _text(art.find(".//Journal/JournalIssue/PubDate/Month"))
        day = _text(art.find(".//Journal/JournalIssue/PubDate/Day"))
        medline_date = _text(art.find(".//Journal/JournalIssue/PubDate/MedlineDate"))
        if year and month and day: published = f"{year}-{_month(month)}-{_day(day)}"
        elif year and month:       published = f"{year}-{_month(month)}-01"
        elif year:                 published = f"{year}-01-01"
        else:                      published = medline_date or ""

        doi = None
        for aid in art.findall(".//ArticleIdList/ArticleId"):
            if (aid.get("IdType") or "").lower() == "doi":
                doi = _text(aid); break

        authors = []
        for a in art.findall(".//AuthorList/Author"):
            last, fore = _text(a.find("LastName")), _text(a.find("ForeName"))
            if last or fore: authors.append(f"{fore} {last}".strip())
        authors_line = ", ".join(authors[:6]) + (" et al." if len(authors)>6 else "")

        abs_html = _abstract_to_html(art.find(".//Abstract"))
        recs.append({
            "pmid": pmid, "title": title, "journal": journal, "published": published,
            "doi": doi, "authors": authors_line, "abstract_html": abs_html
        })
    return recs
