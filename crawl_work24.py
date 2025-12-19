import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlencode

LIST_URL = "https://www.work24.go.kr/cm/c/a/0100/selectBbttList.do"
BASE_URL = "https://www.work24.go.kr"

# 게시판 고정 파라미터
BBS_CL_CD = "kf9cT1sUygs8E64dnqWAxg=="

def make_detail_url(ntceStno):
    params = {
        "ntceStno": ntceStno,
        "bbsClCd": BBS_CL_CD,
        "currentPageNo": 1,
        "recordCountPerPage": 10,
        "sortTycd": 1,
        "startDt": "",
        "endDt": "",
        "searchDeTpCd": "termSearchGbn0",
        "searchTxt": "",
        "searchTycd": 3,
        "upprJobClCd": "",
        "jobClCd": "",
        "bbsUrl": "/c/a/0100/selectBbttListPost.do"
    }

    return f"{BASE_URL}/cm/c/a/0100/selectBbttInfo.do?{urlencode(params)}"


def fetch_posts():
    params = {
        "currentPageNo": 1,
        "bbsClCd": BBS_CL_CD
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = requests.get(LIST_URL, params=params, headers=headers)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")

    posts = []

    for a in soup.select("a[href^='javascript:fn_DetailInfo']"):
        href = a.get("href")

        try:
            ntceStno = href.split("'")[1]
        except IndexError:
            continue

        title = a.get_text(strip=True)

        posts.append({
            "ntceStno": ntceStno,
            "title": title,
            "url": make_detail_url(ntceStno)
        })

    return posts


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
<ul>
"""

    for p in posts:
        html += f"""  <li>
    <a href="{p['url']}" target="_blank">{p['title']}</a>
  </li>
"""

    html += """
</ul>
</body>
</html>
"""
    return html


if __name__ == "__main__":
    print("🔍 Work24 공지사항 크롤링 시작")

    posts = fetch_posts()
    print(f"📌 추출된 게시물 수: {len(posts)}")

    for p in posts:
        print(f" - {p['ntceStno']} | {p['title']}")

    html = make_html(posts)

    with open("work24_notice.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("✅ work24_notice.html 생성 완료")
