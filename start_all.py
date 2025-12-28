import subprocess
import time
import sys
import os

def main():
    """
    Startup script for AURA-PROTO.
    Running this script will launch:
    1. API Server (Port 8000)
    2. User UI (Port 8501)
    3. Staff UI (Port 8502)
    """
    
    # Define commands
    # Using sys.executable to ensure we use the same python environment
    
    # API: Run uvicorn as a module
    # We assume this script is run from the project root
    api_cmd = [sys.executable, "-m", "uvicorn", "api.main:app", "--reload", "--port", "8000"]
    
    # UI Main: Run streamlit
    ui_main_cmd = [sys.executable, "-m", "streamlit", "run", "UI/main.py", "--server.port", "8501"]
    
    # UI Staff: Run streamlit
    ui_staff_cmd = [sys.executable, "-m", "streamlit", "run", "UI/staff.py", "--server.port", "8502"]

    processes = []
    
    print("="*50)
    print("        AURA-PROTO PROTOCOL INITIATED")
    print("="*50)

    try:
        print(f"[1/3] Launching API Server on port 8000...")
        p_api = subprocess.Popen(api_cmd, cwd=os.getcwd())
        processes.append(p_api)
        time.sleep(2) # Give API a moment to start
        
        print(f"[2/3] Launching User UI on port 8501...")
        p_ui = subprocess.Popen(ui_main_cmd, cwd=os.getcwd())
        processes.append(p_ui)
        
        print(f"[3/3] Launching Staff UI on port 8502...")
        p_staff = subprocess.Popen(ui_staff_cmd, cwd=os.getcwd())
        processes.append(p_staff)
        
        print("\nAll services are running!")
        print("API:      http://localhost:8000")
        print("User UI:  http://localhost:8501")
        print("Staff UI: http://localhost:8502")
        print("\nPress Ctrl+C to stop all services.")
        
        while True:
            time.sleep(1)
            # Check if any process has died
            for i, p in enumerate(processes):
                if p.poll() is not None:
                    print(f"\nProcess {i} exited with code {p.returncode}. Shutting down all services...")
                    return

    except KeyboardInterrupt:
        print("\n\nStopping all services...")
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    p.kill()
        print("Services stopped successfully.")

if __name__ == "__main__":
    main()
