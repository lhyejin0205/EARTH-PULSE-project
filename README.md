# EARTH PULSE — 과제 4 지구 관측 정보판

## 무엇을 기록하나요?
NASA POWER Hourly API에서 서울 지점(37.5665, 126.9780)의 `T2M`(2미터 기온, °C)을 가져와, 각 시간의 UTC 타임스탬프를 `Asia/Seoul`로 변환한 뒤 KST 날짜별 평균을 계산합니다. 이는 원천 API가 제공하는 시간별 자료의 집계값이지, 온도계의 실시간 관측값이나 원시 위성영상이 아닙니다.

- 원천 문서: https://power.larc.nasa.gov/docs/services/api/temporal/hourly/
- API: `https://power.larc.nasa.gov/api/temporal/hourly/point`
- 비밀키: 공개 요청에 API 키를 넣지 않습니다.
- 지리 좌표: 서울, 위도 37.5665 / 경도 126.9780
- 영구 기록: `data/history.json`
- KST 수집: 매일 15:20 KST에 전날 KST 날짜를 집계하도록 예약
- 같은 날짜 재실행: 해당 날짜 레코드를 upsert하여 중복 행을 만들지 않음
- 실패: 수집기는 새 기록 검증에 실패하면 파일을 수정하지 않고 종료합니다. UI의 5개 장애는 합성 테스트이며 실제 관측값/실제 오류가 아닙니다.

## 로컬 실행
Python 3.9+ 권장(ZoneInfo 포함).
```bash
python collector.py
python collector.py --date 2026-10-10
```
`--date`는 테스트나 과거 날짜의 원천 자료 확인에 쓸 수 있습니다. 단, 과제에서 요구하는 “서로 다른 KST 날짜에 실제로 수집한 2건”을 증명하려면 서로 다른 날짜에 워크플로를 실제 실행하고 각 실행 시각을 남기세요. 과거 날짜를 한꺼번에 수집한 것만으로 서로 다른 날에 수집했다고 주장하면 안 됩니다.

## GitHub에 올리고 공개 배포하기
1. GitHub에서 새 **Public** repository를 만듭니다.
2. 이 폴더의 모든 파일과 `.github/workflows/collect.yml`을 업로드/커밋합니다.
3. 저장소의 **Settings → Actions → General → Workflow permissions**에서 `Read and write permissions`를 선택하고 저장합니다. 워크플로 파일에는 `contents: write`가 선언되어 있습니다.
4. **Actions** 탭에서 `Collect NASA POWER daily KST temperature`를 선택하고 `Run workflow`로 실행합니다. 실제 성공 후 `data/history.json`이 변경되었는지 확인합니다.
5. **Settings → Pages → Build and deployment**에서 `Deploy from a branch`, `main`, `/(root)`를 선택합니다.
6. Pages가 배포되면 Settings → Pages의 Visit site 링크를 사용합니다. GitHub Pages는 정적 사이트 호스팅이며 Python은 브라우저에서 실행되지 않으므로, 수집은 Actions에서 수행하고 페이지는 저장된 JSON을 읽습니다.
7. 공개 URL을 시크릿 창에서 열어 로그인 없이 접속되는지 확인합니다.

## 두 날짜의 실제 기록 검증
- 서로 다른 KST 날짜의 수집을 실제로 실행합니다. 매일 예약 실행은 전날의 완료된 KST 날짜를 수집합니다.
- `data/history.json`의 각 행에서 `kst_date`, `value_c`, `unit`, `source_url`, `source_time_standard`, `retrieved_at_kst`, `valid_hours`를 확인합니다.
- `source_url`을 열어 NASA POWER 응답의 시간별 `T2M` 값과 타임스탬프를 확인합니다. 해당 KST 날짜로 변환된 유효 시간별 값의 평균이 `value_c`와 일치해야 합니다.
- 화면의 전일 대비는 최신 두 날짜의 저장된 값에서 직접 재계산합니다: 최신 값 − 이전 값.
- 초기 `history.json`은 의도적으로 빈 상태입니다. 실제 API 실행 전 임의의 숫자를 채우지 않습니다.

## 다섯 가지 합성 장애
화면의 버튼은 외부 지연, HTTP 401/403, HTTP 429, 오프라인, 응답 스키마 변경을 재현합니다. 각 버튼은 별도 안내를 보여주며, `history.json`이나 마지막 정상값은 변경하지 않습니다. `다시 불러오기`는 실제 저장된 기록을 다시 읽습니다.

## 제출에 쓸 확인 방법 (4줄)
1. 공개 Pages URL을 시크릿 창에서 열어 로그인 없이 화면이 표시되는지 확인한다.
2. 원천 링크를 열어 NASA POWER Hourly API 응답의 실제 `T2M` 값과 UTC 타임스탬프를 확인한다.
3. `data/history.json`에서 서로 다른 KST 날짜의 실제 기록 2건과 수집 시각을 확인하고, 시간별 값의 평균 및 전일 대비를 재계산한다.
4. 다섯 합성 장애를 실행해 오류별 안내와 기존 기록 보존을 확인한 뒤 다시 불러오기로 정상 상태를 복구한다.

## AI 활용 및 판단 (3줄)
- AI 제안: 공개 NASA API, KST 변환, 날짜별 영구 저장, 전일 대비 계산과 오류 재현 구조를 설계했다.
- 사용자 판단: 비밀키 없는 원천을 우선하고, 실제로 수집되지 않은 숫자는 기록하지 않으며, 시간대를 명시하기로 했다.
- 따르지 않은 방식: 원천 타임스탬프를 무조건 KST로 간주하거나 샘플 수치를 실제 기록처럼 표시하지 않았다. 시간대 오해와 데이터 조작으로 오해될 수 있기 때문이다.

## 상태
- [x] 프로젝트 파일 작성
- [x] API 수집 코드 및 workflow 작성
- [x] 다크 모드 UI와 5개 합성 장애 작성
- [ ] GitHub 저장소 생성 및 파일 업로드
- [ ] Actions에서 실제 API 수집 성공
- [ ] 서로 다른 날짜에 실제로 수집한 KST 기록 2건 확보
- [ ] GitHub Pages 공개 배포 및 시크릿 창 확인

**저장소 생성, 실 API 실행, 공개 배포는 아직 수행되지 않았습니다.**
