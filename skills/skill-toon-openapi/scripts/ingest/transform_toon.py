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

# Chaves de schema consideradas "constraints" relevantes para integração.
_CONSTRAINT_KEYS = [
    "default", "enum", "minimum", "maximum", "exclusiveMinimum",
    "exclusiveMaximum", "minLength", "maxLength", "pattern", "format",
    "multipleOf", "minItems", "maxItems",
]

def extract_constraints(schema):
    """Extrai as constraints de um schema JÁ resolvido. Retorna {} se não houver.

    Para arrays, mescla as constraints dos ``items`` (ex: enum do item), sem
    sobrescrever constraints do próprio array.
    """
    if not isinstance(schema, dict):
        return {}
    c = {}
    for k in _CONSTRAINT_KEYS:
        if schema.get(k) is not None:
            c[k] = schema[k]

    t = schema.get("type")
    if schema.get("nullable") is True or (isinstance(t, list) and "null" in t):
        c["nullable"] = True

    is_array = t == "array" or (isinstance(t, list) and "array" in t)
    if is_array and isinstance(schema.get("items"), dict):
        for k, v in extract_constraints(schema["items"]).items():
            c.setdefault(k, v)
    return c

def _record_constraints(store, token, schema):
    """Registra as constraints de ``schema`` sob ``token`` em ``store`` (se houver)."""
    if store is None:
        return
    c = extract_constraints(schema)
    if c:
        store[token] = c

def _fmt_val(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)

def annotate(token, constraints):
    """Anexa um sufixo compacto ``{...}`` ao token do toon a partir das constraints.

    Só é usado na renderização do toon.txt — o token armazenado em ``params_toon``
    permanece puro. Enums longos são truncados (lista íntegra fica no mapping.json).
    """
    if not constraints:
        return token
    parts = []
    if "enum" in constraints:
        vals = constraints["enum"] or []
        shown = [_fmt_val(x) for x in vals[:6]]
        s = "|".join(shown)
        if len(vals) > 6:
            s += f"|…(+{len(vals) - 6})"
        parts.append(f"enum:{s}")
    if "default" in constraints:
        parts.append(f"def:{_fmt_val(constraints['default'])}")
    if "minimum" in constraints:
        parts.append(f"min:{_fmt_val(constraints['minimum'])}")
    if "maximum" in constraints:
        parts.append(f"max:{_fmt_val(constraints['maximum'])}")
    if "minLength" in constraints:
        parts.append(f"minLen:{constraints['minLength']}")
    if "maxLength" in constraints:
        parts.append(f"maxLen:{constraints['maxLength']}")
    if "multipleOf" in constraints:
        parts.append(f"mult:{_fmt_val(constraints['multipleOf'])}")
    if "format" in constraints:
        parts.append(f"fmt:{constraints['format']}")
    if "pattern" in constraints:
        pat = constraints["pattern"]
        if isinstance(pat, str) and " " not in pat and "}" not in pat and len(pat) <= 20:
            parts.append(f"re:{pat}")
        else:
            parts.append("re:…")
    if constraints.get("nullable"):
        parts.append("null")
    if not parts:
        return token
    return token + "{" + ",".join(parts) + "}"

def _token_depth(token):
    """Profundidade de aninhamento de um token de body. Params (q:/p:/h:/c:/f:) e '…' = 0.
    Ex: body.valor=1, body.valor.original=2, body.infoAdicionais[]=2, body.infoAdicionais[].nome=3."""
    name = token.split(":", 1)[0]
    if not name.startswith("body") or name == "body":
        return 0
    core = name[5:] if name.startswith("body.") else name[4:]
    return core.count(".") + 1 + core.count("[]")

def compact_tokens(tokens, max_depth=1):
    """Projeção rasa para o toon.txt: mantém tokens até max_depth e sinaliza '…' se truncou.
    O mapping.json continua com a lista COMPLETA — isto afeta apenas a renderização do toon."""
    shown = [t for t in tokens if _token_depth(t) <= max_depth]
    if len(shown) < len(tokens):
        shown.append("…")
    return shown

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

# Limites de segurança do expansor recursivo (specs profundas/circulares/patológicas).
_MAX_DEPTH = 8
_MAX_TOKENS = 300

def _deref(spec, node):
    """Resolve um possível $ref. Retorna (schema_resolvido, ref_ou_None)."""
    if isinstance(node, dict) and "$ref" in node:
        return resolve_ref(spec, node), node["$ref"]
    return node, None

def _effective_type(schema):
    """type efetivo tratando OAS 3.1 (lista com 'null')."""
    t = schema.get("type")
    if isinstance(t, list):
        return next((x for x in t if x != "null"), None)
    return t

def _merge_composition(spec, schema, seen):
    """Mescla allOf/oneOf/anyOf de um schema.

    allOf -> união de properties + required (herança/composição).
    oneOf/anyOf -> união de properties como OPCIONAIS + marcador de união.
    Retorna (props, required_list, union_marker). Guarda anti-circular via `seen`.
    """
    if not isinstance(schema, dict):
        return {}, [], None
    props = dict(schema.get("properties", {}))
    req = schema.get("required", [])
    required = list(req) if isinstance(req, list) else []
    union = None

    for sub in schema.get("allOf", []) or []:
        resolved, ref = _deref(spec, sub)
        if ref and ref in seen:
            continue
        sp, sr, su = _merge_composition(spec, resolved, seen | ({ref} if ref else set()))
        props.update(sp)
        required += sr
        union = union or su

    for key, mark in (("oneOf", "~oneOf"), ("anyOf", "~anyOf")):
        for sub in schema.get(key, []) or []:
            union = union or mark
            resolved, ref = _deref(spec, sub)
            if ref and ref in seen:
                continue
            sp, _sr, _su = _merge_composition(spec, resolved, seen | ({ref} if ref else set()))
            for k, v in sp.items():
                props.setdefault(k, v)  # variantes entram como opcionais

    return props, required, union

def _expand(spec, node, prefix, params, constraints, seen, depth, req_mark="!"):
    """Expansor recursivo único. Resolve $ref em qualquer fronteira, mescla composição
    e desce recursivamente por objetos/arrays. Tokens de container/leaf carregam o
    marcador de obrigatoriedade herdado do pai (req_mark) e o marcador de união."""
    base = prefix.rstrip('.')

    if len(params) >= _MAX_TOKENS:
        return params
    if depth > _MAX_DEPTH:
        params.append(f"{base}:o{req_mark}~deep")
        return params

    schema, ref = _deref(spec, node)
    if ref is not None:
        if ref in seen:
            params.append(f"{base}:o{req_mark}~circular")
            return params
        seen = seen | {ref}

    if not isinstance(schema, dict):
        params.append(f"{base}:s{req_mark}")
        return params

    props, required, union = _merge_composition(spec, schema, seen)
    umark = union or ""
    required_set = set(required)
    t = _effective_type(schema)

    is_array = (t == "array") or ("items" in schema and not props)
    is_object = bool(props) or (t == "object") or ("additionalProperties" in schema and not is_array)

    # ARRAY
    if is_array:
        arr_token = f"{base}:a{req_mark}{umark}"
        params.append(arr_token)
        _record_constraints(constraints, arr_token, schema)
        items, _iref = _deref(spec, schema.get("items", {}))
        iprops, _ir, _iu = _merge_composition(spec, items, seen)
        it = _effective_type(items) if isinstance(items, dict) else None
        item_is_scalar = (not iprops and it and it not in ("object", "array")
                          and not (isinstance(items, dict) and "items" in items))
        if item_is_scalar:
            item_token = f"{base}[]:{extract_type(items)}!"
            params.append(item_token)
            _record_constraints(constraints, item_token, items)
            return params
        return _expand(spec, schema.get("items", {}), f"{base}[].", params, constraints, seen, depth + 1, "!")

    # OBJECT
    if is_object:
        # Container do objeto: emitido para nós aninhados ou quando há marcador de união;
        # a raiz do body-objeto continua implícita (compat: expande direto em body.campo).
        if depth > 0 or umark:
            obj_token = f"{base}:o{req_mark}{umark}"
            params.append(obj_token)
            _record_constraints(constraints, obj_token, schema)
        for pname, pschema in props.items():
            cmark = "!" if pname in required_set else "?"
            _expand(spec, pschema, f"{prefix}{pname}.", params, constraints, seen, depth + 1, cmark)
        ap = schema.get("additionalProperties")
        if isinstance(ap, dict):
            _expand(spec, ap, f"{prefix}{{*}}.", params, constraints, seen, depth + 1, "?")
        elif ap is True:
            params.append(f"{prefix}{{*}}:s?")
        return params

    # PRIMITIVO (leaf)
    pt = extract_type(schema)
    leaf = f"{base}:{pt}{req_mark}{umark}"
    params.append(leaf)
    _record_constraints(constraints, leaf, schema)
    return params

def extract_properties(spec, schema, prefix="body.", params=None, depth=0, constraints=None):
    """Wrapper compatível: ponto de entrada do expansor recursivo unificado."""
    if params is None:
        params = []
    return _expand(spec, schema, prefix, params, constraints, seen=frozenset(), depth=depth, req_mark="!")

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

def make_namespace(spec):
    """Deriva o namespace combinando título + versão da spec (quando presente)."""
    info = spec.get("info", {})
    title = info.get("title", "API")
    version = info.get("version", "")
    ns = slugify(title)
    if version:
        ns = f"{ns}-{slugify(version)}"
    return ns

def generate_artifacts(spec):
    toon_lines = []
    mapping = {}

    ns = make_namespace(spec)
    
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
                param_constraints = {}
                _PREFIX_BY_LOC = {"path": "p", "header": "h", "cookie": "c", "formData": "f", "query": "q"}
                sw2_has_form_data = False
                sw2_has_body      = False
                for p in all_params:
                    p = resolve_ref(spec, p)  # parameter pode ser $ref (#/components/parameters/*)
                    req = "!" if p.get("required") else "?"
                    # OAS3: param pode ter schema direto OU content.<media>.schema; SW2: o próprio param
                    schema = p.get("schema")
                    if schema is None and "content" in p:
                        for _ct, _cd in p.get("content", {}).items():
                            schema = _cd.get("schema", {})
                            break
                    if schema is None:
                        schema = p
                    t = extract_type(resolve_ref(spec, schema))
                    in_loc = p.get("in", "query")
                    name = p.get("name")
                    if in_loc == "body":  # Swagger 2.0 body — expande igual ao requestBody OAS3
                        sw2_has_body = True
                        body_schema = p.get("schema", {})
                        if body_schema:
                            params_toon = extract_properties(spec, body_schema, prefix="body.", params=params_toon, constraints=param_constraints)
                        continue

                    pfx = _PREFIX_BY_LOC.get(in_loc, "q")
                    token = f"{pfx}:{name}:{t}{req}"
                    params_toon.append(token)
                    _record_constraints(param_constraints, token, schema)

                    if in_loc == "header":
                        h = {"name": name, "type": t, "required": p.get("required", False)}
                        hc = extract_constraints(schema)
                        if hc:
                            h["constraints"] = hc
                        headers_params.append(h)
                    elif in_loc == "formData":
                        sw2_has_form_data = True
                    
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
                req_body = resolve_ref(spec, details.get("requestBody", {}))  # requestBody pode ser $ref
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
                            temp_c = {}
                            extract_properties(spec, s, prefix="body.", params=temp, constraints=temp_c)
                            for item in temp:
                                if item.startswith("body."):
                                    new_token = "f:" + item[5:]
                                elif item.startswith("body["):
                                    new_token = "f" + item[4:]
                                elif item.startswith("body:"):
                                    new_token = "f:" + item[5:]
                                else:
                                    new_token = item
                                params_toon.append(new_token)
                                if item in temp_c:
                                    param_constraints[new_token] = temp_c[item]
                        else:
                            params_toon = extract_properties(spec, s, prefix="body.", params=params_toon, constraints=param_constraints)

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
                response_constraints = {}
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
                    if not rs:
                        rs = r_det.get("schema", {})  # Swagger 2.0
                    if rs:
                        status_c = {}
                        responses_toon[status] = extract_properties(spec, rs, prefix="body.", constraints=status_c)
                        if status_c:
                            response_constraints[status] = status_c
                    rh = r_det.get("headers", {})
                    if rh:
                        response_headers[status] = [
                            {"name": hname, "type": extract_type(resolve_ref(spec, resolve_ref(spec, hdet).get("schema", {})))}
                            for hname, hdet in rh.items()  # header pode ser $ref (#/components/headers/*)
                        ]

                # Renderização COMPACTA do toon (economia de tokens): 1 nível + '…'.
                # A árvore completa vive no mapping.json (params_toon/responses_toon).
                tags_str = f" [{', '.join(tags)}]" if tags else ""
                toon_lines.append(f"{c} {path} -> {op_id} | {summary}{tags_str}")
                if params_toon:
                    annotated = [tk if tk == "…" else annotate(tk, param_constraints.get(tk, {}))
                                 for tk in compact_tokens(params_toon)]
                    toon_lines.append(f"  Req: {' '.join(annotated)}")

                res_strs = []
                for st in responses_keys:
                    rh_strs = [f"rh:{h['name']}:{h['type']}" for h in response_headers.get(st, [])]
                    # Sucesso (2xx) mostra shape raso; erros/demais só o código de status.
                    if str(st).startswith("2"):
                        st_rc = response_constraints.get(st, {})
                        ann_r = [tk if tk == "…" else annotate(tk, st_rc.get(tk, {}))
                                 for tk in compact_tokens(responses_toon.get(st, []))]
                        parts = ann_r + rh_strs
                    else:
                        parts = []
                    if parts:
                        res_strs.append(f"{st} ({' '.join(parts)})")
                    else:
                        res_strs.append(str(st))

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
                if param_constraints:
                    mapping[op_id]["param_constraints"] = param_constraints
                if response_constraints:
                    mapping[op_id]["response_constraints"] = response_constraints
                
    return "\n".join(toon_lines) + "\n", mapping

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python transform_toon.py <spec.json>")
        sys.exit(1)
        
    spec_path = Path(sys.argv[1])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    ns = make_namespace(spec)
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
