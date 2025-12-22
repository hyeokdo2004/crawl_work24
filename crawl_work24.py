import requests, json, time
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://www.work24.go.kr"
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 20
STATE_FILE = "work24_state.json"

# ======================
# 모든 게시판 (네가 말한 것 전부)
# ======================
BOARD_CONFIGS = [
    {"name":"고용24 공지사항","list":"/cm/c/a/0100/selectBbttList.do","param":"ntceStno","extra":{"bbsClCd":"kf9cT1sUygs8E64dnqWAxg=="}},
    {"name":"고용24 이벤트","list":"/cm/c/e/0100/selectEvtList.do","param":"evtSeq","extra":{}},
    {"name":"공지사항 B1100","list":"/cm/c/b/1100/selectBbttList.do","param":"polySvcFomtId","extra":{}},
    {"name":"공지사항 0130","list":"/cm/c/b/0130/selectBbttList.do","param":"ntceStno","extra":{"bbsClCd":"+WhIYyX4MTPwl6gr4E19tQ=="}},
    {"name":"뉴스레터","list":"/cm/c/d/0220/selectGatherNewsLetter.do","param":"ntceStno","extra":{"bbsClCd":"DnDyhlwrq2vGTpGw9B1HxQ=="}},
    {"name":"직업훈련 공지","list":"/cm/c/a/0410/selectBbttList.do","param":"ntceStno","extra":{"bbsClCd":"OosccI71O3P2dBxVz5A40Q=="}},

    {"name":"상세채용","list":"/wk/a/b/1200/retriveDtlEmpSrchList.do","param":"empSeq","extra":{}},
    {"name":"내주변채용","list":"/wk/a/b/1600/retriveAroundMeEmpInfoList.do","param":"empSeq","extra":{}},
    {"name":"사업검색","list":"/wk/a/d/1000/retrieveBusiSearch.do","param":"busiSeq","extra":{}},
    {"name":"채용행사","list":"/wk/a/f/1100/retrieveEmpEventList.do","param":"evtSeq","extra":{}},
    {"name":"온라인채용박람회","list":"/wk/a/f/1100/retrieveOnlineEmpExhbList.do","param":"exhbSeq","extra":{}},
    {"name":"고용동향","list":"/wk/r/e/1140/pictureEmpTrend.do","param":"ntceStno","extra":{}},
    {"name":"고용뉴스","list":"/wk/r/g/1110/retrieveEmpNewsList.do","param":"ntceStno","extra":{}},
]

# ======================
# 공통 함수
# ======================
def load_state():
    try:
        with open(STATE_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_FILE,"w",encoding="utf-8") as f:
        json.dump(state,f,ensure_ascii=False,indent=2)

def extract_id(href):
    try:
        return href.split("'")[1]   # fn_DetailInfo('433','ERF') → 433
    except:
        return None

def last_page(html):
    soup = BeautifulSoup(html,"html.parser")
    pages=[]
    for b in soup.select("button[onclick^='fn_Search']"):
        try:
            pages.append(int(b["onclick"].split("(")[1].split(")")[0]))
        except:
            pass
    return max(pages) if pages else 1

def extract_attachments(soup):
    files=[]
    for a in soup.select("a[onclick^='gfn_downloadAttFile3nd']"):
        try:
            args=a["onclick"].split("(")[1].split(")")[0].replace("'","").split(",")
            enc, fsno = args[0], args[1]
            url=f"{BASE_URL}/cm/common/fileDownload3nd.do?encAthflSeq={enc}&atchFsno={fsno}"
            files.append({"name":a.get_text(strip=True),"url":url})
        except:
            pass
    return files

# ======================
# 메인
# ======================
state = load_state()
updated=False

for board in BOARD_CONFIGS:
    print(f"\n📌 {board['name']} 증분 수집")
    state.setdefault(board["name"],{})

    params={"currentPageNo":1,"recordCountPerPage":10}
    params.update(board["extra"])

    r=requests.get(BASE_URL+board["list"],params=params,headers=HEADERS,timeout=TIMEOUT)
    lp=last_page(r.text)
    print(f"  마지막 페이지: {lp}")

    for p in range(1,lp+1):
        params["currentPageNo"]=p
        try:
            r=requests.get(BASE_URL+board["list"],params=params,headers=HEADERS,timeout=TIMEOUT)
            soup=BeautifulSoup(r.text,"html.parser")

            for a in soup.select("a[href^='javascript:fn_DetailInfo']"):
                pid=extract_id(a.get("href",""))
                if not pid or pid in state[board["name"]]:
                    continue

                detail_url=f"{BASE_URL}{board['list'].replace('List','Info')}?{board['param']}={pid}"
                dr=requests.get(detail_url,headers=HEADERS,timeout=TIMEOUT)
                dsoup=BeautifulSoup(dr.text,"html.parser")

                state[board["name"]][pid]={
                    "title":a.get_text(strip=True),
                    "detected_at":datetime.utcnow().isoformat(),
                    "detail_url":detail_url,
                    "attachments":extract_attachments(dsoup)
                }
                updated=True
                print(f"📄 신규 게시물 {pid} / 첨부 {len(state[board['name']][pid]['attachments'])}")

        except Exception as e:
            print("⚠",e)
        time.sleep(1)

if updated:
    save_state(state)

print("\n✅ GitHub 증분 수집 완료")
