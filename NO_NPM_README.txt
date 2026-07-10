This patch provides a static build that can run without `npm install`.

1. Extract the patch contents into the existing project root and overwrite matching files.
2. If the browser data has not been generated yet, run:

   powershell -ExecutionPolicy Bypass -File ".\scripts\rebuild_data.ps1"

3. Start the UI:

   powershell -ExecutionPolicy Bypass -File ".\scripts\run_static.ps1"

Browser URL: http://localhost:5173

To stop the server, press Ctrl+C in the PowerShell window.

After adding new results under `source_data`, you can rebuild the data and restart the UI with:

   powershell -ExecutionPolicy Bypass -File ".\scripts\rebuild_and_run_static.ps1"
