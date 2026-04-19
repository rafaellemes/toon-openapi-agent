"""
Testes de integração com specs reais — requer internet.
OpenAPI 3.0: https://petstore3.swagger.io/api/v3/openapi.json  (via URL)
Swagger 2.0: tests/fixtures/swagger2_petstore.json              (via ficheiro)
"""
import json, subprocess, sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/ingest"))
from transform_toon import generate_artifacts, extract_base_url
from parse_spec import load_spec

pytestmark       = pytest.mark.integration
OPENAPI3_URL     = "https://petstore3.swagger.io/api/v3/openapi.json"
SWAGGER2_FIXTURE = Path(__file__).parent / "fixtures" / "swagger2_petstore.json"

@pytest.fixture(scope="session")
def spec_openapi3():
    spec = load_spec(OPENAPI3_URL)
    assert "error" not in spec
    return spec

@pytest.fixture(scope="session")
def spec_swagger2():
    assert SWAGGER2_FIXTURE.exists(), f"Fixture ausente: {SWAGGER2_FIXTURE}"
    return json.loads(SWAGGER2_FIXTURE.read_text(encoding="utf-8"))

class TestOpenApi3Url:
    def test_carregada(self, spec_openapi3):          assert "paths" in spec_openapi3
    def test_base_url(self, spec_openapi3):            assert extract_base_url(spec_openapi3).startswith("http")
    def test_toon_nao_vazio(self, spec_openapi3):
        toon, _ = generate_artifacts(spec_openapi3)
        assert any(l for l in toon.splitlines() if not l.startswith(("BASE","---")))
    def test_toon_tem_base(self, spec_openapi3):
        toon, _ = generate_artifacts(spec_openapi3)
        assert toon.startswith("BASE:")
    def test_toon_contem_pet(self, spec_openapi3):
        toon, _ = generate_artifacts(spec_openapi3)
        assert "/pet" in toon
    def test_mapping_addpet(self, spec_openapi3):
        _, m = generate_artifacts(spec_openapi3)
        assert "addPet" in m
    def test_addpet_full_url(self, spec_openapi3):
        _, m = generate_artifacts(spec_openapi3)
        assert m["addPet"]["full_url"].endswith("/pet")
        assert m["addPet"]["full_url"].startswith("http")
    def test_addpet_post(self, spec_openapi3):
        _, m = generate_artifacts(spec_openapi3)
        assert m["addPet"]["method"] == "POST"
    def test_getpetbyid_obrigatorio(self, spec_openapi3):
        _, m = generate_artifacts(spec_openapi3)
        assert any(p.endswith("!") for p in m["getPetById"]["params_toon"])
    def test_metodos_uppercase(self, spec_openapi3):
        _, m = generate_artifacts(spec_openapi3)
        validos = {"GET","POST","PUT","DELETE","PATCH","HEAD","OPTIONS"}
        assert all(e["method"] in validos for e in m.values())
    def test_full_urls_absolutas(self, spec_openapi3):
        _, m = generate_artifacts(spec_openapi3)
        assert all(e["full_url"].startswith("http") for e in m.values())

class TestSwagger2File:
    def test_e_swagger2(self, spec_swagger2):       assert spec_swagger2.get("swagger") == "2.0"
    def test_tem_host(self, spec_swagger2):          assert "host" in spec_swagger2
    def test_base_url(self, spec_swagger2):          assert extract_base_url(spec_swagger2).startswith("http")
    def test_host_na_base(self, spec_swagger2):      assert spec_swagger2["host"] in extract_base_url(spec_swagger2)
    def test_mapping_addpet(self, spec_swagger2):
        _, m = generate_artifacts(spec_swagger2)
        assert "addPet" in m
    def test_full_url_absoluta(self, spec_swagger2):
        _, m = generate_artifacts(spec_swagger2)
        assert m["addPet"]["full_url"].startswith("http")
    def test_pipeline_cli(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        scripts = Path(__file__).parent.parent / "scripts/ingest"
        parsed  = tmp_path / "parsed.json"
        r1 = subprocess.run([sys.executable, str(scripts/"parse_spec.py"), str(SWAGGER2_FIXTURE)],
                            capture_output=True, text=True)
        assert r1.returncode == 0
        parsed.write_text(r1.stdout, encoding="utf-8")
        spec = json.loads(r1.stdout)
        assert "error" not in spec and "paths" in spec
        r2 = subprocess.run([sys.executable, str(scripts/"transform_toon.py"), str(parsed)],
                            capture_output=True, text=True, cwd=str(tmp_path))
        assert r2.returncode == 0
        ns_dir = next((tmp_path/".toon_apis"/"apis").iterdir())
        assert (ns_dir/"toon.txt").exists() and (ns_dir/"mapping.json").exists()
        toon = (ns_dir/"toon.txt").read_text()
        assert "BASE:" in toon and "/pet" in toon
        m = json.loads((ns_dir/"mapping.json").read_text())
        assert "addPet" in m and m["addPet"]["full_url"].startswith("http")
