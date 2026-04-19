import json
import sys
import re
from pathlib import Path

def extract_type(schema):
    if not schema:
        return "s"
    t = schema.get("type")
    if isinstance(t, list):
        # OpenAPI 3.1 com nullable ex: ["string", "null"]
        t = next((x for x in t if x != "null"), "string")
    if not t:
        return "s"
    
    mapping = {
        "string": "s",
        "integer": "i",
        "number": "i",
        "boolean": "b",
        "array": "a",
        "object": "o"
    }
    return mapping.get(t, "s")

def extract_base_url(spec):
    if "servers" in spec and spec["servers"]:
        url = spec["servers"][0].get("url", "")
        if url.endswith("/"):
            url = url[:-1]
        return url
    if "host" in spec or spec.get("swagger") == "2.0":
        host = spec.get("host", "")
        base_path = spec.get("basePath", "")
        schemes = spec.get("schemes", ["https"])
        scheme = schemes[0] if schemes else "https"
        if host:
            return f"{scheme}://{host}{base_path}"
    return ""

def slugify(text):
    if not text:
        return "default"
    # remove punctuation except spaces and underscores
    text = re.sub(r'[^a-zA-Z0-9\s_]+', '', text)
    text = re.sub(r'[\s_]+', '-', text).strip('-').lower()
    return text if text else "default"

def resolve_ref(spec, schema):
    if not isinstance(schema, dict):
        return schema
    ref = schema.get("$ref")
    if not ref:
        return schema
    
    # ex: #/components/schemas/Pet
    parts = ref.lstrip("#/").split("/")
    current = spec
    try:
        for p in parts:
            current = current[p]
        return current
    except (KeyError, TypeError):
        return schema

def extract_properties(spec, schema, prefix="body.", params=None, depth=0):
    if params is None:
        params = []
        
    if depth > 5:
        return params
    
    schema = resolve_ref(spec, schema)
    
    # Se o schema raiz for um array, indicamos que é um array e extraímos as propriedades dos itens
    if schema.get("type") == "array" or "items" in schema:
        items = schema.get("items", {})
        items = resolve_ref(spec, items)
        base = prefix.rstrip('.')
        params.append(f"{base}:a!")
        new_prefix = f"{base}[]."
        
        # Pode ser um array de primitivos
        if not items.get("properties") and "type" in items and items["type"] not in ("object", "array"):
            pt = extract_type(items)
            params.append(f"{base}[]:{pt}!")
            return params
            
        return extract_properties(spec, items, prefix=new_prefix, params=params, depth=depth+1)

    props = schema.get("properties", {})
    
    # Root primitive body identification
    if not props and schema.get("type") and schema.get("type") not in ("object", "array"):
        pt = extract_type(schema)
        params.append(f"{prefix.rstrip('.')}:{pt}!")
        return params
    req_fields = schema.get("required", [])
    if isinstance(req_fields, bool):
        req_fields = []
    
    for pname, pschema in props.items():
        pschema = resolve_ref(spec, pschema)
        freq = "!" if pname in req_fields else "?"
        pt = extract_type(pschema)
        params.append(f"{prefix}{pname}:{pt}{freq}")
        
    return params

def extract_auth(spec):
    # OpenAPI 3.x
    components = spec.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    
    # Swagger 2.x
    if not security_schemes:
        security_schemes = spec.get("securityDefinitions", {})

    if not security_schemes:
        return {}

    # Pega o primeiro esquema
    name, scheme_def = next(iter(security_schemes.items()))
    t = scheme_def.get("type", "").lower()
    
    if t == "http":
        s = scheme_def.get("scheme", "").lower()
        if s == "bearer":
            return {"scheme": "bearer", "type": "http", "detail": "header: Authorization"}
        if s == "basic":
            return {"scheme": "basic", "type": "http", "detail": "header: Authorization"}
        return {"scheme": s, "type": "http", "detail": ""}
    elif t == "apikey":
        in_loc = scheme_def.get("in", "header")
        param_name = scheme_def.get("name", name)
        return {"scheme": "apikey", "type": "apikey", "detail": f"{in_loc}: {param_name}"}
    elif t == "oauth2":
        return {"scheme": "oauth2", "type": "oauth2", "detail": "oauth2 flow"}
        
    return {"scheme": t, "type": t, "detail": ""}

def generate_artifacts(spec):
    toon_lines = []
    mapping = {}
    
    title = spec.get("info", {}).get("title", "API")
    ns = slugify(title)
    
    base_url = extract_base_url(spec)
    toon_lines.append(f"BASE: {base_url if base_url else '(não definida na spec)'}")
    
    auth = extract_auth(spec)
    if auth:
        toon_lines.append(f"AUTH: {auth['scheme']} ({auth['detail']})")
    else:
        toon_lines.append(f"AUTH: não definida")
        
    toon_lines.append("---")
    
    global_security = spec.get("security", [])
    
    paths = spec.get("paths", {})
    if paths:
        for path, methods in paths.items():
            path_params = methods.get("parameters", [])
            for method, details in methods.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch", "head", "options"]:
                    continue
                
                op_id = details.get("operationId", "")
                if not op_id:
                    # Gera um opId falso base
                    op_id = f"{method.lower()}{re.sub(r'[^a-zA-Z0-9]', '', path.title())}"
                    
                summary = details.get("summary", "")
                tags = details.get("tags", [])
                
                # Resolvendo parãmetros
                all_params = path_params + details.get("parameters", [])
                params_toon = []
                headers_params = []
                sw2_has_form_data = False
                sw2_has_body      = False
                for p in all_params:
                    req = "!" if p.get("required") else "?"
                    schema = p.get("schema", p) # Fallback param=schema (Swagger 2.0)
                    t = extract_type(schema)
                    in_loc = p.get("in", "query")
                    if in_loc == "path":
                        continue  # path params já estão visíveis na URL
                    elif in_loc == "header":
                        params_toon.append(f"h:{p.get('name')}:{t}{req}")
                        headers_params.append({"name": p.get("name"), "type": t, "required": p.get("required", False)})
                    elif in_loc == "cookie":
                        params_toon.append(f"c:{p.get('name')}:{t}{req}")
                    elif in_loc == "formData":
                        sw2_has_form_data = True
                        params_toon.append(f"f:{p.get('name')}:{t}{req}")
                    elif in_loc == "body":  # Swagger 2.0 body — expande igual ao requestBody OAS3
                        sw2_has_body = True
                        body_schema = p.get("schema", {})
                        if body_schema:
                            params_toon = extract_properties(spec, body_schema, prefix="body.", params=params_toon)
                    else:  # query
                        params_toon.append(f"q:{p.get('name')}:{t}{req}")
                    
                # Resolvendo requestBody
                _FORM_CTS   = {"multipart/form-data", "application/x-www-form-urlencoded"}
                _BINARY_CTS = {"application/octet-stream", "application/pdf"}
                _STREAM_CTS = {"text/event-stream"}
                _TEXT_CTS   = {"text/plain", "text/html", "text/csv"}
                _CT_ORDER   = [
                    "application/json", "application/xml", "application/ld+json",
                    "application/vnd.api+json", "multipart/form-data",
                    "application/x-www-form-urlencoded", "text/plain", "text/html",
                    "application/octet-stream", "text/event-stream",
                ]
                request_content_type = None
                req_body = details.get("requestBody", {})
                if req_body:
                    req_content = req_body.get("content", {})
                    s = {}
                    matched_ct = None
                    for pr in _CT_ORDER:
                        if pr in req_content:
                            matched_ct = pr
                            s = req_content[pr].get("schema", {})
                            break
                    if not matched_ct:
                        for ct, ctdet in req_content.items():
                            matched_ct = ct
                            s = ctdet.get("schema", {})
                            break
                    request_content_type = matched_ct
                    is_binary = matched_ct in _BINARY_CTS or bool(
                        matched_ct and matched_ct.startswith(("image/", "audio/", "video/"))
                    )
                    if is_binary:
                        params_toon.append("binary")
                    elif matched_ct in _STREAM_CTS:
                        params_toon.append("stream")
                    elif matched_ct in _TEXT_CTS:
                        params_toon.append("body:s")
                    elif s:
                        if matched_ct in _FORM_CTS:
                            temp = []
                            extract_properties(spec, s, prefix="body.", params=temp)
                            for item in temp:
                                if item.startswith("body."):
                                    params_toon.append("f:" + item[5:])
                                elif item.startswith("body["):
                                    params_toon.append("f" + item[4:])
                                elif item.startswith("body:"):
                                    params_toon.append("f:" + item[5:])
                                else:
                                    params_toon.append(item)
                        else:
                            params_toon = extract_properties(spec, s, prefix="body.", params=params_toon)

                # Swagger 2.0: inferir request_content_type via consumes
                if request_content_type is None and (sw2_has_form_data or sw2_has_body):
                    op_consumes = details.get("consumes", spec.get("consumes", []))
                    if op_consumes:
                        request_content_type = op_consumes[0]
                    elif sw2_has_form_data:
                        request_content_type = "multipart/form-data"
                    elif sw2_has_body:
                        request_content_type = "application/json"

                m_upper = method.upper()
                c = "DEL  " if m_upper == "DELETE" else f"{m_upper: <5}"
                responses_keys = list(details.get("responses", {}).keys())
                responses_toon = {}
                response_headers = {}
                for status, r_det in details.get("responses", {}).items():
                    r_det = resolve_ref(spec, r_det)
                    r_content = r_det.get("content", {})
                    rs = {}
                    priorities = ["application/json", "multipart/form-data", "application/x-www-form-urlencoded"]
                    for pr in priorities:
                        if pr in r_content and "schema" in r_content[pr]:
                            rs = r_content[pr]["schema"]
                            break
                    if not rs:
                        for ct, ctdet in r_content.items():
                            if "schema" in ctdet:
                                rs = ctdet["schema"]
                                break
                    if rs:
                        responses_toon[status] = extract_properties(spec, rs, prefix="body.")
                    rh = r_det.get("headers", {})
                    if rh:
                        response_headers[status] = [
                            {"name": hname, "type": extract_type(resolve_ref(spec, hdet.get("schema", {})))}
                            for hname, hdet in rh.items()
                        ]

                tags_str = f" [{', '.join(tags)}]" if tags else ""
                toon_lines.append(f"{c} {path} -> {op_id} | {summary}{tags_str}")
                if params_toon:
                    toon_lines.append(f"  Req: {' '.join(params_toon)}")

                res_strs = []
                for st in responses_keys:
                    r_params = responses_toon.get(st, [])
                    rh_strs = [f"rh:{h['name']}:{h['type']}" for h in response_headers.get(st, [])]
                    parts = r_params + rh_strs
                    if parts:
                        res_strs.append(f"{st} ({' '.join(parts)})")
                    else:
                        res_strs.append(st)

                if res_strs:
                    toon_lines.append(f"  Res: {', '.join(res_strs)}")
                
                sec = auth if "security" not in details else auth
                
                full_url = f"{base_url}{path}" if base_url else path
                
                
                mapping[op_id] = {
                    "method": m_upper,
                    "path": path,
                    "base_url": base_url,
                    "full_url": full_url,
                    "params_toon": params_toon,
                    "request_content_type": request_content_type,
                    "headers": headers_params,
                    "summary": summary,
                    "tags": tags,
                    "responses": responses_keys,
                    "responses_toon": responses_toon,
                    "response_headers": response_headers,
                    "security": sec
                }
                
    return "\n".join(toon_lines) + "\n", mapping

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python transform_toon.py <spec.json>")
        sys.exit(1)
        
    spec_path = Path(sys.argv[1])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    
    title = spec.get("info", {}).get("title", "API")
    ns = slugify(title)
    
    toon, mapping = generate_artifacts(spec)
    
    storage_dir = Path(".toon_apis/apis") / ns
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    (storage_dir / "toon.txt").write_text(toon, encoding="utf-8")
    (storage_dir / "mapping.json").write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    
    import subprocess
    export_script = Path(__file__).parent.parent / "export" / "export_context.py"
    
    cmd = [sys.executable, str(export_script), ns, "--save"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[{len(mapping)} operações ingeridas. Porém ocorreu um erro ao gerar a view exportavel]")
        print(e.stderr)
