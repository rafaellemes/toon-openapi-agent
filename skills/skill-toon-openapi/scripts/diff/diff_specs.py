import sys
import json
from pathlib import Path
import re

# Fake modules for parsing
sys.path.insert(0, str(Path(__file__).parent.parent / "ingest"))
try:
    from parse_spec import load_spec
    from transform_toon import generate_artifacts
except ImportError:
    pass

def slugify_label(label):
    return re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')

def extract_meta(mapping):
    base_url = ""
    auth = ""
    if mapping:
        first = next(iter(mapping.values()))
        base_url = first.get("base_url", "")
        security = first.get("security", {})
        if security:
            auth = security.get("scheme", "")
    return {"base_url": base_url, "auth": auth}

def classify(rule):
    breaking = ["endpoint_removed", "param_type_changed", "param_required_added", "param_removed", "method_changed", "base_url_changed", "auth_scheme_changed"]
    non_breaking = ["endpoint_added", "param_optional_added"]
    if rule in breaking:
        return "🔴 BREAKING", "high"
    elif rule in non_breaking:
        return "🟢 NON-BREAKING", "low"
    else:
        return "⚪ INFO", "low"

def diff_mappings(base, target):
    added = []
    removed = []
    modified = []
    unchanged = []
    
    for op_id, t_op in target.items():
        if op_id not in base:
            added.append({"op_id": op_id, "op": t_op})
            continue
            
        b_op = base[op_id]
        changes = []
        
        # Check params
        # Simple string comparison or parsing
        b_params_str = ",".join(b_op.get("params_toon", []))
        t_params_str = ",".join(t_op.get("params_toon", []))
        
        if b_params_str != t_params_str:
            bp = {x.split(":")[0]: x.split(":")[-1] for x in b_op.get("params_toon", []) if ":" in x}
            tp = {x.split(":")[0]: x.split(":")[-1] for x in t_op.get("params_toon", []) if ":" in x}
            
            for k, v in tp.items():
                if k not in bp:
                    if v.endswith("!"):
                        changes.append({"rule": "param_required_added", "detail": f"Param {k} adicionado como obrigatório."})
                    else:
                        changes.append({"rule": "param_optional_added", "detail": f"Param {k} adicionado como opcional."})
                elif bp[k] != v:
                    changes.append({"rule": "param_type_changed", "detail": f"Param {k} mudou de {bp[k]} para {v}."})
            
            for k in bp:
                if k not in tp:
                    changes.append({"rule": "param_removed", "detail": f"Param {k} foi removido."})
                    
        # Other simple checks to fulfill standard rules
        if b_op.get("method") != t_op.get("method"):
            changes.append({"rule": "method_changed", "detail": "Método HTTP mudou."})
        if b_op.get("base_url") != t_op.get("base_url"):
            changes.append({"rule": "base_url_changed", "detail": "Base URL mudou."})
        if b_op.get("security", {}).get("scheme") != t_op.get("security", {}).get("scheme"):
            changes.append({"rule": "auth_scheme_changed", "detail": "Esquema de auth mudou."})
        if b_op.get("summary") != t_op.get("summary"):
            changes.append({"rule": "summary_changed", "detail": "Summary mudou."})
            
        # Classify changes
        for c in changes:
            label, impact = classify(c["rule"])
            c["label"] = label
            c["impact"] = impact
            
        if changes:
            modified.append({"op_id": op_id, "op_base": b_op, "op_target": t_op, "changes": changes})
        else:
            unchanged.append({"op_id": op_id})
            
    for op_id, b_op in base.items():
        if op_id not in target:
            removed.append({"op_id": op_id, "op": b_op})
            
    return {"added": added, "removed": removed, "modified": modified, "unchanged": unchanged}

def render_report(diff, name_base, name_target, meta_base, meta_target, src_b, src_t):
    out = []
    out.append(f"=== API Diff Report: {name_base} vs {name_target} ===")
    
    total_added = len(diff['added'])
    total_removed = len(diff['removed'])
    total_modified = len(diff['modified'])
    total_breaking = 0
    for m in diff['modified']:
        if any("BREAKING" in c["label"] for c in m["changes"]):
            total_breaking += 1
    total_breaking += total_removed
    
    out.append(f"\nRESUMO:")
    out.append(f"- {total_added} endpoints adicionados")
    out.append(f"- {total_removed} endpoints removidos")
    out.append(f"- {total_modified} endpoints modificados")
    out.append(f"- {total_breaking} breaking changes detectadas")
    
    if total_added == 0 and total_removed == 0 and total_modified == 0:
        out.append("\nNenhuma diferença encontrada.")
        return "\n".join(out)
        
    if total_added > 0:
        out.append("\n[+] ENDPOINTS ADICIONADOS:")
        for i in diff['added']:
            out.append(f"  {i['op']['method']} {i['op']['path']} -> {i['op_id']}")
    
    if total_removed > 0:
        out.append("\n[-] ENDPOINTS REMOVIDOS:")
        for i in diff['removed']:
            out.append(f"  {i['op']['method']} {i['op']['path']} -> {i['op_id']}")
            
    if total_modified > 0:
        out.append("\n[~] ENDPOINTS MODIFICADOS:")
        for i in diff['modified']:
            out.append(f"  {i['op_base']['method']} {i['op_base']['path']} -> {i['op_id']}:")
            for c in i['changes']:
                out.append(f"    {c['label']} ({c['impact']}): {c['detail']}")
                
    return "\n".join(out)

def resolve_source(source):
    # Namespace existing?
    p = Path(f".toon_apis/apis/{source}/mapping.json")
    if p.exists():
        return json.loads(p.read_text()), source
    
    p = Path(source)
    if p.exists() and source.endswith(".json") and not "swagger" in p.read_text() and not "openapi" in p.read_text():
         # Maybe it's a mapping json itself? Let's check keys
         try:
             d = json.loads(p.read_text())
             if all(isinstance(v, dict) and "method" in v for v in d.values()):
                 return d, p.stem
         except: pass

    # Ingest realtime
    spec = load_spec(source)
    if "error" in spec:
        print(f"Erro ao ingerir a fonte {source}: {spec['error']}", file=sys.stderr)
        sys.exit(1)
        
    _, mapping = generate_artifacts(spec)
    return mapping, source.split("/")[-1].split(".")[0][:20]

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python diff_specs.py <base> <target>")
        sys.exit(1)
        
    b_map, b_name = resolve_source(sys.argv[1])
    t_map, t_name = resolve_source(sys.argv[2])
    
    b_meta = extract_meta(b_map)
    t_meta = extract_meta(t_map)
    
    diff = diff_mappings(b_map, t_map)
    report = render_report(diff, b_name, t_name, b_meta, t_meta, sys.argv[1], sys.argv[2])
    
    print(report)
    
    import time
    ts = int(time.time())
    Path(".toon_apis/diffs").mkdir(parents=True, exist_ok=True)
    report_file = Path(f".toon_apis/diffs/diff_{slugify_label(b_name)}_vs_{slugify_label(t_name)}_{ts}.txt")
    report_file.write_text(report, encoding="utf-8")
