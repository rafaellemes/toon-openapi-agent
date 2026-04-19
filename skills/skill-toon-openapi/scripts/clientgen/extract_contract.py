import sys
import json
import argparse
from pathlib import Path

def detect_auth(mapping):
    for op in mapping.values():
        if "security" in op and op["security"]:
            return op["security"]
    return {}

def filter_operations(mapping, op_id, tag):
    if op_id:
        if op_id not in mapping:
            raise KeyError(op_id)
        return {op_id: mapping[op_id]}
    if tag:
        tag_lower = tag.lower()
        res = {k: v for k, v in mapping.items() if tag_lower in [x.lower() for x in v.get("tags", [])]}
        if not res:
            raise KeyError(tag)
        return res
    return mapping.copy()

def parse_params(params_toon):
    body = []
    other = []
    
    exp_map = {"s": "string", "i": "integer", "b": "boolean", "a": "array", "o": "object"}
    
    for p in params_toon:
        if ":" not in p:
            continue
        parts = p.split(":")
        name = parts[0]
        treq = parts[1]
        t = treq[0] if len(treq) > 0 else "s"
        req = False
        if len(treq) > 1 and treq[1] == "!":
            req = True
            
        is_body = name.startswith("body.")
        if is_body:
            name = name[5:]
            
        pdict = {
            "name": name,
            "type": exp_map.get(t, "string"),
            "required": req,
            "is_body": is_body
        }
        if is_body:
            body.append(pdict)
        else:
            other.append(pdict)
            
    return body, other

def render_contract(ops, namespace, auth, scope):
    out = []
    out.append(f"CONTRACT: {namespace} | {scope}")
    out.append(f"Total de operações: {len(ops)}")
    
    if auth and auth.get("scheme"):
        scheme_name = auth['scheme']
        if scheme_name.lower() == 'bearer':
            scheme_name = 'Bearer'
        out.append(f"Autenticação: {scheme_name} (header: {auth.get('detail', 'Authorization')})")
    else:
        out.append("Autenticação: não definida (usar placeholder)")
        
    out.append("---")
    
    for op_id, op in ops.items():
        out.append(f"OPERAÇÃO: {op_id}")
        out.append(f"SUMMARY: {op.get('summary')}")
        out.append(f"METHOD: {op.get('method')}")
        out.append(f"URL: {op.get('full_url')}")
        out.append(f"RESPONSES: {', '.join(op.get('responses', []))}")
        
        body, other = parse_params(op.get("params_toon", []))
        if not body and not other:
            out.append("PARAMS: nenhum")
        else:
            out.append("PARAMS:")
            for p in other:
                mark = "[obrigatório]" if p['required'] else "[opcional]"
                out.append(f"  - (path/query) {p['name']}: {p['type']} {mark}")
            for p in body:
                mark = "[obrigatório]" if p['required'] else "[opcional]"
                out.append(f"  - (body) {p['name']}: {p['type']} {mark}")
        out.append("...")
        
    out.append("---")
    out.append("INSTRUÇÕES PARA O LLM:")
    out.append("- Gere código idiomático na linguagem desejada.")
    out.append("- Não invente campos não descritos no contrato.")
    out.append("- [obrigatório] significa que deve ser exigido ou ter valor definido.")
    out.append("- [opcional] deve ter valor padrão nulo/omitido se aplicável.")
    
    return "\n".join(out)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ns")
    parser.add_argument("--operation")
    parser.add_argument("--tag")
    
    try:
        args = parser.parse_args()
        
        mapping_path = Path(".toon_apis/apis") / args.ns / "mapping.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        
        ops = filter_operations(mapping, args.operation, args.tag)
        auth = detect_auth(mapping)
        
        scope = "completo"
        if args.operation: scope = f"operação: {args.operation}"
        if args.tag: scope = f"tag: {args.tag}"
        
        contract = render_contract(ops, args.ns, auth, scope)
        print(contract)
        
    except KeyError as e:
        print(f"Operação ou tag não encontrada: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)
