
cd C:\Users\saras\OneDrive\Documents\GitHub\devrunauto
.venv\Scripts\Activate.ps1
Start-Process -NoNewWindow -FilePath "powershell.exe" -ArgumentList "-Command & \"$PSScriptRoot\.venv\Scripts\python.exe\" -u \"$PSScriptRoot\server.py\" *> \"$PSScriptRoot\server_startup.log\"" -PassThru | Out-Null
