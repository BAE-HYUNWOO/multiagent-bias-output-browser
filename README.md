# Multi-Agent Bias Output Browser

BBQ, CBBQ, KoBBQ의 실제 실험 문제와 다음 세 조건의 저장된 output을 탐색하고 다운로드하는 정적 React UI입니다.

- Single Agent
- Multi-Agent Without Revision
- Multi-Agent With Revision

모델을 다시 호출하지 않습니다. `stages.jsonl`, `item_level_results.csv`, 원본 split CSV를 브라우저용 JSON으로 변환해서 표시합니다.

## 1. 기존 데이터 넣는 위치

기존 결과 폴더 전체를 **복사**합니다. 이동하거나 원본을 삭제하지 않습니다.

```text
기존:
C:\Users\samsung-user\Desktop\multiagent_bias_experiment\outputs\runs\split001

복사할 위치:
이 프로젝트\source_data\outputs\split001
```

실제 문제의 context/question/options를 표시하려면 split CSV도 필요합니다.

```text
기존:
C:\Users\samsung-user\Desktop\multiagent_bias_experiment\data\splits\bbq_cbbq_kobbq_pair20_split001.csv

복사할 위치:
이 프로젝트\source_data\splits\bbq_cbbq_kobbq_pair20_split001.csv
```

가장 쉬운 방법은 프로젝트 루트에서 다음 명령을 실행하는 것입니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\import_split001.ps1
```

이 스크립트는 위 두 위치에서 데이터를 자동으로 **복사**합니다.

## 2. UI 데이터 생성

```powershell
.\scripts\rebuild_data.ps1
```

생성되는 주요 폴더:

```text
public\data\
public\downloads\
```

기본 다운로드 ZIP에는 질문, item-level 결과, 9-stage output이 포함됩니다.
`raw_calls.jsonl`까지 포함한 매우 큰 ZIP이 필요하면 다음을 실행합니다.

```powershell
.\scripts\rebuild_data.ps1 -IncludeRawZip
```

대용량 raw ZIP은 GitHub 저장소에 직접 commit하지 않는 것을 권장합니다.

## 3. 처음 한 번 package 설치

```powershell
.\scripts\setup.ps1
```

## 4. 로컬 실행

```powershell
.\scripts\run_local.ps1
```

브라우저에서 일반적으로 다음 주소가 열립니다.

```text
http://localhost:5173
```

## 5. 화면 구조

```text
BBQ / CBBQ / KoBBQ
  └─ Category folders
      └─ Matched pair list
          ├─ Ambiguous / Disambiguated 선택
          ├─ Model 선택
          ├─ Single Agent
          ├─ Multi-Agent Without Revision
          └─ Multi-Agent With Revision
```

문제 하나는 JSON 또는 CSV로 받을 수 있습니다. Category와 Dataset은 ZIP으로 받을 수 있고, 첫 화면에서는 전체 가공 결과 ZIP을 받을 수 있습니다.

## 6. Render 배포

1. UI 데이터 생성 후 `public/data`, `public/downloads`를 포함해서 GitHub에 push합니다.
2. Render에서 **New → Static Site**를 선택합니다.
3. GitHub 저장소를 연결합니다.
4. 설정은 아래와 같습니다.

```text
Build Command: npm ci && npm run build
Publish Directory: dist
```

루트의 `render.yaml`을 사용하는 방식도 가능합니다.

## 7. 다음 split 추가

```text
source_data\outputs\split002
source_data\splits\bbq_cbbq_kobbq_pair20_split002.csv
```

을 추가한 다음 다시 실행합니다.

```powershell
.\scripts\rebuild_data.ps1
```

여러 split이 하나의 UI에 자동으로 합쳐집니다.

## 8. 주요 코드

```text
scripts/build_ui_data.py       원본 결과를 UI JSON/ZIP으로 변환
scripts/validate_ui_data.py    생성된 파일 경로 검사
src/pages/HomePage.tsx         BBQ/CBBQ/KoBBQ 첫 화면
src/pages/DatasetPage.tsx      category 폴더 화면
src/pages/CategoryPage.tsx     문제 목록, 모델/context 필터, 상세 결과
src/components/ConditionViewer.tsx  세 조건의 agent flow 표시
```
