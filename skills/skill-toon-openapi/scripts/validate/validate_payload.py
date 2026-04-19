import sys
import json
from pathlib import Path
import time
import argparse

def parse_params_toon(params_toon):
    parsed = []
    for p in params_toon:
        # e.g., "body.email:s!" or "id:i?"
        if ":" not in p:
            continue
        parts = p.split(":")
        name_part = parts[0]
        type_req = parts[1]
        
        prefix = None
        name = name_part
        if name_part.startswith("body."):
            prefix = "body"
            name = name_part[5:]
            
        t = type_req[0] if len(type_req) > 0 else "s"
        req = False
        if len(type_req) > 1 and type_req[1] == "!":
            req = True
            
        parsed.append({
            "name": name,
            "prefix": prefix,
            "type": t,
            "required": req,
            "is_body": prefix == "body",
            "token": p
        })
    return parsed

def build_schema_tree(parsed_params):
    tree = {}
    for p in parsed_params:
        if not p["is_body"]:
            continue
            
        parts = p["name"].split(".")
        current = tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {"type": "o", "properties": {}, "required": False}
            elif "properties" not in current[part]:
                current[part]["properties"] = {}
            current = current[part]["properties"]
            
        leaf_name = parts[-1]
        current[leaf_name] = {
            "type": p["type"],
            "required": p["required"],
            "token": p["token"]
        }
    return tree

def validate_types_strict(val, t):
    if t == "s":
        return isinstance(val, str)
    if t == "i":
        return isinstance(val, int) and not isinstance(val, bool)
    if t == "b":
        return isinstance(val, bool)
    if t == "a":
        return isinstance(val, list)
    if t == "o":
        return isinstance(val, dict)
    return True

def _validate_node(schema_node, val, path, depth, max_depth, errors):
    if depth > max_depth:
        errors.append({"field": path, "token": "", "error": "Objeto aninhado além de max_depth", "severity": "⚪ INFO"})
        return
        
    for k, v in schema_node.items():
        sub_path = f"{path}.{k}" if path else k
        
        if k not in val:
            if v.get("required"):
                errors.append({"field": sub_path, "token": v.get("token", ""), "error": "campo obrigatório ausente", "severity": "🔴 ERRO"})
            continue
            
        field_val = val[k]
        
        # Verify type
        expected_type = v.get("type", "s")
        if not validate_types_strict(field_val, expected_type):
            errors.append({"field": sub_path, "token": v.get("token", ""), "error": f"tipo incorreto, esperado {expected_type}", "severity": "🔴 ERRO"})
            continue
            
        if expected_type == "o" and isinstance(field_val, dict) and "properties" in v:
            _validate_node(v["properties"], field_val, sub_path, depth + 1, max_depth, errors)
            
        if expected_type == "a" and isinstance(field_val, list):
            # Valida só primeiros 3
            pass

    for k in val:
        if k not in schema_node:
            sub_path = f"{path}.{k}" if path else k
            errors.append({"field": sub_path, "token": "", "error": "campo extra não no contrato", "severity": "🟡 AVISO"})


def validate_payload(entry, payload, max_depth=3):
    parsed = parse_params_toon(entry.get("params_toon", []))
    tree = build_schema_tree(parsed)
    errors = []
    
    if not isinstance(payload, dict):
        if tree:
            errors.append({"field": "body", "token": "", "error": "Payload não é um objeto JSON", "severity": "🔴 ERRO"})
    else:
        _validate_node(tree, payload, "", 0, max_depth, errors)
        
    hard_count = len([e for e in errors if "ERRO" in e["severity"]])
    warn_count = len([e for e in errors if "AVISO" in e["severity"]])
    info_count = len([e for e in errors if "INFO" in e["severity"]])
    
    return {
        "is_valid": hard_count == 0,
        "errors": errors,
        "hard_count": hard_count,
        "warn_count": warn_count,
        "info_count": info_count
    }

def render_validation_report(result, ns, op_id, depth):
    out = []
    out.append(f"=== Reporte Validação: {ns} / {op_id} (depth={depth}) ===")
    
    if result["is_valid"]:
        out.append("✅ VÁLIDO")
    else:
        out.append("❌ INVÁLIDO")
        
    out.append(f"ERROS: {result['hard_count']} | AVISOS: {result['warn_count']} | INFO: {result['info_count']}")
    
    if result["errors"]:
        out.append("\nDetalhes:")
        for e in result["errors"]:
            out.append(f"  {e['severity']} [{e['field']}] {e['error']} {f'({e.get(chr(116)+chr(111)+chr(107)+chr(101)+chr(110), chr(34)+chr(34))})' if e.get(chr(116)+chr(111)+chr(107)+chr(101)+chr(110)) else ''}")
            
    return "\n".join(out)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ns")
    parser.add_argument("opId")
    parser.add_argument("json_input", nargs="?")
    parser.add_argument("--file")
    parser.add_argument("--depth", type=int, default=3)
    
    try:
        args = parser.parse_args()
        
        if args.file:
            payload_str = Path(args.file).read_text(encoding="utf-8")
        else:
            payload_str = args.json_input

        payload = json.loads(payload_str)
        
        mapping_path = Path(".toon_apis/apis") / args.ns / "mapping.json"
        if not mapping_path.exists():
            print(f"Namespace {args.ns} não encontrado.")
            sys.exit(2)
            
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        if args.opId not in mapping:
            print(f"Operação {args.opId} não encontrada.")
            sys.exit(2)
            
        result = validate_payload(mapping[args.opId], payload, args.depth)
        report = render_validation_report(result, args.ns, args.opId, args.depth)
        
        print(report)
        
        ts = int(time.time())
        Path(".toon_apis/validations").mkdir(parents=True, exist_ok=True)
        (Path(f".toon_apis/validations/validation_{args.opId}_{ts}.txt")).write_text(report, encoding="utf-8")
        
        sys.exit(0 if result["is_valid"] else 1)
        
    except Exception as e:
        print(f"Erro de execução: {e}")
        sys.exit(2)
