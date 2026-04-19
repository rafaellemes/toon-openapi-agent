import sys
import json
import argparse
from pathlib import Path
import time

def detect_auth_from_mapping(mapping):
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

def build_export_block(ops, namespace, auth, title, base_url, with_params):
    out = []
    out.append(f"[API: {title} | BASE: {base_url}]")
    
    if auth and auth.get("scheme"):
        out.append(f"AUTH: {auth['scheme']} ({auth.get('detail', '')})")
    else:
        out.append("AUTH: não definida")
        
    out.append("---")
    
    for op_id, op in ops.items():
        m = op.get("method", "GET").upper()
        c = "DEL  " if m == "DELETE" else f"{m: <5}"
        
        tags_str = f" [{', '.join(op.get('tags', []))}]" if op.get("tags") else ""
        out.append(f"{c} {op.get('path')} -> {op_id} | {op.get('summary')}{tags_str}")
        
        if with_params:
            params = op.get("params_toon", [])
            if params:
                out.append(f"  {' '.join(params)}")
                
    out.append("---")
    out.append(f"{len(ops)} operações | Namespace: {namespace}")
    out.append("")
    out.append("[toon-openapi] API mapeada. Você pode pedir:")
    out.append("  → detalhes de endpoint ou código de integração  (ex: \"como chamo esse endpoint?\" / \"gera cliente Go\")")
    out.append("  → cliente HTTP ou SDK — API inteira ou endpoint  (ex: \"gera classe TypeScript completa\" / \"gera só o método POST /orders\")")
    out.append("  → testes de integração                          (ex: \"gera testes pytest para esse endpoint\")")
    out.append("  → validação de payload                          (ex: \"valida esse JSON contra o contrato\")")
    out.append("  → diff com outra versão                         (ex: \"compara com a v2 que acabei de ingerir\")")
    out.append("  → exportar contexto para outra thread           (ex: \"exporta o bloco TooN desta API\")")

    return "\n".join(out)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ns")
    parser.add_argument("--tag")
    parser.add_argument("--operation")
    parser.add_argument("--params", action="store_true")
    parser.add_argument("--save", action="store_true")
    
    try:
        args = parser.parse_args()
        
        ns_path = Path(".toon_apis/apis") / args.ns
        mapping_path = ns_path / "mapping.json"
        toon_path = ns_path / "toon.txt"
        
        if not toon_path.exists():
            print(f"Namespace não encontrado.")
            sys.exit(1)
            
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        toon_lines = toon_path.read_text(encoding="utf-8").splitlines()
        
        title = args.ns
        for l in toon_lines:
            pass # can read from toon or mapping
            
        # Pega a base_url do mapping
        base_url = ""
        if mapping:
            base_url = next(iter(mapping.values())).get("base_url", "")
            
        ops = filter_operations(mapping, args.operation, args.tag)
        auth = detect_auth_from_mapping(mapping)
        
        block = build_export_block(ops, args.ns, auth, args.ns, base_url, args.params)
        print(block)
        
        if args.save:
            scope = "completo"
            if args.tag: scope = f"tag_{args.tag}"
            if args.operation: scope = f"op_{args.operation}"
            ts = int(time.time())
            Path(".toon_apis/exports").mkdir(parents=True, exist_ok=True)
            exp_path = Path(f".toon_apis/exports/{args.ns}_{scope}_{ts}.txt")
            exp_path.write_text(block, encoding="utf-8")
            
    except KeyError as e:
        print(f"Erro: Não encontrado.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)
