import os
import subprocess
import time

def kill_conflicting_instances(script_name='sidecar.py'):
    """Finds and kills other running instances of the specified script using PowerShell."""
    current_pid = os.getpid()
    print(f"[debug] Current PID: {current_pid}")
    try:
        # PowerShell command to find python processes running the script
        ps_cmd = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*" + script_name + "*' } | "
            "Select-Object -ExpandProperty ProcessId"
        )
        
        creation_flags = 0x08000000 if os.name == 'nt' else 0
        output = subprocess.check_output(
            ["powershell", "-Command", ps_cmd], 
            creationflags=creation_flags
        )
        
        pids = [int(p) for p in output.decode().split() if p.strip().isdigit()]
        killed_any = False
        for pid in pids:
            if pid != current_pid:
                print(f"[i] Terminating conflicting instance (PID: {pid})...")
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                killed_any = True
        
        if killed_any:
            print("[i] Cleanup complete. Waiting 1s for release...")
            time.sleep(1)
            
    except Exception as e:
        print(f"[!] Warning: Failed to cleanup instances: {e}")
