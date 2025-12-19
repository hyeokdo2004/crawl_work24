import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlencode
import re

BASE_URL = "https://www.work24.go.kr"
LIST_URL = f"{BASE_URL}/cm/c/a/0100/selectBbttList.do"
DETAIL_URL = f"{BASE_URL}/cm/c/a/0100/selectBbttInfo.do"

BBS_CL_CD = "kf9cT1sUygs8E64dnqWAxg=="

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# -------------------------------------------------
# 1. 마지막 페이지 번호 추출
# -------------------------------------------------
def get_last_page():
    params = {
        "currentPageNo": 1,
        "bbsClCd": BBS_CL_CD
    }
    res = requests.get(LIST_URL, params=params, headers=HEADERS)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")

    last_btn = soup.select_one("button.btn_page.last[onclick]")
    if not last_btn:
        return 1

    m = re.search(r"fn_Search\((\d+)\)", last_btn["onclick"])
    return int(m.group(1)) if m else 1


# -------------------------------------------------
# 2. 게시판 전체 페이지 순회 → 게시물 수집
# -------------------------------------------------
def fetch_posts_all_pages():
    last_page = get_last_page()
    print(f"📌 마지막 페이지: {last_page}")

    posts = []

    for page in range(1, last_page + 1):
        print(f"🔍 목록 페이지 {page} 수집 중")

        params = {
            "currentPageNo": page,
            "bbsClCd": BBS_CL_CD
        }

        res = requests.get(LIST_URL, params=params, headers=HEADERS)
        res.raise_for_status()

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
                "detail_url": make_detail_url(ntceStno),
                "files": []
            })

    return posts


# -------------------------------------------------
# 3. 게시물 상세 URL 생성
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
# 4. 게시물 상세 페이지 → 첨부파일 추출
# -------------------------------------------------
def fetch_attachments(post):
    res = requests.get(post["detail_url"], headers=HEADERS)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")

    for a in soup.select("a[onclick^='gfn_downloadAttFile3nd']"):
        onclick = a.get("onclick", "")
        m = re.search(
            r"gfn_downloadAttFile3nd\('([^']+)'\s*,\s*'([^']+)'\)",
            onclick
        )
        if not m:
            continue

        encAthflSeq, atchFsno = m.groups()
        filename = a.get_text(strip=True)

        download_url = (
            f"{BASE_URL}/cm/common/fileDownload3nd.do"
            f"?encAthflSeq={encAthflSeq}&atchFsno={atchFsno}"
        )

        post["files"].append({
            "name": filename,
            "url": download_url
        })


# -------------------------------------------------
# 5. HTML 생성
# -------------------------------------------------
def make_html(posts):
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
        html += f"""
<h3>{post['title']}</h3>
<p><a href="{post['detail_url']}" target="_blank">게시물 보기</a></p>
"""

        if post["files"]:
            html += "<ul>"
            for f in post["files"]:
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
# 6. main
# -------------------------------------------------
if __name__ == "__main__":
    print("🚀 Work24 전체 공지사항 수집 시작")

    posts = fetch_posts_all_pages()

    for post in posts:
        print(f"📄 게시물 {post['ntceStno']} 첨부파일 수집")
        fetch_attachments(post)

    html = make_html(posts)

    with open("work24_notice.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("✅ work24_notice.html 생성 완료")
