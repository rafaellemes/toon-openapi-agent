"""
Testes unitários do validador de payload — sem rede.
"""
import sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/validate"))
from validate_payload import validate_payload, parse_params_toon, render_validation_report

@pytest.fixture
def entry_simples():
    return {"method": "POST", "path": "/users", "full_url": "https://api.exemplo.com/v1/users",
            "params_toon": ["body.email:s!", "body.age:i?", "body.active:b?"],
            "summary": "Criar usuário", "responses": ["201", "400"]}

@pytest.fixture
def entry_aninhado():
    return {"method": "POST", "path": "/users", "full_url": "https://api.exemplo.com/v1/users",
            "params_toon": ["body.name:s!", "body.address:o?",
                            "body.address.street:s?", "body.address.zip:s?"],
            "summary": "Criar com endereço", "responses": ["201"]}

@pytest.fixture
def entry_array():
    return {"method": "POST", "path": "/users/bulk", "full_url": "https://api.exemplo.com/v1/users/bulk",
            "params_toon": ["body.users:a!"], "summary": "Bulk", "responses": ["201"]}

class TestParseParamsToon:
    def test_body_obrigatorio(self):
        p = parse_params_toon(["body.email:s!"])[0]
        assert p["name"]=="email" and p["prefix"]=="body" and p["type"]=="s" and p["required"] is True
    def test_body_opcional(self):
        assert parse_params_toon(["body.age:i?"])[0]["required"] is False
    def test_sem_prefixo(self):
        p = parse_params_toon(["id:s!"])[0]
        assert p["prefix"] is None and p["name"]=="id"
    def test_invalido_ignorado(self):
        assert parse_params_toon(["invalido", ""]) == []

class TestValidPayload:
    def test_minimo_valido(self, entry_simples):
        r = validate_payload(entry_simples, {"email": "a@b.com"})
        assert r["is_valid"] and r["hard_count"] == 0
    def test_completo_valido(self, entry_simples):
        assert validate_payload(entry_simples, {"email":"a@b.com","age":30,"active":True})["is_valid"]
    def test_obrigatorio_ausente(self, entry_simples):
        r = validate_payload(entry_simples, {"age": 30})
        assert not r["is_valid"] and r["hard_count"] >= 1
        assert "email" in [e["field"] for e in r["errors"] if "ERRO" in e["severity"]]
    def test_tipo_errado_string(self, entry_simples):
        assert validate_payload(entry_simples, {"email": 123})["hard_count"] >= 1
    def test_tipo_errado_integer(self, entry_simples):
        assert validate_payload(entry_simples, {"email":"a@b.com","age":"trinta"})["hard_count"] >= 1
    def test_campo_extra_aviso(self, entry_simples):
        r = validate_payload(entry_simples, {"email":"a@b.com","extra":"x"})
        assert r["is_valid"] and r["warn_count"] >= 1
    def test_payload_vazio(self, entry_simples):
        r = validate_payload(entry_simples, {})
        assert not r["is_valid"] and r["hard_count"] >= 1

class TestBoolNotInt:
    def test_bool_nao_aceite_como_int(self):
        entry = {"method":"POST","path":"/x","full_url":"/x",
                 "params_toon":["body.count:i!"],"summary":"","responses":[]}
        assert validate_payload(entry, {"count": True})["hard_count"] >= 1
    def test_bool_correto_para_boolean(self, entry_simples):
        assert validate_payload(entry_simples, {"email":"a@b.com","active":True})["hard_count"] == 0

class TestRecursao:
    def test_aninhado_valido(self, entry_aninhado):
        r = validate_payload(entry_aninhado,
                             {"name":"João","address":{"street":"Rua A","zip":"1234"}}, max_depth=3)
        assert r["is_valid"]
    def test_aninhado_tipo_errado(self, entry_aninhado):
        assert validate_payload(entry_aninhado,
                                {"name":"João","address":{"street":123}}, max_depth=3)["hard_count"] >= 1
    def test_depth_zero_nao_desce(self, entry_aninhado):
        r = validate_payload(entry_aninhado,
                             {"name":"João","address":{"street":999}}, max_depth=0)
        assert any("address" in e["field"] and "INFO" in e["severity"] for e in r["errors"])
    def test_array_valido(self, entry_array):
        assert validate_payload(entry_array, {"users":[{"name":"A"}]})["is_valid"]
    def test_array_tipo_errado(self, entry_array):
        assert validate_payload(entry_array, {"users":"nao_array"})["hard_count"] >= 1

class TestRenderValidationReport:
    def _r(self, is_valid, errors=None):
        errors = errors or []
        return {"is_valid":is_valid,"errors":errors,
                "hard_count":len([e for e in errors if "ERRO" in e.get("severity","")]),
                "warn_count":len([e for e in errors if "AVISO" in e.get("severity","")]),
                "info_count":len([e for e in errors if "INFO" in e.get("severity","")])}
    def test_valido(self):
        assert "✅ VÁLIDO" in render_validation_report(self._r(True),"ns","addPet",3)
    def test_invalido(self):
        r = render_validation_report(self._r(False,[{
            "field":"email","token":"body.email:s!",
            "error":"campo obrigatório ausente","severity":"🔴 ERRO"}]),"ns","addPet",3)
        assert "❌ INVÁLIDO" in r and "email" in r
