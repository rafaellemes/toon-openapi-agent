import sys
from pathlib import Path

def load_namespace_toon(namespace):
    storage_dir = Path(".toon_apis/apis") / namespace
    toon_path = storage_dir / "toon.txt"
    if not toon_path.exists():
        raise FileNotFoundError(f"Namespace não encontrado: {namespace}")
    return toon_path.read_text(encoding="utf-8")

def build_multi_view(namespaces):
    if len(namespaces) < 2:
        print("Erro: É necessário fornecer pelo menos dois namespaces.", file=sys.stderr)
        sys.exit(1)
        
    out = []
    
    if len(namespaces) > 5:
        out.append("AVISO: Mais de 5 namespaces combinados. Recomendado escopo menor.\n")
        
    out.append(f"=== MULTI-NAMESPACE: {' + '.join(namespaces)} ===\n")
    
    for ns in namespaces:
        try:
            content = load_namespace_toon(ns)
            lines = content.splitlines()
            base = lines[0] if lines else "BASE: (não encontrada)"
            out.append(f"[{ns} | {base}]")
            out.append("\n".join(lines[1:]))
            out.append("")
        except FileNotFoundError as e:
            out.append(f"[{ns} | ERRO: namespace não encontrado]")
            out.append("")
            
    out.append("===")
    out.append("Para gerar código: jq '.<operationId>' .toon_apis/<namespace>/mapping.json")
    
    return "\n".join(out)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python resolve_multi.py <ns1> <ns2> ...")
        sys.exit(1)
        
    namespaces = sys.argv[1:]
    
    try:
        # Validate that if any doesn't exist, we exit 1? Wait, test says: "Se algum namespace não existir → listar os disponíveis e indicar qual falhou".
        # But wait, test says: "Exit: 0=sucesso, 1=namespace não encontrado"
        view = build_multi_view(namespaces)
        print(view)
        # Check if any error was in view
        if "namespace não encontrado" in view:
            sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {str(e)}", file=sys.stderr)
        sys.exit(1)
