"""
Testes unitários — sem dependência de rede.
Cobre: extract_type, extract_base_url, slugify, generate_artifacts, log_metrics,
       extract_constraints, annotate, validate_constraint, build_happy_payload, diff_constraints.
"""
import json, sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/ingest"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/consult"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/validate"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/testgen"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/diff"))
from transform_toon import generate_artifacts, extract_type, extract_base_url, slugify, extract_auth, extract_constraints, annotate
from log_metrics import log_token_usage
from validate_payload import validate_payload, validate_constraint
from generate_tests import build_happy_payload
from diff_specs import _diff_constraints

@pytest.fixture
def spec_completa():
    return {
        "info": {"title": "Users API"},
        "servers": [{"url": "https://api.exemplo.com/v1"}],
        "paths": {
            "/users": {
                "post": {
                    "operationId": "createUser", "summary": "Cadastrar novo usuário",
                    "tags": ["users"],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {
                        "required": ["email"],
                        "properties": {
                            "email": {"type": "string"}, "age": {"type": "integer"},
                            "active": {"type": "boolean"},
                        }
                    }}}},
                    "responses": {"201": {}, "400": {}},
                },
                "get": {
                    "operationId": "listUsers", "summary": "Listar todos os usuários",
                    "tags": ["users"],
                    "parameters": [{"name": "page", "in": "query", "required": False,
                                    "schema": {"type": "integer"}}],
                    "responses": {"200": {}},
                },
            },
            "/users/{id}": {
                "get": {
                    "operationId": "getUser", "summary": "Buscar usuário por ID",
                    "tags": ["users"],
                    "parameters": [{"name": "id", "in": "path", "required": True,
                                    "schema": {"type": "string"}}],
                    "responses": {"200": {}, "404": {}},
                },
                "delete": {
                    "operationId": "deleteUser", "summary": "Remover usuário",
                    "tags": ["users"],
                    "parameters": [{"name": "id", "in": "path", "required": True,
                                    "schema": {"type": "string"}}],
                    "responses": {"204": {}, "404": {}},
                },
            },
        },
    }

@pytest.fixture
def spec_swagger2_mock():
    return {
        "swagger": "2.0", "info": {"title": "Legacy API"},
        "host": "legacy.exemplo.com", "basePath": "/api", "schemes": ["https"],
        "paths": {"/items": {"get": {"operationId": "listItems",
            "summary": "Listar itens", "tags": ["items"], "responses": {"200": {}}}}},
    }

@pytest.fixture
def spec_sem_servers():
    return {"info": {"title": "No Server API"}, "paths": {
        "/ping": {"get": {"operationId": "ping", "summary": "Health check",
                          "responses": {"200": {}}}}}}

@pytest.fixture
def spec_nullable():
    return {"info": {"title": "Nullable API"},
            "servers": [{"url": "https://api.exemplo.com"}],
            "paths": {"/items": {"get": {
                "operationId": "listItems", "summary": "Listar itens",
                "tags": ["items"],
                "parameters": [{"name": "filter", "in": "query", "required": False,
                                "schema": {"type": ["string", "null"]}}],
                "responses": {"200": {}}}}}}

@pytest.fixture
def spec_circular():
    return {
        "info": {"title": "Circular API"},
        "paths": {
            "/loop": {
                "post": {
                    "requestBody": {
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Node"}}}
                    },
                    "responses": {"200": {}}
                }
            }
        },
        "components": {"schemas": {"Node": {"type": "array", "items": {"$ref": "#/components/schemas/Node"}}}}
    }

@pytest.fixture
def spec_primitive_body():
    return {
        "info": {"title": "Primitive API"},
        "paths": {
            "/upload": {
                "post": {
                    "requestBody": {
                        "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}
                    },
                    "responses": {"200": {}}
                }
            }
        }
    }

@pytest.fixture
def spec_form_data():
    return {
        "info": {"title": "Form API"},
        "paths": {
            "/submit": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/x-www-form-urlencoded": {
                                "schema": {"type": "object", "properties": {"token": {"type": "string"}}}
                            }
                        }
                    },
                    "responses": {"200": {}}
                }
            }
        }
    }

class TestExtractType:
    def test_tipos_primitivos(self):
        assert extract_type({"type": "string"})  == "s"
        assert extract_type({"type": "integer"}) == "i"
        assert extract_type({"type": "number"})  == "i"
        assert extract_type({"type": "boolean"}) == "b"
        assert extract_type({"type": "array"})   == "a"
        assert extract_type({"type": "object"})  == "o"
    def test_nullable_openapi31(self):
        assert extract_type({"type": ["string",  "null"]}) == "s"
        assert extract_type({"type": ["integer", "null"]}) == "i"
    def test_lista_so_null(self):
        assert extract_type({"type": ["null"]}) == "s"
    def test_schema_vazio(self):
        assert extract_type({}) == "s"

class TestExtractBaseUrl:
    def test_openapi3(self):
        assert extract_base_url({"servers": [{"url": "https://api.exemplo.com/v1"}]}) \
               == "https://api.exemplo.com/v1"
    def test_trailing_slash(self):
        assert extract_base_url({"servers": [{"url": "https://api.exemplo.com/v1/"}]}) \
               == "https://api.exemplo.com/v1"
    def test_swagger2(self):
        assert extract_base_url({"host": "x.com", "basePath": "/api", "schemes": ["https"]}) \
               == "https://x.com/api"
    def test_swagger2_sem_scheme(self):
        assert extract_base_url({"host": "x.com", "basePath": "/api"}) \
               == "https://x.com/api"
    def test_sem_servers(self):
        assert extract_base_url({}) == ""
        assert extract_base_url({"servers": []}) == ""

class TestSlugify:
    def test_simples(self):       assert slugify("Petstore API") == "petstore-api"
    def test_numeros(self):       assert slugify("API v2.0")     == "api-v20"
    def test_vazio(self):         assert slugify("")              == "default"
    def test_underscores(self):   assert slugify("my_api")       == "my-api"

class TestGenerateArtifactsToon:
    def test_cabecalho_base(self, spec_completa):
        toon, _ = generate_artifacts(spec_completa)
        assert "BASE: https://api.exemplo.com/v1" in toon
    def test_separador(self, spec_completa):
        toon, _ = generate_artifacts(spec_completa)
        assert "---" in toon
    def test_linhas_summary_tags(self, spec_completa):
        toon, _ = generate_artifacts(spec_completa)
        assert "POST  /users -> createUser" in toon
        assert "GET   /users/{id} -> getUser" in toon
        assert "DEL   /users/{id} -> deleteUser" in toon
    def test_sem_servers(self, spec_sem_servers):
        toon, _ = generate_artifacts(spec_sem_servers)
        assert "BASE: (não definida na spec)" in toon
    def test_nullable_nao_crasha(self, spec_nullable):
        toon, _ = generate_artifacts(spec_nullable)
        assert "listItems" in toon
    def test_swagger2(self, spec_swagger2_mock):
        toon, _ = generate_artifacts(spec_swagger2_mock)
        assert "BASE: https://legacy.exemplo.com/api" in toon
    def test_evita_loop_infinito_circular_arrays(self, spec_circular):
        # Guarda anti-circular: não trava e marca o nó recorrente com ~circular.
        toon, mapping = generate_artifacts(spec_circular)
        assert "body:a!" in toon
        tokens = mapping["postLoop"]["params_toon"]
        assert any("~circular" in t for t in tokens)
        assert len(tokens) < 20  # não expandiu infinitamente
    def test_primitive_root_body(self, spec_primitive_body):
        toon, _ = generate_artifacts(spec_primitive_body)
        assert "Req: binary" in toon
    def test_form_data_priority(self, spec_form_data):
        toon, _ = generate_artifacts(spec_form_data)
        assert "Req: f:token:s?" in toon

class TestGenerateArtifactsMapping:
    def test_full_url(self, spec_completa):
        _, m = generate_artifacts(spec_completa)
        assert m["createUser"]["full_url"] == "https://api.exemplo.com/v1/users"
        assert m["getUser"]["full_url"]    == "https://api.exemplo.com/v1/users/{id}"
    def test_metodos_uppercase(self, spec_completa):
        _, m = generate_artifacts(spec_completa)
        assert m["createUser"]["method"] == "POST"
        assert m["listUsers"]["method"]  == "GET"
        assert m["deleteUser"]["method"] == "DELETE"
    def test_request_body(self, spec_completa):
        _, m = generate_artifacts(spec_completa)
        p = m["createUser"]["params_toon"]
        assert "body.email:s!" in p
        assert "body.age:i?"   in p
        assert "body.active:b?" in p
    def test_param_path(self, spec_completa):
        _, m = generate_artifacts(spec_completa)
        assert "{id}" in m["getUser"]["path"]
    def test_param_query(self, spec_completa):
        _, m = generate_artifacts(spec_completa)
        assert "q:page:i?" in m["listUsers"]["params_toon"]
    def test_responses(self, spec_completa):
        _, m = generate_artifacts(spec_completa)
        assert "201" in m["createUser"]["responses"]
        assert "404" in m["getUser"]["responses"]
    def test_spec_vazia(self):
        toon, m = generate_artifacts({"info": {"title": "Empty"}})
        assert m == {} and "---" in toon

class TestExtractAuth:
    def test_bearer_openapi3(self):
        spec = {"components": {"securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer"}
        }}}
        auth = extract_auth(spec)
        assert auth["scheme"] == "bearer"
        assert "Authorization" in auth["detail"]

    def test_apikey_openapi3(self):
        spec = {"components": {"securitySchemes": {
            "apiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-Api-Key"}
        }}}
        auth = extract_auth(spec)
        assert auth["scheme"] == "apikey"
        assert "X-Api-Key" in auth["detail"]

    def test_basic_openapi3(self):
        spec = {"components": {"securitySchemes": {
            "basicAuth": {"type": "http", "scheme": "basic"}
        }}}
        auth = extract_auth(spec)
        assert auth["scheme"] == "basic"

    def test_bearer_swagger2(self):
        spec = {"securityDefinitions": {
            "Bearer": {"type": "apiKey", "in": "header", "name": "Authorization"}
        }}
        auth = extract_auth(spec)
        assert auth.get("scheme") in ("bearer", "apikey")

    def test_sem_auth(self):
        assert extract_auth({}) == {}
        assert extract_auth({"info": {"title": "No Auth API"}}) == {}

    def test_auth_propagada_no_mapping(self):
        """Operações sem security própria devem herdar a auth global."""
        spec = {
            "info": {"title": "Test"},
            "servers": [{"url": "https://api.exemplo.com"}],
            "components": {"securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            }},
            "paths": {"/items": {"get": {
                "operationId": "listItems",
                "summary": "List items",
                "responses": {"200": {}}
                # sem campo security específico
            }}}
        }
        _, mapping = generate_artifacts(spec)
        assert mapping["listItems"]["security"].get("scheme") == "bearer"

    def test_toon_contem_auth_line(self):
        """toon.txt deve ter linha AUTH: após BASE:."""
        spec = {
            "info": {"title": "Auth Test"},
            "servers": [{"url": "https://api.exemplo.com"}],
            "components": {"securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            }},
            "paths": {"/items": {"get": {
                "operationId": "listItems", "summary": "List",
                "responses": {"200": {}}
            }}}
        }
        toon, _ = generate_artifacts(spec)
        assert "AUTH:" in toon
        assert "bearer" in toon.lower()

    def test_toon_sem_auth_exibe_nao_definida(self, spec_sem_servers):
        toon, _ = generate_artifacts(spec_sem_servers)
        assert "AUTH:" in toon
        assert "não definida" in toon


CONSTRAINTS_FIXTURE = Path(__file__).parent / "fixtures" / "oas3_constraints.json"

@pytest.fixture
def constraints_spec():
    return json.loads(CONSTRAINTS_FIXTURE.read_text())


class TestExtractConstraints:
    def test_string_with_enum_and_default(self):
        schema = {"type": "string", "enum": ["a", "b", "c"], "default": "a"}
        c = extract_constraints(schema)
        assert c["enum"] == ["a", "b", "c"]
        assert c["default"] == "a"

    def test_integer_with_min_max_format(self):
        schema = {"type": "integer", "minimum": 1, "maximum": 100, "format": "int32"}
        c = extract_constraints(schema)
        assert c["minimum"] == 1
        assert c["maximum"] == 100
        assert c["format"] == "int32"

    def test_string_with_length_and_pattern(self):
        schema = {"type": "string", "minLength": 2, "maxLength": 50, "pattern": "^[A-Z]+$"}
        c = extract_constraints(schema)
        assert c["minLength"] == 2
        assert c["maxLength"] == 50
        assert c["pattern"] == "^[A-Z]+$"

    def test_array_inherits_items_enum(self):
        schema = {"type": "array", "items": {"type": "string", "enum": ["x", "y"]}}
        c = extract_constraints(schema)
        assert c["enum"] == ["x", "y"]

    def test_nullable_true(self):
        schema = {"type": "string", "nullable": True}
        c = extract_constraints(schema)
        assert c.get("nullable") is True

    def test_empty_schema_returns_empty(self):
        assert extract_constraints({}) == {}
        assert extract_constraints(None) == {}

    def test_multiple_of(self):
        schema = {"type": "integer", "multipleOf": 5}
        c = extract_constraints(schema)
        assert c["multipleOf"] == 5


class TestAnnotate:
    def test_no_constraints_returns_token(self):
        assert annotate("body.name:s!", {}) == "body.name:s!"

    def test_enum_inline(self):
        result = annotate("q:status:s?", {"enum": ["a", "b", "c"], "default": "a"})
        assert "{" in result and "enum:a|b|c" in result and "def:a" in result

    def test_enum_truncation(self):
        vals = ["v1", "v2", "v3", "v4", "v5", "v6", "v7"]
        result = annotate("q:x:s?", {"enum": vals})
        assert "…(+1)" in result

    def test_min_max(self):
        result = annotate("p:id:i!", {"minimum": 1, "maximum": 100, "format": "int32"})
        assert "min:1" in result and "max:100" in result and "fmt:int32" in result

    def test_nullable(self):
        result = annotate("body.x:s?", {"nullable": True})
        assert "null" in result

    def test_pattern_short(self):
        # patterns sem "}" são renderizados inline; com "}" usam "…" para não quebrar a sintaxe TooN
        result_safe = annotate("body.code:s!", {"pattern": "^[A-Z]+$"})
        assert "re:^[A-Z]+$" in result_safe
        result_brace = annotate("body.code:s!", {"pattern": "^[A-Z]{3}$"})
        assert "re:…" in result_brace

    def test_pattern_with_brace_uses_ellipsis(self):
        result = annotate("body.x:s!", {"pattern": "^{complex}[pattern]$"})
        assert "re:…" in result


class TestGenerateArtifactsConstraints:
    def test_path_param_always_in_params_toon(self, constraints_spec):
        _, mapping = generate_artifacts(constraints_spec)
        assert any(t.startswith("p:itemId") for t in mapping["getItem"]["params_toon"])

    def test_path_param_with_constraint_in_mapping(self, constraints_spec):
        _, mapping = generate_artifacts(constraints_spec)
        pc = mapping["getItem"].get("param_constraints", {})
        path_token = next((k for k in pc if k.startswith("p:itemId")), None)
        assert path_token is not None
        assert pc[path_token]["minimum"] == 1
        assert pc[path_token]["maximum"] == 9999

    def test_query_enum_in_param_constraints(self, constraints_spec):
        _, mapping = generate_artifacts(constraints_spec)
        pc = mapping["getItem"].get("param_constraints", {})
        status_token = next((k for k in pc if "status" in k and k.startswith("q:")), None)
        assert status_token is not None
        assert pc[status_token]["enum"] == ["active", "inactive", "pending"]
        assert pc[status_token]["default"] == "active"

    def test_body_maxlength_in_constraints(self, constraints_spec):
        _, mapping = generate_artifacts(constraints_spec)
        pc = mapping["updateItem"].get("param_constraints", {})
        name_token = next((k for k in pc if "name" in k and "body." in k), None)
        assert name_token is not None
        assert pc[name_token]["maxLength"] == 100

    def test_response_constraints_enum(self, constraints_spec):
        _, mapping = generate_artifacts(constraints_spec)
        rc = mapping["getItem"].get("response_constraints", {})
        assert "200" in rc
        status_tok = next((k for k in rc["200"] if "status" in k), None)
        assert status_tok is not None
        assert "active" in rc["200"][status_tok]["enum"]

    def test_toon_inline_annotation(self, constraints_spec):
        toon, _ = generate_artifacts(constraints_spec)
        assert "p:itemId:i!{" in toon
        assert "enum:active|inactive|pending" in toon

    def test_toon_path_param_without_constraint_no_braces(self):
        spec = {
            "info": {"title": "T"}, "servers": [{"url": "https://x.com"}],
            "paths": {"/a/{id}": {"get": {
                "operationId": "getA",
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {}}
            }}}
        }
        toon, _ = generate_artifacts(spec)
        assert "p:id:s!" in toon
        assert "{" not in toon.split("p:id:s!")[1].split("\n")[0]

    def test_params_toon_token_stays_pure(self, constraints_spec):
        _, mapping = generate_artifacts(constraints_spec)
        for token in mapping["getItem"]["params_toon"]:
            assert "{" not in token

    def test_no_constraints_keys_omitted(self):
        spec = {
            "info": {"title": "T"}, "servers": [{"url": "https://x.com"}],
            "paths": {"/a": {"get": {
                "operationId": "listA",
                "parameters": [{"name": "page", "in": "query", "required": False, "schema": {"type": "integer"}}],
                "responses": {"200": {}}
            }}}
        }
        _, mapping = generate_artifacts(spec)
        assert "param_constraints" not in mapping["listA"]
        assert "response_constraints" not in mapping["listA"]


class TestValidateConstraints:
    def _make_entry(self, params_toon, param_constraints=None):
        return {"params_toon": params_toon, "param_constraints": param_constraints or {}}

    def test_enum_invalid_is_error(self):
        entry = self._make_entry(
            ["body.status:s!"],
            {"body.status:s!": {"enum": ["a", "b", "c"]}}
        )
        result = validate_payload(entry, {"status": "invalid"})
        assert not result["is_valid"]
        errors = [e for e in result["errors"] if "enum" in e["error"]]
        assert errors and "ERRO" in errors[0]["severity"]

    def test_enum_valid_passes(self):
        entry = self._make_entry(
            ["body.status:s!"],
            {"body.status:s!": {"enum": ["a", "b", "c"]}}
        )
        result = validate_payload(entry, {"status": "a"})
        assert result["is_valid"]

    def test_maxlength_violation_is_warning(self):
        entry = self._make_entry(
            ["body.name:s!"],
            {"body.name:s!": {"maxLength": 5}}
        )
        result = validate_payload(entry, {"name": "toolongvalue"})
        warnings = [e for e in result["errors"] if "maxLength" in e["error"]]
        assert warnings and "AVISO" in warnings[0]["severity"]

    def test_minimum_violation_is_warning(self):
        entry = self._make_entry(
            ["body.qty:i!"],
            {"body.qty:i!": {"minimum": 1}}
        )
        result = validate_payload(entry, {"qty": 0})
        warnings = [e for e in result["errors"] if "mínimo" in e["error"]]
        assert warnings and "AVISO" in warnings[0]["severity"]

    def test_pattern_violation_is_warning(self):
        entry = self._make_entry(
            ["body.code:s!"],
            {"body.code:s!": {"pattern": "^[A-Z]{3}$"}}
        )
        result = validate_payload(entry, {"code": "abc"})
        warnings = [e for e in result["errors"] if "pattern" in e["error"]]
        assert warnings and "AVISO" in warnings[0]["severity"]

    def test_no_constraints_no_extra_errors(self):
        entry = self._make_entry(["body.name:s!"])
        result = validate_payload(entry, {"name": "hello"})
        assert result["is_valid"]


class TestTestgenConstraints:
    def test_enum_uses_first_value(self):
        params = ["body.status:s!"]
        pc = {"body.status:s!": {"enum": ["placed", "approved"]}}
        payload = build_happy_payload(params, pc)
        assert payload["status"] == "placed"

    def test_default_used_when_no_enum(self):
        params = ["body.active:b?"]
        pc = {"body.active:b?": {"default": False}}
        payload = build_happy_payload(params, pc)
        assert payload["active"] is False

    def test_minimum_used_for_integer(self):
        params = ["body.qty:i?"]
        pc = {"body.qty:i?": {"minimum": 10}}
        payload = build_happy_payload(params, pc)
        assert payload["qty"] == 10

    def test_no_constraints_uses_defaults(self):
        params = ["body.name:s!", "body.count:i?", "body.flag:b?"]
        payload = build_happy_payload(params)
        assert isinstance(payload["name"], str)
        assert isinstance(payload["count"], int)
        assert isinstance(payload["flag"], bool)


class TestDiffConstraints:
    def test_enum_removal_is_breaking(self):
        b = {"tok": {"enum": ["a", "b", "c"]}}
        t = {"tok": {"enum": ["a", "b"]}}
        changes = _diff_constraints(b, t)
        assert any(c["rule"] == "constraint_tightened" for c in changes)

    def test_enum_addition_is_non_breaking(self):
        b = {"tok": {"enum": ["a", "b"]}}
        t = {"tok": {"enum": ["a", "b", "c"]}}
        changes = _diff_constraints(b, t)
        assert any(c["rule"] == "constraint_relaxed" for c in changes)

    def test_maxlength_reduction_is_breaking(self):
        b = {"tok": {"maxLength": 100}}
        t = {"tok": {"maxLength": 20}}
        changes = _diff_constraints(b, t)
        assert any(c["rule"] == "constraint_tightened" for c in changes)

    def test_minimum_increase_is_breaking(self):
        b = {"tok": {"minimum": 0}}
        t = {"tok": {"minimum": 5}}
        changes = _diff_constraints(b, t)
        assert any(c["rule"] == "constraint_tightened" for c in changes)

    def test_no_change_no_diff(self):
        c = {"tok": {"enum": ["a", "b"], "maxLength": 50}}
        assert _diff_constraints(c, c) == []

    def test_empty_base_no_breaking(self):
        changes = _diff_constraints({}, {"tok": {"maxLength": 50}})
        assert all(c["rule"] != "constraint_tightened" for c in changes)


STRUCTURAL_FIXTURE = Path(__file__).parent / "fixtures" / "oas3_structural.json"

@pytest.fixture(scope="module")
def structural():
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/ingest"))
    from parse_spec import load_spec
    spec = load_spec(str(STRUCTURAL_FIXTURE))
    toon, mapping = generate_artifacts(spec)
    return toon, mapping


class TestStructuralFidelity:
    """Perenidade: $ref em qualquer fronteira, composição, recursão, additionalProperties."""

    def _tokens(self, mapping, op):
        return mapping[op]["params_toon"]

    def test_parameter_ref_resolved(self, structural):
        _, mapping = structural
        toks = self._tokens(mapping, "createWidget")
        assert "q:page:i?" in toks
        assert not any(":None:" in t or t.startswith("q:None") for t in toks)

    def test_requestbody_ref_resolved(self, structural):
        _, mapping = structural
        toks = self._tokens(mapping, "createWidget")
        assert any(t.startswith("body.name:") for t in toks)

    def test_allof_merges_properties_and_required(self, structural):
        _, mapping = structural
        toks = self._tokens(mapping, "createWidget")
        assert "body.id:i!" in toks      # required herdado de Base
        assert "body.name:s!" in toks    # required do topo de Widget

    def test_nested_array_of_ref_objects(self, structural):
        _, mapping = structural
        toks = self._tokens(mapping, "createWidget")
        assert "body.tags:a?" in toks
        assert "body.tags[].key:s?" in toks

    def test_additional_properties_schema_wildcard(self, structural):
        _, mapping = structural
        toks = self._tokens(mapping, "createWidget")
        assert "body.meta.{*}.key:s?" in toks

    def test_additional_properties_true(self, structural):
        _, mapping = structural
        toks = self._tokens(mapping, "createWidget")
        assert "body.freeform.{*}:s?" in toks

    def test_additional_properties_false_no_wildcard(self, structural):
        _, mapping = structural
        toks = self._tokens(mapping, "createWidget")
        assert "body.closed:o?" in toks
        assert not any(t.startswith("body.closed.{*}") for t in toks)

    def test_not_keyword_does_not_crash(self, structural):
        _, mapping = structural
        toks = self._tokens(mapping, "createWidget")
        assert any(t.startswith("body.forbidden:") for t in toks)

    def test_oneof_merges_variants_as_optional(self, structural):
        _, mapping = structural
        toks = self._tokens(mapping, "createContact")
        assert any("~oneOf" in t for t in toks)
        assert "body.email:s?" in toks
        assert "body.phone:s?" in toks

    def test_circular_ref_guarded(self, structural):
        _, mapping = structural
        toks = self._tokens(mapping, "createNode")
        assert any("~circular" in t for t in toks)
        assert len(toks) < 20

    def test_constraints_survive_composition(self, structural):
        _, mapping = structural
        pc = mapping["createWidget"].get("param_constraints", {})
        assert pc.get("body.id:i!", {}).get("format") == "int64"
        assert pc.get("body.name:s!", {}).get("maxLength") == 50
        assert pc.get("body.kind:s?", {}).get("enum") == ["a", "b", "c"]
        assert pc.get("q:page:i?", {}).get("minimum") == 1

    def test_toon_stays_compact(self, structural):
        toon, _ = structural
        # Toon compacto: linhas Req não devem despejar árvore profunda; '…' quando trunca.
        req_lines = [l for l in toon.splitlines() if l.strip().startswith("Req:")]
        assert req_lines
        assert all(len(l) < 400 for l in req_lines)


class TestLogMetrics:
    def test_cria_arquivo(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        log_token_usage("ns", 100, "ingest")
        assert (tmp_path / ".toon_apis" / "apis" / "ns" / "metrics.json").exists()
    def test_estrutura(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        d = log_token_usage("ns", 42, "ingest")
        assert d["total_tokens"] == 42
        assert d["history"][0]["mode"] == "ingest"
        assert "timestamp" in d["history"][0]
    def test_acumulacao(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        log_token_usage("ns", 100, "ingest")
        log_token_usage("ns", 50, "consult")
        d = log_token_usage("ns", 25, "generate")
        assert d["total_tokens"] == 175 and len(d["history"]) == 3
    def test_namespaces_isolados(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        log_token_usage("a", 100, "ingest")
        d = log_token_usage("b", 50, "ingest")
        assert d["total_tokens"] == 50
    def test_corrompido_recupera(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        d = tmp_path / ".toon_apis" / "apis" / "ns"
        d.mkdir(parents=True)
        (d / "metrics.json").write_text("INVALID{{")
        assert log_token_usage("ns", 10, "consult")["total_tokens"] == 10
