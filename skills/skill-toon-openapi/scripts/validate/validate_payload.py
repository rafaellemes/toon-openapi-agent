import sys
import json
from pathlib import Path
import time
import argparse

# Prefixos de parâmetros que NÃO fazem parte do corpo JSON (path/query/header/cookie/form).
_NON_BODY_PREFIXES = ("p:", "q:", "h:", "c:", "f:")

def parse_params_toon(params_toon):
    """Faz o parse dos tokens do corpo. Ignora params não-body e tolera marcadores (~oneOf...)."""
    parsed = []
    for p in params_toon:
        if ":" not in p or p.startswith(_NON_BODY_PREFIXES):
            continue
        # nome antes do primeiro ':'; o resto é tipo+marcador (ex: "o?~oneOf")
        name_part, type_req = p.split(":", 1)

        prefix = None
        name = name_part
        if name_part == "body":
            prefix, name = "body", ""          # raiz do corpo (ex: body:a!)
        elif name_part.startswith("body."):
            prefix, name = "body", name_part[5:]

        t = type_req[0] if type_req else "s"
        req = len(type_req) > 1 and type_req[1] == "!"

        parsed.append({
            "name": name,
            "prefix": prefix,
            "type": t,
            "required": req,
            "is_body": prefix == "body",
            "token": p,
        })
    return parsed

def _new_node():
    return {"type": None, "required": False, "token": "", "children": {}, "items": None, "wild": None}

def _parse_steps(name):
    """Converte o caminho de um token em passos de navegação.
    Passos: ('field', nome) | ('items',) [array] | ('wild',) [additionalProperties {*}].
    Ex: 'infoAdicionais[].nome' -> field infoAdicionais, items, field nome."""
    steps = []
    if not name:
        return steps
    for part in name.split("."):
        if part == "{*}":
            steps.append(("wild",))
            continue
        base = part
        arrays = 0
        while base.endswith("[]"):
            base = base[:-2]
            arrays += 1
        if base:
            steps.append(("field", base))
        for _ in range(arrays):
            steps.append(("items",))
    return steps

def build_schema_tree(parsed_params):
    """Árvore de schema entendendo objetos aninhados, arrays ([]) e mapas livres ({*})."""
    root = _new_node()
    root["type"] = "o"
    for p in parsed_params:
        if not p["is_body"]:
            continue
        steps = _parse_steps(p["name"])
        node = root
        for i, step in enumerate(steps):
            kind = step[0]
            if kind == "field":
                node = node["children"].setdefault(step[1], _new_node())
            elif kind == "items":
                if node["items"] is None:
                    node["items"] = _new_node()
                node = node["items"]
            elif kind == "wild":
                if node["wild"] is None:
                    node["wild"] = _new_node()
                node = node["wild"]
        node["type"] = p["type"]
        node["required"] = p["required"]
        node["token"] = p["token"]
    return root

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

def validate_constraint(val, c, field, token, errors):
    """Valida ``val`` contra as constraints ``c``. Enum = ERRO, demais = AVISO."""
    import re as _re
    if "enum" in c and val not in c["enum"]:
        errors.append({"field": field, "token": token,
                        "error": f"valor '{val}' não está no enum permitido: {c['enum']}",
                        "severity": "🔴 ERRO"})
    if "minimum" in c and isinstance(val, (int, float)) and val < c["minimum"]:
        errors.append({"field": field, "token": token,
                        "error": f"valor {val} abaixo do mínimo permitido ({c['minimum']})",
                        "severity": "🟡 AVISO"})
    if "maximum" in c and isinstance(val, (int, float)) and val > c["maximum"]:
        errors.append({"field": field, "token": token,
                        "error": f"valor {val} acima do máximo permitido ({c['maximum']})",
                        "severity": "🟡 AVISO"})
    if "minLength" in c and isinstance(val, str) and len(val) < c["minLength"]:
        errors.append({"field": field, "token": token,
                        "error": f"string com {len(val)} chars abaixo do minLength ({c['minLength']})",
                        "severity": "🟡 AVISO"})
    if "maxLength" in c and isinstance(val, str) and len(val) > c["maxLength"]:
        errors.append({"field": field, "token": token,
                        "error": f"string com {len(val)} chars acima do maxLength ({c['maxLength']})",
                        "severity": "🟡 AVISO"})
    if "pattern" in c and isinstance(val, str) and not _re.search(c["pattern"], val):
        errors.append({"field": field, "token": token,
                        "error": f"valor '{val}' não bate com o pattern '{c['pattern']}'",
                        "severity": "🟡 AVISO"})
    if "multipleOf" in c and isinstance(val, (int, float)) and c["multipleOf"] and val % c["multipleOf"] != 0:
        errors.append({"field": field, "token": token,
                        "error": f"valor {val} não é múltiplo de {c['multipleOf']}",
                        "severity": "🟡 AVISO"})

def _is_container(node):
    return bool(node["children"] or node["items"] is not None or node["wild"] is not None)

def _validate(node, value, path, cmap, errors, depth, max_depth):
    """Valida ``value`` contra ``node`` (objeto/array/mapa/leaf), aplicando constraints."""
    t = node.get("type")
    if t and value is not None and not validate_types_strict(value, t):
        errors.append({"field": path or "body", "token": node.get("token", ""),
                        "error": f"tipo incorreto, esperado {t}", "severity": "🔴 ERRO"})
        return

    # Constraints (apenas em valores escalares — objetos/arrays não têm enum/min/etc.)
    tok = node.get("token")
    if tok and tok in cmap and not isinstance(value, (dict, list)):
        validate_constraint(value, cmap[tok], path or "body", tok, errors)

    # Objeto
    if node["children"] and isinstance(value, dict):
        for cname, cnode in node["children"].items():
            sub = f"{path}.{cname}" if path else cname
            if cname not in value:
                if cnode["required"]:
                    errors.append({"field": sub, "token": cnode.get("token", ""),
                                    "error": "campo obrigatório ausente", "severity": "🔴 ERRO"})
                continue
            if _is_container(cnode) and depth + 1 > max_depth:
                errors.append({"field": sub, "token": "", "error": "aninhado além de max_depth",
                                "severity": "⚪ INFO"})
                continue
            _validate(cnode, value[cname], sub, cmap, errors, depth + 1, max_depth)
        for k in value:
            if k not in node["children"]:
                sub = f"{path}.{k}" if path else k
                errors.append({"field": sub, "token": "", "error": "campo extra não no contrato",
                                "severity": "🟡 AVISO"})

    # Array — valida os primeiros itens contra o schema do item
    if node["items"] is not None and isinstance(value, list):
        if depth + 1 > max_depth:
            errors.append({"field": path, "token": "", "error": "array aninhado além de max_depth",
                            "severity": "⚪ INFO"})
        else:
            for idx, el in enumerate(value[:3]):
                _validate(node["items"], el, f"{path}[{idx}]", cmap, errors, depth + 1, max_depth)

    # Mapa livre (additionalProperties)
    if node["wild"] is not None and isinstance(value, dict):
        if depth + 1 <= max_depth:
            for k, v in list(value.items())[:5]:
                sub = f"{path}.{k}" if path else k
                _validate(node["wild"], v, sub, cmap, errors, depth + 1, max_depth)


def validate_payload(entry, payload, max_depth=3):
    parsed = parse_params_toon(entry.get("params_toon", []))
    tree = build_schema_tree(parsed)
    cmap = entry.get("param_constraints", {}) or {}
    errors = []

    has_body = _is_container(tree) or (tree.get("type") not in (None, "o"))
    if isinstance(payload, dict) or (tree.get("type") == "a" and isinstance(payload, list)):
        _validate(tree, payload, "", cmap, errors, 0, max_depth)
    elif has_body:
        errors.append({"field": "body", "token": "", "error": "Payload não é um objeto JSON", "severity": "🔴 ERRO"})

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
