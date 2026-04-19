import sys
import json
import os
from datetime import datetime, timezone
from pathlib import Path

def log_token_usage(namespace, tokens, mode):
    storage_dir = Path(".toon_apis/apis") / namespace
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    metrics_file = storage_dir / "metrics.json"
    
    data = {"total_tokens": 0, "history": []}
    if metrics_file.exists():
        try:
            data = json.loads(metrics_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass # Recover from corruption by overwriting with initial data
            
    try:
        tokens_int = int(tokens)
    except ValueError:
        tokens_int = 0
        
    data["total_tokens"] = data.get("total_tokens", 0) + tokens_int
    data.get("history", []).append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "tokens": tokens_int,
        "namespace": namespace
    })
    
    tmp_file = storage_dir / "metrics.json.tmp"
    tmp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp_file.replace(metrics_file)
    
    return data

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python log_metrics.py <namespace> <tokens> <mode>")
        sys.exit(1)
        
    try:
        log_token_usage(sys.argv[1], int(sys.argv[2]), sys.argv[3])
        print("Métricas registradas com sucesso.")
    except Exception as e:
        print(f"Erro ao registrar métricas: {e}")
        sys.exit(1)
