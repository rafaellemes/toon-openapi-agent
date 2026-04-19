import sys
import json
import requests
import yaml
from pathlib import Path

def load_spec(source):
    try:
        if source.startswith('http://') or source.startswith('https://'):
            resp = requests.get(source, timeout=15)
            resp.raise_for_status()
            content = resp.text
        else:
            p = Path(source).expanduser().resolve()
            if not p.exists():
                return {"error": f"Arquivo não encontrado: {source}"}
            content = p.read_text(encoding="utf-8")
        
        try:
            spec = json.loads(content)
        except json.JSONDecodeError:
            try:
                spec = yaml.safe_load(content)
            except yaml.YAMLError as e:
                return {"error": f"Erro de parse YAML: {e}"}
                
        try:
            from openapi_spec_validator import validate
            validate(spec)
        except Exception as e:
            # Continua mesmo se inválido estrito, mas podemos loggar
            pass
            
        if source.startswith('http'):
            from urllib.parse import urlparse
            parsed_url = urlparse(source)
            base_from_source = f"{parsed_url.scheme}://{parsed_url.netloc}"
            if "servers" in spec and isinstance(spec["servers"], list):
                for srv in spec["servers"]:
                    if "url" in srv and srv["url"].startswith("/"):
                        srv["url"] = f"{base_from_source}{srv['url']}"
                        
        return spec

    except requests.Timeout:
        return {"error": "Timeout ao tentar acessar a URL (limite 15s)."}
    except requests.RequestException as e:
        return {"error": f"Erro HTTP ao acessar a URL: {e}"}
    except Exception as e:
        return {"error": f"Erro inesperado: {str(e)}"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Uso: python parse_spec.py <url_ou_arquivo>"}))
        sys.exit(1)
        
    spec = load_spec(sys.argv[1])
    print(json.dumps(spec, ensure_ascii=False, indent=2))
    if "error" in spec:
        sys.exit(1)
