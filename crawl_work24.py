import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlencode
import re
import time
import os
import json

BASE_URL = "https://www.work24.go.kr"
LIST_URL = f"{BASE_URL}/cm/c/a/0100/selectBbttList.do"
DETAIL_URL = f"{BASE_URL}/cm/c/a/0100/selectBbttInfo.do"

BBS_CL_CD = "kf9cT1sUygs8E64dnqWAxg=="

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

STATE_FILE = "attachments_state.json"


# -------------------------------------------------
# 상태 파일 로드 / 저장
# -------------------------------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# -------------------------------------------------
# 마지막 페이지 번호
# -------------------------------------------------
def get_last_page():
    try:
        res = requests.get(
            LIST_URL,
            params={"currentPageNo": 1, "bbsClCd": BBS_CL_CD},
            headers=HEADERS,
            timeout=10
        )
        res.raise_for_status()
    except requests.exceptions.RequestException:
        return 1

    soup = BeautifulSoup(res.text, "html.parser")
    btn = soup.select_one("button.btn_page.last[onclick]")

    if not btn:
        return 1

    m = re.search(r"fn_Search\((\d+)\)", btn.get("onclick", ""))
    return int(m.group(1)) if m else 1


# -------------------------------------------------
# 게시물 목록 수집
# -------------------------------------------------
def fetch_posts():
    last_page = get_last_page()
    print(f"📌 마지막 페이지: {last_page}")

    posts = []

    for page in range(1, last_page + 1):
        print(f"🔍 목록 페이지 {page} 수집")

        try:
            res = requests.get(
                LIST_URL,
                params={"currentPageNo": page, "bbsClCd": BBS_CL_CD},
                headers=HEADERS,
                timeout=10
            )
            res.raise_for_status()
        except requests.exceptions.RequestException:
            continue

        soup = BeautifulSoup(res.text, "html.parser")

        for a in soup.select("a[href^='javascript:fn_DetailInfo']"):
            m = re.search(r"fn_DetailInfo\('(\d+)'\)", a.get("href", ""))
            if not m:
                continue

            ntceStno = m.group(1)
            title = a.get_text(strip=True)

            posts.append({
                "ntceStno": ntceStno,
                "title": title,
                "detail_url": make_detail_url(ntceStno)
            })

        time.sleep(1)

    return posts


# -------------------------------------------------
# 상세 URL 생성
# -------------------------------------------------
def make_detail_url(ntceStno):
    params = {
        "ntceStno": ntceStno,
        "bbsClCd": BBS_CL_CD,
        "currentPageNo": 1,
        "recordCountPerPage": 10,
        "sortTycd": 1,
        "searchDeTpCd": "termSearchGbn0",
        "searchTycd": 3,
        "bbsUrl": "/c/a/0100/selectBbttListPost.do"
    }
    return f"{DETAIL_URL}?{urlencode(params)}"


# -------------------------------------------------
# 첨부파일 수집 (이번 실행 기준)
# -------------------------------------------------
def fetch_attachments_once(post):
    files = []

    try:
        res = requests.get(post["detail_url"], headers=HEADERS, timeout=10)
        res.raise_for_status()
    except requests.exceptions.RequestException:
        print(f"⚠ 상세 페이지 실패 (ntceStno={post['ntceStno']})")
        return files

    soup = BeautifulSoup(res.text, "html.parser")

    for a in soup.select("a[onclick^='gfn_downloadAttFile3nd']"):
        m = re.search(
            r"gfn_downloadAttFile3nd\('([^']+)'\s*,\s*'([^']+)'\)",
            a.get("onclick", "")
        )
        if not m:
            continue

        encAthflSeq, atchFsno = m.groups()

        files.append({
            "name": a.get_text(strip=True),
            "url": f"{BASE_URL}/cm/common/fileDownload3nd.do"
                   f"?encAthflSeq={encAthflSeq}&atchFsno={atchFsno}"
        })

    return files


# -------------------------------------------------
# HTML 생성 (JSON 기준)
# -------------------------------------------------
def make_html(posts, state):
    today = datetime.now().strftime("%Y-%m-%d")

    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Work24 공지사항 ({today})</title>
</head>
<body>
<h1>Work24 공지사항</h1>
<p>생성일: {today}</p>
<hr>
"""

    for post in posts:
        ntceStno = post["ntceStno"]
        html += f"""
<h3>{post['title']}</h3>
<p><a href="{post['detail_url']}" target="_blank">게시물 보기</a></p>
"""

        files = state.get(ntceStno, [])
        if files:
            html += "<ul>"
            for f in files:
                html += f'<li><a href="{f["url"]}" target="_blank">{f["name"]}</a></li>'
            html += "</ul>"
        else:
            html += "<p>첨부파일 없음</p>"

        html += "<hr>"

    html += """
</body>
</html>
"""
    return html


# -------------------------------------------------
# main
# -------------------------------------------------
if __name__ == "__main__":
    print("🚀 Work24 공지사항 수집 시작")

    state = load_state()
    posts = fetch_posts()

    for post in posts:
        ntceStno = post["ntceStno"]
        print(f"📄 게시물 {ntceStno} 첨부파일 확인")

        new_files = fetch_attachments_once(post)
        time.sleep(1.5)

        if not new_files:
            continue

        # 기존 + 신규 병합 (삭제 없음)
        old = state.get(ntceStno, [])
        merged = {(f["name"], f["url"]): f for f in old}
        for f in new_files:
            merged[(f["name"], f["url"])] = f

        state[ntceStno] = list(merged.values())

    save_state(state)

    html = make_html(posts, state)
    with open("work24_notice.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("✅ work24_notice.html / attachments_state.json 생성 완료")
