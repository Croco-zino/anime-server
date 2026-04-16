from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

BASE_URL = "https://hondram.site"

headers = {
    "User-Agent": "Mozilla/5.0"
}

# =========================
# ID SYSTEM (RAM ONLY)
# =========================
id_map = {}
counter = 1

def get_id(url):
    global counter
    if url in id_map:
        return id_map[url]
    id_map[url] = counter
    counter += 1
    return id_map[url]

def get_url(_id):
    for url, uid in id_map.items():
        if uid == int(_id):
            return url
    return None

# =========================
# SEARCH
# =========================
@app.route("/search")
def search():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "missing q"})
    try:
        url = f"{BASE_URL}/?s={query}"
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        results = []
        seen = set()
        for a in soup.find_all("a", href=True):
            link = a["href"]
            if BASE_URL not in link:
                continue
            if link in seen:
                continue
            seen.add(link)
            title = a.get_text(strip=True)
            if not title:
                continue
            img = a.find("img")
            results.append({
                "id": get_id(link),
                "title": title,
                "image": img["src"] if img and img.get("src") else None
            })
        return jsonify({
            "query": query,
            "count": len(results),
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e)})

# =========================
# EPISODE SERVERS
# =========================
@app.route("/ep")
def episode():
    _id = request.args.get("id")
    if not _id:
        return jsonify({"error": "missing id"})
    url = get_url(_id)
    if not url:
        return jsonify({"error": "invalid id"})
    try:
        if "?watch=1" not in url:
            url += "?watch=1"
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        servers = []
        BAD = ["wp-json", "xml", "font", ".css", ".svg", ".ttf", ".woff", "googleapis", "jquery", "javascript", "yourcolor", "theme"]
        GOOD = ["vidmoly", "dood", "streamwish", "streamtape", "mp4", "embed", "player", "iframe"]

        # iframes
        for iframe in soup.find_all("iframe"):
            src = iframe.get("src")
            if src and not any(b in src for b in BAD):
                servers.append({"type": "iframe", "url": src})

        # links
        for a in soup.find_all("a", href=True):
            link = a["href"]
            if not any(b in link for b in BAD) and any(g in link for g in GOOD):
                servers.append({"type": "link", "url": link})

        # script scan
        text = res.text
        i = 0
        while True:
            i = text.find("https", i)
            if i == -1:
                break
            j = text.find('"', i)
            if j == -1:
                break
            link = text[i:j]
            if not any(b in link for b in BAD) and any(g in link for g in GOOD):
                servers.append({"type": "script", "url": link})
            i = j

        # remove duplicates
        clean = []
        seen = set()
        for s in servers:
            if s["url"] not in seen:
                seen.add(s["url"])
                clean.append(s)

        return jsonify({
            "id": int(_id),
            "count": len(clean),
            "servers": clean,
            "source": url
        })
    except Exception as e:
        return jsonify({"error": str(e)})

# =========================
# HOME
# =========================
@app.route("/")
def home():
    return jsonify({
        "status": "OK",
        "endpoints": {
            "/search?q=": "Search anime",
            "/ep?id=": "Get clean servers list"
        }
    })