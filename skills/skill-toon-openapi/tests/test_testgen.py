"""
Testes unitários do gerador de testes — sem rede.
"""
import sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/testgen"))
from generate_tests import (
    build_happy_payload, build_missing_required_payload,
    GENERATORS, EXTENSIONS, DEFAULT_FRAMEWORKS
)

@pytest.fixture
def entry_addpet():
    return {"method":"POST","path":"/pet","full_url":"https://petstore3.swagger.io/api/v3/pet",
            "params_toon":["body.name:s!","body.status:s?"],
            "summary":"Add a new pet","tags":["pet"],"responses":["200","405"]}

@pytest.fixture
def entry_getpet():
    return {"method":"GET","path":"/pet/{petId}","full_url":"https://petstore3.swagger.io/api/v3/pet/1",
            "params_toon":["petId:i!"],"summary":"Find pet by ID","tags":["pet"],
            "responses":["200","400","404"]}

@pytest.fixture
def entry_sem_params():
    return {"method":"GET","path":"/store/inventory",
            "full_url":"https://petstore3.swagger.io/api/v3/store/inventory",
            "params_toon":[],"summary":"Returns inventories","tags":["store"],"responses":["200"]}

class TestBuildPayload:
    def test_happy_com_campos(self, entry_addpet):
        p = build_happy_payload(entry_addpet["params_toon"])
        assert "name" in p and "status" in p
    def test_happy_sem_body(self, entry_getpet):
        assert build_happy_payload(entry_getpet["params_toon"]) == {}
    def test_missing_remove_obrigatorio(self, entry_addpet):
        payload, omitted = build_missing_required_payload(entry_addpet["params_toon"])
        assert omitted == "name" and "name" not in payload
    def test_missing_sem_obrigatorios(self, entry_sem_params):
        _, omitted = build_missing_required_payload(entry_sem_params["params_toon"])
        assert omitted is None

class TestGeradores:
    def test_python_contem_requests(self, entry_addpet):
        code = GENERATORS["python"](entry_addpet, "addPet", "pytest")
        assert "requests" in code and "petstore3.swagger.io" in code
    def test_python_happy_path(self, entry_addpet):
        code = GENERATORS["python"](entry_addpet, "addPet", "pytest")
        assert "happy" in code.lower() or "200" in code
    def test_python_campo_ausente(self, entry_addpet):
        code = GENERATORS["python"](entry_addpet, "addPet", "pytest")
        assert "ausente" in code or "missing" in code.lower() or "400" in code
    def test_python_404_gera_nao_encontrado(self, entry_getpet):
        code = GENERATORS["python"](entry_getpet, "getPetById", "pytest")
        assert "404" in code
    def test_javascript_fetch(self, entry_addpet):
        code = GENERATORS["javascript"](entry_addpet, "addPet", "jest")
        assert "fetch" in code or "describe" in code
    def test_kotlin_suspend(self, entry_addpet):
        assert "suspend" in GENERATORS["kotlin"](entry_addpet, "addPet", "junit5")
    def test_go_func_test(self, entry_addpet):
        assert "func Test" in GENERATORS["go"](entry_addpet, "addPet", "testing")
    def test_ruby_rspec(self, entry_addpet):
        code = GENERATORS["ruby"](entry_addpet, "addPet", "rspec")
        assert "RSpec" in code or "describe" in code

class TestDispatcher:
    def test_linguagens_registadas(self):
        for lang in ["python","javascript","typescript","kotlin","go","ruby"]:
            assert lang in GENERATORS and lang in EXTENSIONS and lang in DEFAULT_FRAMEWORKS
    def test_geradores_callable(self):
        assert all(callable(fn) for fn in GENERATORS.values())
