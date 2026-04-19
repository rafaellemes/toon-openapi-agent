"""
Testes unitários do extractor de contrato — sem rede.
"""
import sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/clientgen"))
from extract_contract import detect_auth, filter_operations, parse_params, render_contract

@pytest.fixture
def mapping():
    return {
        "addPet": {"method":"POST","path":"/pet",
                   "base_url":"https://petstore3.swagger.io/api/v3",
                   "full_url":"https://petstore3.swagger.io/api/v3/pet",
                   "params_toon":["body.name:s!","body.status:s?"],
                   "summary":"Add a new pet","tags":["pet"],
                   "responses":["200","405"],"security":{"scheme":"bearer"}},
        "getPetById": {"method":"GET","path":"/pet/{petId}",
                       "base_url":"https://petstore3.swagger.io/api/v3",
                       "full_url":"https://petstore3.swagger.io/api/v3/pet/{petId}",
                       "params_toon":["petId:i!"],"summary":"Find pet by ID","tags":["pet"],
                       "responses":["200","404"],"security":{"scheme":"bearer"}},
        "getInventory": {"method":"GET","path":"/store/inventory",
                         "base_url":"https://petstore3.swagger.io/api/v3",
                         "full_url":"https://petstore3.swagger.io/api/v3/store/inventory",
                         "params_toon":[],"summary":"Returns inventories","tags":["store"],
                         "responses":["200"],"security":{"scheme":"apikey","name":"X-Api-Key"}},
        "createUser": {"method":"POST","path":"/user",
                       "base_url":"https://petstore3.swagger.io/api/v3",
                       "full_url":"https://petstore3.swagger.io/api/v3/user",
                       "params_toon":["body.username:s!","body.email:s!","body.age:i?"],
                       "summary":"Create user","tags":["user"],
                       "responses":["200"],"security":{}},
    }

class TestDetectAuth:
    def test_bearer(self, mapping):
        assert detect_auth({"addPet": mapping["addPet"]})["scheme"] == "bearer"
    def test_apikey(self, mapping):
        assert detect_auth({"getInventory": mapping["getInventory"]})["scheme"] == "apikey"
    def test_sem_auth(self, mapping):
        assert not detect_auth({"createUser": mapping["createUser"]}).get("scheme")
    def test_vazio(self):
        assert detect_auth({}) == {}

class TestFilterOperations:
    def test_operation(self, mapping):
        assert list(filter_operations(mapping,"addPet",None).keys()) == ["addPet"]
    def test_tag_pet(self, mapping):
        ops = filter_operations(mapping, None, "pet")
        assert "addPet" in ops and "getInventory" not in ops
    def test_tag_case_insensitive(self, mapping):
        assert "addPet" in filter_operations(mapping, None, "PET")
    def test_completo(self, mapping):
        assert len(filter_operations(mapping, None, None)) == len(mapping)
    def test_operation_inexistente(self, mapping):
        with pytest.raises(KeyError): filter_operations(mapping,"naoExiste",None)
    def test_tag_inexistente(self, mapping):
        with pytest.raises(KeyError): filter_operations(mapping, None, "xxx")

class TestParseParams:
    def test_body_obrigatorio(self):
        body, _ = parse_params(["body.name:s!"])
        assert body[0] == {"name":"name","type":"string","required":True,"is_body":True}
    def test_body_opcional(self):
        body, _ = parse_params(["body.status:s?"])
        assert body[0]["required"] is False
    def test_path_param(self):
        _, other = parse_params(["petId:i!"])
        assert other[0]["name"]=="petId" and other[0]["type"]=="integer" and not other[0]["is_body"]
    def test_tipos_expandidos(self):
        body, _ = parse_params(["body.a:s?","body.b:i?","body.c:b?","body.d:a?","body.e:o?"])
        tipos = {p["name"]: p["type"] for p in body}
        assert tipos == {"a":"string","b":"integer","c":"boolean","d":"array","e":"object"}
    def test_invalido_ignorado(self):
        assert parse_params(["invalido",""]) == ([],[])

class TestRenderContract:
    def test_cabecalho(self, mapping):
        ops = filter_operations(mapping,None,None)
        c = render_contract(ops,"petstore-api",detect_auth(mapping),"completo")
        assert "CONTRACT:" in c and "petstore-api" in c
    def test_todas_operacoes(self, mapping):
        ops = filter_operations(mapping,None,None)
        c = render_contract(ops,"petstore-api",detect_auth(mapping),"completo")
        assert all(op in c for op in mapping)
    def test_auth_bearer(self, mapping):
        ops = filter_operations(mapping,"addPet",None)
        c = render_contract(ops,"petstore-api",{"scheme":"bearer"},"operação: addPet")
        assert "Bearer" in c and "Authorization" in c
    def test_sem_auth_placeholder(self, mapping):
        ops = filter_operations(mapping,"createUser",None)
        c = render_contract(ops,"petstore-api",{},"operação: createUser")
        assert "placeholder" in c.lower() or "não definida" in c
    def test_obrigatorio_marcado(self, mapping):
        ops = filter_operations(mapping,"addPet",None)
        c = render_contract(ops,"petstore-api",{"scheme":"bearer"},"operação: addPet")
        assert "obrigatório" in c
    def test_opcional_marcado(self, mapping):
        ops = filter_operations(mapping,"addPet",None)
        c = render_contract(ops,"petstore-api",{"scheme":"bearer"},"operação: addPet")
        assert "opcional" in c
    def test_full_url_presente(self, mapping):
        ops = filter_operations(mapping,"addPet",None)
        c = render_contract(ops,"petstore-api",{"scheme":"bearer"},"operação: addPet")
        assert "petstore3.swagger.io" in c
    def test_instrucoes_llm(self, mapping):
        ops = filter_operations(mapping,None,None)
        c = render_contract(ops,"petstore-api",detect_auth(mapping),"completo")
        assert "INSTRUÇÕES PARA O LLM" in c and "idiomático" in c
    def test_sem_params_reportado(self, mapping):
        ops = filter_operations(mapping,"getInventory",None)
        c = render_contract(ops,"petstore-api",{"scheme":"apikey"},"operação: getInventory")
        assert "nenhum" in c.lower()
    def test_scope_no_cabecalho(self, mapping):
        ops = filter_operations(mapping,None,"pet")
        c = render_contract(ops,"petstore-api",detect_auth(mapping),"tag: pet")
        assert "tag: pet" in c
