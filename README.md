# 부동산신탁사 재무 대시보드

금융감독원 **금융통계정보시스템(FISIS)** 오픈API에서 부동산신탁사 14개사의 고유계정 재무지표를
받아 **최근 12개 분기**를 차트로 보여주는 웹앱입니다. 서버 없이 GitHub Pages(또는 Cloudflare
Pages)에 무료로 올리고, 휴대폰 홈 화면에 앱처럼 설치할 수 있습니다.

- **업계 비교**: 지표를 고르면 14개사 순위, 12분기 추이(업계 합산평균 강조), 전사 요약표
- **신탁사별**: 핵심 지표 8개 타일(전분기 대비·업계 합산평균·상태 표시), 재무상태·손익·신탁계정대·NCR 차트, 분기별 원자료 표

---

## 0. 어떻게 돌아가나요

```
 ┌───────────── GitHub 저장소 ─────────────┐
 │  index.html  (화면)                      │
 │  data/fisis_data.json  (데이터)  ◀──┐    │
 │  scripts/fetch_fisis.py  (수집)     │    │
 └──────────────┬──────────────────────│───┘
                │                      │ ② 바뀐 데이터만 커밋
                │ ③ 배포               │
                ▼                      │
     GitHub Pages / Cloudflare    GitHub Actions (매주 월 06:07 자동)
     https://아이디.github.io/…    ① FISIS API 호출 (인증키는 Secret에 보관)
                ▲
                │ ④ 휴대폰·PC 브라우저로 열람, 홈 화면에 설치
```

- 브라우저가 FISIS를 직접 부르지 않습니다. **인증키가 화면 코드에 노출되지 않고**, FISIS의 CORS 제한도
  피합니다. 키는 GitHub의 암호화된 Secret에만 저장되고, 수집은 GitHub 서버(Actions)에서 돌아갑니다.
- 분기 업무보고서가 FISIS에 올라오는 날짜가 일정하지 않아 **매주 확인하고, 실제로 바뀐 경우에만** 커밋합니다.
- 인증키 만료나 한도 초과로 빈 응답이 오면 기존 데이터를 지우지 않고 실패로 끝냅니다.

## 1. 폴더 구성

| 경로 | 역할 |
| --- | --- |
| `index.html` | 앱 화면 전체 (차트 라이브러리 Chart.js는 CDN에서 불러옴) |
| `data/fisis_data.json` | 화면이 읽는 데이터. Actions가 자동으로 갱신 |
| `scripts/fetch_fisis.py` | FISIS 수집·지표 계산 스크립트 (파이썬 표준 라이브러리만 사용) |
| `scripts/make_icons.py` | 홈 화면 아이콘 다시 만들기 (Pillow 필요, 평소엔 쓸 일 없음) |
| `.github/workflows/update-and-deploy.yml` | 자동 수집 + GitHub Pages 배포 설정 |
| `manifest.webmanifest`, `sw.js`, `icons/` | 홈 화면 설치용 앱 정보·오프라인 캐시·아이콘 |

> 처음 받은 `data/fisis_data.json`은 **초기 시드 데이터**입니다(2023Q3~2026Q2, 공개 저장소에 수집돼 있던
> FISIS 값을 옮긴 것). 화면 상단에 노란 안내가 보이며, 본인 키로 첫 수집이 끝나면 FISIS 원본으로
> 교체되고 안내도 사라집니다.

---

## 2. 준비물: FISIS 오픈API 인증키

1. <https://fisis.fss.or.kr> 접속 → 상단 메뉴 **오픈API** → **인증키 신청**
2. 이용 목적을 **비영리**로 신청합니다. 비영리 키는 즉시 발급됩니다.
   - ⚠️ **영리 키는 신청한 IP에서만 동작**합니다(`err_cd 021`). GitHub Actions 서버는 매번 IP가 바뀌므로
     영리 키로는 자동 수집이 실패합니다.
3. 발급된 키(긴 영문·숫자 문자열)를 메모장에 복사해 둡니다. **이 키는 어디에도 공개하지 마세요.**

---

## 3. GitHub Pages로 배포하기 (권장)

### 3-1. GitHub 계정과 저장소 만들기

1. <https://github.com> 에서 **Sign up**으로 가입합니다(무료).
2. 로그인 후 오른쪽 위 **＋ → New repository**
3. 입력
   - **Repository name**: `trust-dashboard` (영문, 원하는 이름. 주소에 들어갑니다)
   - **Public** 선택 — 무료 계정은 *공개 저장소*에서만 Pages를 쓸 수 있습니다.
     공개되는 것은 코드와 공개 통계 데이터뿐이고, 인증키는 Secret이라 보이지 않습니다.
   - 나머지는 그대로 두고 **Create repository**

### 3-2. 파일 올리기

압축 파일을 풀면 `trust-dashboard` 폴더가 나옵니다.

**방법 A — 브라우저에서 업로드 (설치 없이)**

1. 새 저장소 화면의 **uploading an existing file** 링크(또는 **Add file → Upload files**)를 누릅니다.
2. 폴더 **안의 내용물**(index.html, data, icons, scripts, manifest.webmanifest, sw.js, README.md …)을
   전부 선택해 끌어다 놓습니다. 폴더째 끌어도 하위 폴더 구조가 유지됩니다.
3. 아래 **Commit changes**를 누릅니다.
4. ⚠️ **`.github` 폴더 확인**: 이름이 점(.)으로 시작하는 폴더는 Windows·macOS에서 숨김이라 빠지기
   쉽습니다. 저장소 첫 화면에 `.github` 폴더가 안 보이면:
   1. **Add file → Create new file**
   2. 파일 이름 칸에 `.github/workflows/update-and-deploy.yml` 을 그대로 입력
      (슬래시를 치면 폴더가 자동으로 만들어집니다)
   3. 압축 파일의 같은 경로 파일을 메모장으로 열어 내용 전체를 붙여넣고 **Commit changes**

**방법 B — GitHub Desktop (앞으로 화면을 자주 고칠 계획이라면)**

1. <https://desktop.github.com> 설치 → 로그인
2. **File → Clone repository** 로 방금 만든 저장소를 PC에 받기
3. 받은 폴더에 압축을 푼 파일을 전부 복사(숨김 폴더 `.github` 포함)
4. 왼쪽 아래 Summary에 `첫 업로드` 입력 → **Commit to main** → 위쪽 **Push origin**

### 3-3. 인증키를 Secret으로 등록

1. 저장소 상단 **Settings** → 왼쪽 **Secrets and variables → Actions**
2. **New repository secret**
   - **Name**: `FISIS_API_KEY` (정확히 이 철자)
   - **Secret**: 발급받은 인증키 붙여넣기
3. **Add secret**

### 3-4. Pages 켜기

1. **Settings → Pages**
2. **Build and deployment → Source** 를 **GitHub Actions** 로 바꿉니다.
   (Deploy from a branch가 아닙니다. 이 프로젝트는 워크플로가 직접 배포합니다.)

### 3-5. 첫 수집·배포 실행

1. 저장소 상단 **Actions** 탭
   - "Workflows aren't being run on this repository" 같은 안내가 나오면 **I understand… enable** 버튼을 누릅니다.
2. 왼쪽 목록에서 **데이터 갱신 및 배포** → 오른쪽 **Run workflow → Run workflow**
3. 2~4분 기다리면 `update`, `deploy` 두 단계가 초록 체크로 바뀝니다.
   - 로그(`update` → FISIS 수집)에 `회사 14곳`, `✓ 한국토지신탁: 17개 분기` 같은 줄이 보이면 정상입니다.
4. 완료 화면의 `deploy` 상자에 나오는 주소, 또는 **Settings → Pages** 상단 주소로 접속합니다.
   - 주소 형식: `https://<GitHub아이디>.github.io/<저장소이름>/`
   - 노란 "초기 데이터" 안내가 사라졌으면 본인 키로 받은 데이터입니다.

이후로는 **매주 월요일 06:07(한국시간)** 자동으로 확인하고, 새 분기가 올라오면 화면도 자동 갱신됩니다.
급할 때는 언제든 Actions 탭에서 **Run workflow**를 누르면 됩니다.

### 3-6. 문제가 생겼을 때

| 증상 (Actions 로그) | 원인과 해결 |
| --- | --- |
| `FISIS_API_KEY 시크릿이 없어 수집을 건너뜁니다` | 3-3을 다시 확인. Name 철자가 정확해야 합니다 |
| `err_cd 010/011/012` | 키가 미등록·중지·삭제 상태. FISIS에서 키 상태 확인 |
| `err_cd 021` | 영리 키를 쓰는 중. 비영리 키로 다시 발급 |
| `err_cd 020` | 하루 호출 한도 초과. 다음 날 다시 실행 (1회 수집에 약 70회 호출) |
| `최신 분기가 후퇴했습니다` / `회사 수가 크게 줄었습니다` | FISIS 점검 등으로 불완전한 응답. 기존 데이터는 그대로이니 나중에 재실행 |
| `deploy` 단계에서 `Get Pages site failed` | 3-4에서 Source를 GitHub Actions로 바꾸지 않음 |
| 주소에 404 | 첫 배포 직후 1~2분 지연. 주소 끝 `/저장소이름/` 철자 확인 |
| 화면은 열리는데 차트가 안 나옴 | 회사 PC처럼 CDN이 막힌 환경. 휴대폰·개인 PC에서 확인 |

---

## 4. Cloudflare Pages로 배포하기 (대안)

GitHub 저장소는 그대로 쓰고, 화면만 Cloudflare가 서비스하는 방식입니다. 데이터 수집은 여전히
GitHub Actions가 하고, 데이터가 커밋될 때마다 Cloudflare가 자동으로 다시 배포합니다.
(Cloudflare 화면 문구는 개편에 따라 조금 다를 수 있습니다.)

1. 3-1 ~ 3-3까지 똑같이 진행합니다(저장소 + Secret). 3-4는 건너뜁니다.
2. <https://dash.cloudflare.com> 가입 → 왼쪽 **Workers & Pages** → **Create** → **Pages** 탭 →
   **Connect to Git** → GitHub 계정 연결 후 저장소 선택
3. 빌드 설정
   - **Framework preset**: `None`
   - **Build command**: 비워 둠
   - **Build output directory**: 비워 두거나 `/` (저장소 최상위 폴더가 곧 사이트)
4. **Save and Deploy** → 1분 뒤 `https://<프로젝트이름>.pages.dev` 주소가 생깁니다.
5. GitHub Pages 배포 단계를 끕니다: GitHub 저장소 **Settings → Secrets and variables → Actions →
   Variables 탭 → New repository variable** 에서 Name `DEPLOY_TARGET`, Value `cloudflare`.
   (그대로 두면 Pages가 꺼져 있어 `deploy` 단계가 매번 빨간불로 끝납니다.)
6. Actions에서 **Run workflow**로 첫 수집을 실행합니다. 수집 결과가 커밋되면 Cloudflare가 알아서 재배포합니다.

| | GitHub Pages | Cloudflare Pages |
| --- | --- | --- |
| 가입 | GitHub만 | GitHub + Cloudflare |
| 주소 | `아이디.github.io/저장소` | `이름.pages.dev` |
| 비공개 저장소 | 유료 플랜 필요 | 무료로 가능 |
| 국내 접속 속도 | 보통 | 대체로 빠름 |

---

## 5. 휴대폰 홈 화면에 설치

- **iPhone (Safari)**: 배포 주소 열기 → 아래 **공유** 버튼 → **홈 화면에 추가** → 추가
- **Android (Chrome)**: 배포 주소 열기 → 오른쪽 위 **⋮** → **홈 화면에 추가** 또는 **앱 설치**

전용 아이콘으로 설치되고 주소창 없이 열립니다. 한 번 열어 본 데이터는 저장돼 있어
인터넷이 끊겨도 마지막 화면을 볼 수 있습니다.

---

## 6. PC에서 미리 보기

`index.html`을 더블클릭하면 브라우저 보안 정책 때문에 데이터 파일을 못 읽습니다. 폴더에서 아래를 실행하세요.

```bash
python -m http.server 8000
# 브라우저에서 http://localhost:8000
```

수집도 PC에서 직접 돌려볼 수 있습니다(인터넷 연결 필요).

```bash
# macOS / Linux
FISIS_API_KEY=발급키 python scripts/fetch_fisis.py
# Windows PowerShell
$env:FISIS_API_KEY="발급키"; python scripts/fetch_fisis.py
```

---

## 7. 데이터와 지표

**사용 통계표** (권역 `partDiv=M` 부동산신탁, 분기 `term=Q`)

| 통계표 | 이름 | 사용 항목 |
| --- | --- | --- |
| SM005 | 요약재무상태표(고유계정) | 자산총계, 현금및예치금, 신탁계정대, 신탁계정대 대손충당금, 부채총계, 차입부채, 자본총계, 자본금 |
| SM007 | 요약손익계산서(고유계정) | 영업수익, 신탁보수, 영업이익, 당기순이익 |
| SM009 | 자본적정성 | 영업용순자본, 총위험액, 영업용순자본비율(NCR) |
| SM013 | 자산건전성 | 고정이하자산, 분류대상자산, 고정이하자산비율 |
| SM016 | 자산건전성 분류 | 신탁계정대의 정상·요주의·고정·회수의문·추정손실 |

**계산 지표** (금액 억원, 비율 %)

| 지표 | 산식 |
| --- | --- |
| 신탁계정대/자기자본 | 신탁계정대 ÷ 자본총계 |
| 신탁계정대 고정이하비율 | (고정+회수의문+추정손실) ÷ 분류 합계 |
| 충당금적립률 | 신탁계정대 대손충당금 ÷ 신탁계정대 |
| 부채비율 | 부채총계 ÷ 자본총계 |
| 순차입금의존도 | (차입부채 − 현금및예치금) ÷ 자산총계 |
| ROA·ROE(최근 4분기) | 최근 4개 분기 순이익 합계 ÷ 기말 자산·자본 |
| 신탁보수 비중 | 최근 4개 분기 신탁보수 ÷ 영업수익 |

- **업계 평균은 합산평균**입니다. 비율 지표는 14개사의 분자 합계 ÷ 분모 합계로 계산해 규모가 큰 회사의 비중이
  반영됩니다(예: 업계 NCR = 영업용순자본 합계 ÷ 총위험액 합계). 금액 지표는 회사당 평균입니다.
- FISIS의 분기 손익은 **해당 분기 단독 금액**입니다(누적 아님). 그래서 연환산 대신 최근 4분기 합계를 씁니다.
- 일부 회사만 먼저 올라온 분기(과반 미만)는 미완성으로 보고 화면에서 뺍니다.
- 화면의 양호·주의·경계 표시는 **참고용 임의 기준**입니다(NCR 150%만 규제선). 기준은
  `index.html`의 `const M = {…}` 안 `st:` 줄에서 바꿀 수 있습니다.

**지표를 더 넣고 싶다면**: `scripts/fetch_fisis.py`의 `TABLES`에 `(필드명, 계정코드, 계정명)`을 한 줄
추가하고, `index.html`의 `M`과 `RAW_ROWS`에 같은 필드명을 넣으면 됩니다. 통계표·계정코드는
FISIS 오픈API의 `statisticsListSearch`(lrgDiv=M), `accountListSearch`(listNo=SM005 등)로 확인합니다.

---

출처: 금융감독원 금융통계정보시스템. 업무보고서 기반 자료로 국가승인통계가 아니며 회사 공시와 다를 수 있습니다.
