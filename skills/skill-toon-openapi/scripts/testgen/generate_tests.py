import sys
import json
from pathlib import Path
import time

GENERATORS = {}
EXTENSIONS = {"python": "py", "javascript": "js", "typescript": "ts", "kotlin": "kt", "go": "go", "ruby": "rb"}
DEFAULT_FRAMEWORKS = {"python": "pytest", "javascript": "jest", "typescript": "jest", "kotlin": "junit5", "go": "testing", "ruby": "rspec"}

def build_happy_payload(params_toon):
    payload = {}
    for p in params_toon:
        if not p.startswith("body."):
            continue
        parts = p.split(":")
        name = parts[0][5:]
        t = parts[1][0] if len(parts)>1 and len(parts[1])>0 else "s"
        
        # very simple mock
        if t == "s": val = "string"
        elif t == "i": val = 1
        elif t == "b": val = True
        elif t == "a": val = []
        elif t == "o": val = {}
        else: val = "str"
        
        # simple dot path for dict
        keys = name.split(".")
        cur = payload
        for k in keys[:-1]:
            if k not in cur:
                cur[k] = {}
            cur = cur[k]
        cur[keys[-1]] = val
        
    return payload

def build_missing_required_payload(params_toon):
    p = build_happy_payload(params_toon)
    missing_name = None
    
    # acha primeiro obrigatorio
    for param in params_toon:
        if param.startswith("body.") and param.endswith("!"):
            missing_name = param.split(":")[0][5:]
            break
            
    if missing_name:
        keys = missing_name.split(".")
        cur = p
        for k in keys[:-1]:
            cur = cur[k]
        if keys[-1] in cur:
            del cur[keys[-1]]
            
    return p, missing_name

def gen_python(entry, op_id, framework):
    happy = build_happy_payload(entry["params_toon"])
    missing, miss_name = build_missing_required_payload(entry["params_toon"])
    url = entry.get("full_url", "")
    code = f"import requests\n\ndef test_{op_id}_happy():\n    url = '{url}'\n    payload = {json.dumps(happy)}\n    resp = requests.{entry['method'].lower()}(url, json=payload)\n    assert resp.status_code == 200\n"
    if miss_name:
        code += f"\ndef test_{op_id}_missing_req():\n    url = '{url}'\n    payload = {json.dumps(missing)}\n    resp = requests.{entry['method'].lower()}(url, json=payload)\n    # campo obrigatório ausente, erro esperado\n    assert resp.status_code == 400\n"
    if "404" in entry.get("responses", []):
        code += f"\ndef test_{op_id}_not_found():\n    url = '{url}'\n    resp = requests.{entry['method'].lower()}(url)\n    assert resp.status_code == 404\n"
    return code

def gen_javascript(entry, op_id, framework):
    return "describe('test', () => { it('fetch test', () => {}); });"

def gen_kotlin(entry, op_id, framework):
    return "@Test suspend fun test() {}"

def gen_go(entry, op_id, framework):
    return "func Test(t *testing.T) {}"

def gen_ruby(entry, op_id, framework):
    return "RSpec.describe 'test' do end"

GENERATORS["python"] = gen_python
GENERATORS["javascript"] = gen_javascript
GENERATORS["typescript"] = gen_javascript
GENERATORS["kotlin"] = gen_kotlin
GENERATORS["go"] = gen_go
GENERATORS["ruby"] = gen_ruby


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python generate_tests.py <ns> <opId> <lang> [framework]")
        sys.exit(1)
        
    ns = sys.argv[1]
    op_id = sys.argv[2]
    lang = sys.argv[3].lower()
    fw = sys.argv[4] if len(sys.argv) > 4 else DEFAULT_FRAMEWORKS.get(lang, "")
    
    try:
        mapping = json.loads((Path(".toon_apis/apis") / ns / "mapping.json").read_text())
        if op_id not in mapping:
            print("Operação não encontrada.")
            sys.exit(1)
            
        entry = mapping[op_id]
        generator = GENERATORS.get(lang)
        if not generator:
            print(f"Linguagem {lang} não suportada.")
            sys.exit(1)
            
        code = generator(entry, op_id, fw)
        print(code)
        
        ts = int(time.time())
        ext = EXTENSIONS.get(lang, "txt")
        Path(".toon_apis/tests").mkdir(parents=True, exist_ok=True)
        (Path(".toon_apis/tests") / f"{ns}_{op_id}_{lang}_{ts}.{ext}").write_text(code, encoding="utf-8")
        
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)
