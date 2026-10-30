#!/usr/bin/env python3
"""금융통계정보시스템(FISIS) Open API → data/fisis_data.json

부동산신탁 권역(partDiv=M) 전 회사의 고유계정 재무지표를 최근 12개 분기로 수집합니다.
표준 라이브러리만 사용하므로 pip install 이 필요 없습니다.

  환경변수
    FISIS_API_KEY   (필수) FISIS 오픈API 인증키
    FISIS_END_MM    (선택) 조회 종료월 YYYYMM. 비우면 실행 시점 직전 분기말
    QUARTERS        (선택) 화면에 남길 분기 수, 기본 12

  실행
    FISIS_API_KEY=발급키 python scripts/fetch_fisis.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "fisis_data.json"

API = "https://fisis.fss.or.kr/openapi/{op}.json"
# 기본 파이썬 User-Agent 로 호출하면 FISIS가 503을 돌려줍니다.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
DELAY = 0.3          # 호출 간격(초)
SECTOR = "M"         # 부동산신탁

KEEP = int(os.environ.get("QUARTERS", "12"))
FETCH = KEEP + 3 + 2  # 표시 12 + TTM 계산용 3 + 공시 지연 여유 2

# ── 수집할 통계표와 계정 ──────────────────────────────────────────────
# (필드명, 계정코드, 계정명 키워드)  ― 코드가 안 맞으면 계정명으로 한 번 더 찾습니다.
TABLES = {
    "SM005": [  # 요약재무상태표(고유계정)
        ("total_assets", "A", "자산총계"),
        ("cash", "A1", "현금및예치금"),
        ("trust_loan", "A45", "신탁계정대"),
        ("trust_loan_allow", "A472", "신탁계정대대손충당금"),
        ("total_liab", "B", "부채총계"),
        ("borrowings", "B2", "차입부채"),
        ("total_equity", "C", "자본총계"),
        ("capital_stock", "C1", "자본금"),
    ],
    "SM007": [  # 요약손익계산서(고유계정) ― 분기 단독 금액
        ("op_revenue", "A", "영업수익"),
        ("trust_fee", "A11", "신탁보수"),
        ("op_income", "C", "영업이익"),
        ("net_income", "G", "당기순이익"),
    ],
    "SM009": [  # 자본적정성
        ("nop_capital", "A", "영업용순자본"),
        ("total_risk", "B", "총위험액"),
        ("ncr", "C", "영업용순자본비율"),
    ],
    "SM013": [  # 고정이하자산비율
        ("npl", "A", "고정이하자산"),
        ("classified", "B", "분류대상자산"),
        ("npl_ratio", "C", "고정이하자산비율"),
    ],
}
SM016_ACCOUNT = "K"  # 자산건전성 분류표의 '신탁계정대' 행 (a~e = 정상~추정손실)
RATIO_FIELDS = {"ncr", "npl_ratio"}


# ── API 호출 ─────────────────────────────────────────────────────────
class FisisError(RuntimeError):
    def __init__(self, msg: str, fatal: bool = False):
        super().__init__(msg)
        self.fatal = fatal  # 인증키·한도 문제처럼 계속해도 소용없는 오류


def call(op: str, **params: str) -> dict:
    key = os.environ.get("FISIS_API_KEY", "").strip()
    if not key:
        raise FisisError("FISIS_API_KEY 환경변수가 비어 있습니다.")
    q = urllib.parse.urlencode({"auth": key, "lang": "kr", **params})
    req = urllib.request.Request(f"{API.format(op=op)}?{q}", headers={"User-Agent": UA})
    last = None
    for attempt in range(3):
        time.sleep(DELAY)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = f"{type(e).__name__}"          # 키가 담긴 URL은 로그에 남기지 않음
            time.sleep(1.5 * (attempt + 1))
            continue
        res = body.get("result", body)
        code = str(res.get("err_cd", "000"))
        if code == "000":
            return res
        if code == "900":                        # FISIS 내부 오류 → 재시도
            last = f"err_cd 900 {res.get('err_msg', '')}"
            time.sleep(1.5 * (attempt + 1))
            continue
        hint = {
            "010": "미등록 인증키", "011": "중지된 인증키", "012": "삭제된 인증키",
            "020": "일일 호출 한도 초과", "021": "허용되지 않은 IP(영리 키는 신청 IP에서만 동작)",
            "103": "조회기간 40분기 초과",
        }.get(code, "")
        raise FisisError(f"FISIS err_cd {code} {res.get('err_msg', '')} {hint}".strip(),
                         fatal=code in {"010", "011", "012", "013", "020", "021"})
    raise FisisError(f"FISIS 호출 실패: {last}")


def rows(res: dict) -> list[dict]:
    v = res.get("list")
    if v is None:
        return []
    return [v] if isinstance(v, dict) else list(v)


def legend(res: dict) -> tuple[list[str], list[str]]:
    """값 컬럼 id 목록과 단위 목록 (a,b,c… / 백만원,% …)."""
    desc = res.get("description") or []
    if isinstance(desc, dict):
        desc = desc.get("column", [desc])
    if isinstance(desc, dict):
        desc = [desc]
    ids = [d.get("column_id") for d in desc if d.get("column_id")]
    units = [u.strip() for u in str(res.get("unit") or "").split(",")]
    if len(units) != len(ids):
        units = [units[0] if units and units[0] else ""] * len(ids)
    return ids, units


MONEY_DIV = {"원": 1e8, "천원": 1e5, "백만원": 100, "십억원": 0.1, "억원": 1}


def num(value):
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def to_eok(x, unit: str):
    """금액을 억원으로. 단위가 금액 단위가 아니면 FISIS 기본 단위(백만원)로 봅니다."""
    if x is None:
        return None
    return x / MONEY_DIV.get(unit, 100)


# ── 기간 계산 ─────────────────────────────────────────────────────────
def qlabel(ym: str) -> str:
    return f"{ym[:4]}Q{(int(ym[4:]) - 1) // 3 + 1}"


def quarter_window() -> tuple[str, str]:
    end = os.environ.get("FISIS_END_MM", "").strip()
    if not end:
        t = dt.date.today()
        q = (t.month - 1) // 3          # 0~3, 직전 분기말
        y, m = (t.year - 1, 12) if q == 0 else (t.year, q * 3)
        end = f"{y}{m:02d}"
    y, m = int(end[:4]), int(end[4:])
    idx = y * 4 + (m - 1) // 3 - (FETCH - 1)
    start = f"{idx // 4}{(idx % 4) * 3 + 3:02d}"
    return start, end


# ── 수집 ──────────────────────────────────────────────────────────────
def companies() -> list[dict]:
    out = []
    for r in rows(call("companySearch", partDiv=SECTOR)):
        name = (r.get("finance_nm") or "").strip()
        if "[폐]" in name or "폐업" in name:
            continue
        out.append({"code": r["finance_cd"], "name": name})
    out.sort(key=lambda c: c["name"])
    return out


def fetch_table(fcd: str, list_no: str, start: str, end: str) -> list[dict]:
    res = call("statisticsInfoSearch", financeCd=fcd, listNo=list_no,
               term="Q", startBaseMm=start, endBaseMm=end)
    ids, units = legend(res)
    out = []
    for r in rows(res):
        out.append({"ym": str(r.get("base_month")), "cd": str(r.get("account_cd") or ""),
                    "nm": str(r.get("account_nm") or "").replace(" ", ""),
                    "ids": ids, "units": units,
                    "v": {cid: num(r.get(cid)) for cid in [*ids, *"abcdef"]}})
    return out


def pick(table_rows: list[dict], code: str, kw: str, ratio: bool) -> dict[str, float]:
    """계정코드(우선) 또는 계정명으로 분기별 첫 값 컬럼을 뽑습니다. 금액은 억원 환산."""
    hit = [r for r in table_rows if r["cd"] == code] or \
          [r for r in table_rows if r["nm"] == kw] or \
          [r for r in table_rows if kw in r["nm"]]
    by_q = {}
    for r in hit:
        if not r["ids"]:
            continue
        val = r["v"].get(r["ids"][0])
        if val is not None and not ratio:
            val = to_eok(val, r["units"][0])
        if val is not None and qlabel(r["ym"]) not in by_q:
            by_q[qlabel(r["ym"])] = val
    return by_q


def collect() -> dict:
    start, end = quarter_window()
    print(f"조회 구간: {start} ~ {end} ({FETCH}분기)")
    comps = companies()
    print(f"회사 {len(comps)}곳: " + ", ".join(c["name"] for c in comps))
    data: dict[str, dict[str, dict]] = {}
    for c in comps:
        series: dict[str, dict] = {}
        for list_no, fields in TABLES.items():
            try:
                tr = fetch_table(c["code"], list_no, start, end)
            except FisisError as e:
                if e.fatal:
                    raise                                   # 인증·한도 오류는 즉시 중단
                print(f"  ! {c['name']} {list_no}: {e}")
                continue
            for field, code, kw in fields:
                for q, val in pick(tr, code, kw, field in RATIO_FIELDS).items():
                    series.setdefault(q, {})[field] = round(val, 2 if field in RATIO_FIELDS else 1)
        # 신탁계정대 건전성 분류(정상·요주의·고정·회수의문·추정손실)
        try:
            tr = fetch_table(c["code"], "SM016", start, end)
            # 계정코드 K(신탁계정대) 행만 사용. 없을 때만 계정명이 정확히 '신탁계정대'인 행.
            hit = [r for r in tr if r["cd"] == SM016_ACCOUNT] or [r for r in tr if r["nm"] == "신탁계정대"]
            for r in hit:
                unit = dict(zip(r["ids"], r["units"])).get("a", "")
                # 값 컬럼 a~e = 정상·요주의·고정·회수의문·추정손실
                v = [to_eok(r["v"].get(col) or 0, unit) for col in "abcde"]
                if sum(v) > 0:
                    s = series.setdefault(qlabel(r["ym"]), {})
                    s["tal_class"] = [round(x, 1) for x in v]
        except FisisError as e:
            if e.fatal:
                raise
            print(f"  ! {c['name']} SM016: {e}")
        data[c["code"]] = series
        print(f"  ✓ {c['name']}: {len(series)}개 분기")
    return {"companies": comps, "raw": data}


# ── 지표 계산 ─────────────────────────────────────────────────────────
def pct(a, b, nd=2):
    if a is None or b in (None, 0):
        return None
    return round(a / b * 100, nd)


def prev_q(q: str, n: int) -> str:
    y, k = int(q[:4]), int(q[5])
    i = y * 4 + k - 1 - n
    return f"{i // 4}Q{i % 4 + 1}"


def derive(raw: dict[str, dict]) -> None:
    for q, d in raw.items():
        ttm = {}
        for f in ("net_income", "op_revenue", "trust_fee", "op_income"):
            seq = [raw.get(prev_q(q, n), {}).get(f) for n in range(4)]
            ttm[f] = round(sum(seq), 1) if all(x is not None for x in seq) else None
            d[f + "_ttm"] = ttm[f]
        cls = d.get("tal_class")
        if cls:
            d["tal_npl"] = round(sum(cls[2:]), 1)
            d["tal_classified"] = round(sum(cls), 1)   # 합산평균 분모
            d["tal_npl_ratio"] = pct(sum(cls[2:]), sum(cls))
        d["debt_ratio"] = pct(d.get("total_liab"), d.get("total_equity"))
        d["tal_to_equity"] = pct(d.get("trust_loan"), d.get("total_equity"))
        d["allow_cover"] = pct(abs(d["trust_loan_allow"]) if d.get("trust_loan_allow") is not None else None,
                               d.get("trust_loan"))
        d["borrow_dep"] = pct(d.get("borrowings"), d.get("total_assets"))
        if d.get("borrowings") is not None and d.get("cash") is not None:
            d["net_borrow_dep"] = pct(d["borrowings"] - d["cash"], d.get("total_assets"))
        d["roa_ttm"] = pct(ttm["net_income"], d.get("total_assets"))
        d["roe_ttm"] = pct(ttm["net_income"], d.get("total_equity"))
        d["fee_share_ttm"] = pct(ttm["trust_fee"], ttm["op_revenue"], 1)
        d["op_margin_ttm"] = pct(ttm["op_income"], ttm["op_revenue"], 1)


def build(col: dict) -> dict:
    comps, raw = col["companies"], col["raw"]
    for s in raw.values():
        derive(s)
    all_q = sorted({q for s in raw.values() for q in s})
    # 일부 회사만 먼저 올라온 미완성 분기 제외 (자산총계 수집 회사가 과반 미달)
    done = []
    for q in all_q:
        n = sum(1 for s in raw.values() if s.get(q, {}).get("total_assets") is not None)
        if n * 2 > len(comps):
            done.append(q)
        else:
            print(f"분기 {q} 제외: {n}/{len(comps)}개사만 수집됨")
    quarters = done[-KEEP:]
    series = {c: {q: raw[c][q] for q in quarters if q in raw[c]} for c in raw}
    return {
        "meta": {
            "source": "금융감독원 금융통계정보시스템(FISIS) 오픈API",
            "tables": ["SM005", "SM007", "SM009", "SM013", "SM016"],
            "basis": "고유계정 기준 · 금액 억원 · 비율 %",
            "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds"),
            "latest": quarters[-1] if quarters else None,
            "seed": False,
        },
        "quarters": quarters,
        "companies": comps,
        "series": series,
    }


def guard(new: dict) -> None:
    """빈 응답·한도 초과로 정상 데이터를 덮어쓰는 사고를 막습니다."""
    if not new["quarters"]:
        raise SystemExit("수집된 분기가 없습니다. 기존 파일을 유지합니다.")
    if not OUT.exists():
        return
    old = json.loads(OUT.read_text(encoding="utf-8"))
    if old.get("meta", {}).get("seed"):
        return
    if (old.get("meta", {}).get("latest") or "") > new["meta"]["latest"]:
        raise SystemExit(f"최신 분기가 후퇴했습니다({old['meta']['latest']} → {new['meta']['latest']}).")
    if len(new["companies"]) < len(old.get("companies", [])) - 2:
        raise SystemExit("회사 수가 크게 줄었습니다. 기존 파일을 유지합니다.")


def main() -> None:
    try:
        new = build(collect())
    except FisisError as e:
        raise SystemExit(f"중단: {e}")
    guard(new)
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        strip = lambda d: {k: v for k, v in d.items() if k != "meta"} | {"latest": d["meta"].get("latest")}
        if strip(old) == strip(new) and not old["meta"].get("seed"):
            print("변경 없음 — 파일을 다시 쓰지 않습니다.")
            return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(new, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"저장: data/{OUT.name} · {new['quarters'][0]}~{new['meta']['latest']} · {len(new['companies'])}개사")


if __name__ == "__main__":
    main()
