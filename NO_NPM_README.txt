이 패치는 npm install 없이 UI를 실행하기 위한 정적 빌드입니다.

1. 기존 프로젝트 루트에 패치 내용을 덮어씁니다.
2. 데이터가 아직 생성되지 않았다면:
   powershell -ExecutionPolicy Bypass -File ".\scripts\rebuild_data.ps1"
3. UI 실행:
   powershell -ExecutionPolicy Bypass -File ".\scripts\run_static.ps1"

브라우저 주소: http://localhost:5173
종료: PowerShell 창에서 Ctrl+C

새 결과를 source_data에 추가한 뒤에는 아래 하나만 실행해도 됩니다:
   powershell -ExecutionPolicy Bypass -File ".\scripts\rebuild_and_run_static.ps1"
