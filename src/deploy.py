import subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"

def deploy(mode="test", config=None):
    if mode == "test":
        print("  [TEST] Deploy simulado")
        return True
    remote_path = "/var/www/daily_readings" if not config else config.get("server_path", "/var/www/daily_readings")
    if not OUTPUT_DIR.exists():
        print("  [WARN] No hay output")
        return False
    try:
        subprocess.run(["sudo", "rsync", "-avz", str(OUTPUT_DIR) + "/", remote_path + "/"], check=True, timeout=60)
        subprocess.run(["sudo", "chown", "-R", "deploy:deploy", remote_path], check=True, timeout=10)
        print("  [OK] Sincronizado")
        return True
    except Exception as e:
        print(f"  [WARN] Deploy: {e}")
        return False
