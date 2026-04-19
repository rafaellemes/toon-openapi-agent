"""
Testes unitários — sem dependência de rede.
Cobre: extract_type, extract_base_url, slugify, generate_artifacts, log_metrics.
"""
import json, sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/ingest"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/consult"))
from transform_toon import generate_artifacts, extract_type, extract_base_url, slugify, extract_auth
from log_metrics import log_token_usage

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
        toon, _ = generate_artifacts(spec_circular)
        assert "body[][][][][]:a!" in toon  # Limite máximo 5
    def test_primitive_root_body(self, spec_primitive_body):
        toon, _ = generate_artifacts(spec_primitive_body)
        assert "Req: body:s!" in toon
    def test_form_data_priority(self, spec_form_data):
        toon, _ = generate_artifacts(spec_form_data)
        assert "Req: body.token:s?" in toon

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
        assert "id:s!" in m["getUser"]["params_toon"]
    def test_param_query(self, spec_completa):
        _, m = generate_artifacts(spec_completa)
        assert "page:i?" in m["listUsers"]["params_toon"]
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
