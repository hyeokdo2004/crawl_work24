import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse, parse_qs
import re
import time
import json
import sys

BASE_URL = "https://www.work24.go.kr"
HEADERS = {"User-Agent": "Mozilla/5.0"}

BOARDS = [
    {
        "name": "고용24 공지사항",
        "url": "https://www.work24.go.kr/cm/c/a/0100/selectBbttList.do?currentPageNo=1&recordCountPerPage=10&bbsClCd=kf9cT1sUygs8E64dnqWAxg%3D%3D",
        "fallback_param": "ntceStno"
    },
    {
        "name": "고용24 이벤트",
        "url": "https://www.work24.go.kr/cm/c/e/0100/selectEvtList.do?currentPageNo=1&recordCountPerPage=10&evtStcd=",
        "fallback_param": "evtSeq"
    },
    {
        "name": "고용24 공지사항(B1100)",
        "url": "https://www.work24.go.kr/cm/c/b/1100/selectBbttList.do?currentPageNo=1&recordCountPerPage=10",
        "fallback_param": "polySvcFomtId"
    },
    {
        "name": "고용24 뉴스레터",
        "url": "https://www.work24.go.kr/cm/c/d/0220/selectGatherNewsLetter.do?currentPageNo=1&recordCountPerPage=10&bbsClCd=DnDyhlwrq2vGTpGw9B1HxQ%3D%3D",
        "fallback_param": "ntceStno"
    },
    {
        "name": "직업훈련 공지사항",
        "url": "https://www.work24.go.kr/cm/c/a/0410/selectBbttList.do?currentPageNo=1&recordCountPerPage=10&bbsClCd=OosccI71O3P2dBxVz5A40Q%3D%3D",
        "fallback_param": "ntceStno"
    },

    # 요청하신 wk 게시판들
    {
        "name": "상세 채용정보",
        "url": "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do?currentPageNo=1&recordCountPerPage=10&bbsUrl=%2Fa%2Fb%2F1200%2FretriveDtlEmpSrchListPost.do",
        "fallback_param": "seq"
    },
    {
        "name": "내 주변 채용정보",
        "url": "https://www.work24.go.kr/wk/a/b/1600/retriveAroundMeEmpInfoList.do?currentPageNo=1&recordCountPerPage=10&bbsUrl=%2Fa%2Fb%2F1600%2FretriveAroundMeEmpInfoListPost.do",
        "fallback_param": "seq"
    },
    {
        "name": "사업 검색",
        "url": "https://www.work24.go.kr/wk/a/d/1000/retrieveBusiSearch.do?currentPageNo=1&recordCountPerPage=10&bbsUrl=%2Fa%2Fd%2F1000%2FretrieveBusiSearchPost.do",
        "fallback_param": "seq"
    },
    {
        "name": "채용 행사",
        "url": "https://www.work24.go.kr/wk/a/f/1100/retrieveEmpEventList.do?currentPageNo=1&recordCountPerPage=10&bbsUrl=%2Fa%2Ff%2F1100%2FretrieveEmpEventListPost.do",
        "fallback_param": "seq"
    },
    {
        "name": "온라인 채용박람회",
        "url": "https://www.work24.go.kr/wk/a/f/1100/retrieveOnlineEmpExhbList.do?currentPageNo=1&recordCountPerPage=10&bbsUrl=%2Fa%2Ff%2F1100%2FretrieveOnlineEmpExhbListPost.do",
        "fallback_param": "seq"
    },
    {
        "name": "고용 동향 이미지",
        "url": "https://www.work24.go.kr/wk/r/e/1140/pictureEmpTrend.do?currentPageNo=1&recordCountPerPage=10&bbsUrl=%2Fr%2Fe%2F1140%2FpictureEmpTrendPost.do",
        "fallback_param": "seq"
    },
    {
        "name": "고용 뉴스",
        "url": "https://www.work24.go.kr/wk/r/g/1110/retrieveEmpNewsList.do?currentPageNo=1&recordCountPerPage=10&bbsUrl=%2Fr%2Fg%2F1110%2FretrieveEmpNewsListPost.do",
        "fallback_param": "seq"
    },
]


def extract_detail_param_name(html: str):
    m = re.search(
        r"function\s+fn_DetailInfo\s*\(\s*(\w+)\s*\)\s*\{[^}]*?\$\(\"#(\w+)\"\)\.val",
        html,
        re.DOTALL
    )
    return m.group(2) if m else None


def get_last_page(soup: BeautifulSoup) -> int:
    pages = []
    for el in soup.select("[onclick*='fn_Search']"):
        m = re.search(r"fn_Search\((\d+)\)", el.get("onclick", ""))
        if m:
            pages.append(int(m.group(1)))
    return max(pages) if pages else 1


def extract_posts(soup: BeautifulSoup):
    posts = []
    for a in soup.select("a"):
        target = a.get("onclick", "") or a.get("href", "")
        if "fn_DetailInfo" not in target:
            continue

        # 첫 번째 인자(문자/숫자/혼합) 허용
        m = re.search(r"fn_DetailInfo\s*\(\s*'([^']+)'", target)
        if not m:
            continue

        posts.append({
            "id": m.group(1),
            "title": a.get_text(" ", strip=True) or "(제목 없음)"
        })
    return posts


def extract_attachments(info_url: str):
    files = []
    try:
        res = requests.get(info_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
    except:
        return files

    for a in soup.select("a[onclick^='gfn_downloadAttFile3nd']"):
        m = re.search(
            r"gfn_downloadAttFile3nd\('([^']+)'\s*,\s*'([^']+)'\)",
            a.get("onclick", "")
        )
        if m:
            enc, fsno = m.groups()
            files.append({
                "name": a.get_text(strip=True),
                "url": f"{BASE_URL}/cm/common/fileDownload3nd.do?encAthflSeq={enc}&atchFsno={fsno}"
            })
    return files


def main():
    results = {}

    for board in BOARDS:
        parsed = urlparse(board["url"])
        list_path = parsed.path
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        params.setdefault("currentPageNo", "1")

        # 1) 첫 페이지 가져오기
        res = requests.get(f"{BASE_URL}{list_path}", params=params, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, "html.parser")

        # 2) detail 파라미터명
        detail_param = extract_detail_param_name(res.text) or board["fallback_param"]

        # 3) 마지막 페이지
        last_page = get_last_page(soup)

        board_posts = []

        for page in range(1, last_page + 1):
            params["currentPageNo"] = str(page)

            res = requests.get(f"{BASE_URL}{list_path}", params=params, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(res.text, "html.parser")

            posts = extract_posts(soup)

            for post in posts:
                # list -> info (기존 로직 유지)
                info_path = list_path.replace("List", "Info")
                info_params = params.copy()
                info_params[detail_param] = post["id"]
                info_url = f"{BASE_URL}{info_path}?{urlencode(info_params)}"

                files = extract_attachments(info_url)

                board_posts.append({
                    "id": post["id"],
                    "title": post["title"],
                    "info_url": info_url,
                    "attachments": files
                })

                time.sleep(0.3)

        results[board["name"]] = board_posts

    # 파일로 저장하지 않고 stdout으로 JSON 출력
    json.dump(results, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
