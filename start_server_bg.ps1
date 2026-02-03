$projDir = "C:\Users\saras\OneDrive\Documents\GitHub\devrunauto"
cd $projDir

# Activate virtual environment
. .\.venv\Scripts\Activate.ps1

# Start server in background, redirecting all output to a log file
Start-Process -NoNewWindow -FilePath "powershell.exe" -ArgumentList "-Command & \"$projDir\.venv\Scripts\python.exe\" \"$projDir\server.py\" *> \"$projDir\server_log_port8002.txt\"" -PassThru | Out-Null
