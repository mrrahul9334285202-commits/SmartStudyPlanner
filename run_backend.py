
import sys
import subprocess
from pathlib import Path

# Get the project root folder
PROJECT_DIR = Path(__file__).resolve().parent

# Start FastAPI using Uvicorn
command = [
    sys.executable,
    "-m",
    "uvicorn",
    "backend.main:app",
    "--reload",
    "--app-dir",
    str(PROJECT_DIR),
]

print("Starting Smart Study Planner backend...")
print("Project folder:", PROJECT_DIR)
print("API documentation: http://127.0.0.1:8000/docs")

try:
    subprocess.run(command, cwd=PROJECT_DIR, check=True)
except KeyboardInterrupt:
    print("\nSmart Study Planner backend stopped.")
except subprocess.CalledProcessError as error:
    print(f"Backend stopped with error code: {error.returncode}")
