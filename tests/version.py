"""部署版本验证"""
import subprocess, sys

def get_version():
    try:
        result = subprocess.run(['git','log','--oneline','-1'], capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return "unknown"

if __name__ == "__main__":
    print(f"Version: {get_version()}")
