"""
Testes unitários do motor de diff — sem rede.
"""
import sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/diff"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/ingest"))
from diff_specs import diff_mappings, classify, render_report, extract_meta, slugify_label

@pytest.fixture
def mapping_v1():
    base = "https://api.exemplo.com/v1"
    return {
        "listUsers":  {"method": "GET",    "path": "/users",     "base_url": base,
                       "full_url": f"{base}/users",     "params_toon": ["page:i?"],
                       "summary": "Listar", "tags": ["users"], "responses": ["200"],
                       "security": {"scheme": "bearer"}},
        "createUser": {"method": "POST",   "path": "/users",     "base_url": base,
                       "full_url": f"{base}/users",     "params_toon": ["body.email:s!", "body.age:i?"],
                       "summary": "Criar",  "tags": ["users"], "responses": ["201", "400"],
                       "security": {"scheme": "bearer"}},
        "deleteUser": {"method": "DELETE", "path": "/users/{id}","base_url": base,
                       "full_url": f"{base}/users/{{id}}","params_toon": ["id:s!"],
                       "summary": "Remover","tags": ["users"], "responses": ["204", "404"],
                       "security": {"scheme": "bearer"}},
    }

@pytest.fixture
def mapping_v2():
    base = "https://api.exemplo.com/v2"
    return {
        "listUsers":  {"method": "GET",  "path": "/users",      "base_url": base,
                       "full_url": f"{base}/users",     "params_toon": ["page:i?", "limit:i?"],
                       "summary": "Listar", "tags": ["users"], "responses": ["200", "429"],
                       "security": {"scheme": "apikey"}},
        "createUser": {"method": "POST", "path": "/users",      "base_url": base,
                       "full_url": f"{base}/users",     "params_toon": ["body.email:s!", "body.role:s!"],
                       "summary": "Criar",  "tags": ["users"], "responses": ["201", "400", "422"],
                       "security": {"scheme": "apikey"}},
        "createBulk": {"method": "POST", "path": "/users/bulk", "base_url": base,
                       "full_url": f"{base}/users/bulk","params_toon": ["body.users:a!"],
                       "summary": "Bulk",   "tags": ["users"], "responses": ["201"],
                       "security": {"scheme": "apikey"}},
    }

class TestClassify:
    def test_breaking(self):
        for rule in ["endpoint_removed","param_type_changed","param_required_added",
                     "param_removed","method_changed","base_url_changed","auth_scheme_changed"]:
            label, _ = classify(rule)
            assert "BREAKING" in label
    def test_non_breaking(self):
        for rule in ["endpoint_added", "param_optional_added"]:
            label, _ = classify(rule)
            assert "NON-BREAKING" in label
    def test_info(self):
        label, _ = classify("summary_changed")
        assert "INFO" in label
    def test_desconhecida(self):
        label, _ = classify("inexistente")
        assert "INFO" in label

class TestDiffMappings:
    def test_adicionado(self, mapping_v1, mapping_v2):
        d = diff_mappings(mapping_v1, mapping_v2)
        assert "createBulk" in [i["op_id"] for i in d["added"]]
    def test_removido(self, mapping_v1, mapping_v2):
        d = diff_mappings(mapping_v1, mapping_v2)
        assert "deleteUser" in [i["op_id"] for i in d["removed"]]
    def test_modificados(self, mapping_v1, mapping_v2):
        d = diff_mappings(mapping_v1, mapping_v2)
        mods = [i["op_id"] for i in d["modified"]]
        assert "createUser" in mods and "listUsers" in mods
    def test_identicos(self, mapping_v1):
        d = diff_mappings(mapping_v1, mapping_v1)
        assert d["added"]==[] and d["removed"]==[] and d["modified"]==[]
        assert len(d["unchanged"]) == len(mapping_v1)
    def test_param_obrigatorio_breaking(self, mapping_v1, mapping_v2):
        d = diff_mappings(mapping_v1, mapping_v2)
        create = next(i for i in d["modified"] if i["op_id"]=="createUser")
        assert "param_required_added" in [c["rule"] for c in create["changes"]]
    def test_param_removido_breaking(self, mapping_v1, mapping_v2):
        d = diff_mappings(mapping_v1, mapping_v2)
        create = next(i for i in d["modified"] if i["op_id"]=="createUser")
        assert "param_removed" in [c["rule"] for c in create["changes"]]
    def test_param_opcional_non_breaking(self, mapping_v1, mapping_v2):
        d = diff_mappings(mapping_v1, mapping_v2)
        list_u = next(i for i in d["modified"] if i["op_id"]=="listUsers")
        assert "param_optional_added" in [c["rule"] for c in list_u["changes"]]

class TestExtractMeta:
    def test_base_url(self, mapping_v1):
        assert extract_meta(mapping_v1)["base_url"] == "https://api.exemplo.com/v1"
    def test_auth(self, mapping_v1):
        assert extract_meta(mapping_v1)["auth"] == "bearer"
    def test_vazio(self):
        m = extract_meta({})
        assert m["base_url"] == "" and m["auth"] == ""

class TestRenderReport:
    def _r(self, v1, v2):
        d = diff_mappings(v1, v2)
        return render_report(d,"v1","v2",extract_meta(v1),extract_meta(v2),"v1","v2")
    def test_cabecalho(self, mapping_v1, mapping_v2):
        assert "API Diff Report" in self._r(mapping_v1, mapping_v2)
    def test_resumo(self, mapping_v1, mapping_v2):
        r = self._r(mapping_v1, mapping_v2)
        assert "RESUMO" in r and "adicionados" in r
    def test_breaking_contabilizado(self, mapping_v1, mapping_v2):
        assert "breaking change" in self._r(mapping_v1, mapping_v2).lower()
    def test_marcadores(self, mapping_v1, mapping_v2):
        r = self._r(mapping_v1, mapping_v2)
        assert "[+]" in r and "[-]" in r and "[~]" in r
    def test_sem_diff(self, mapping_v1):
        d = diff_mappings(mapping_v1, mapping_v1)
        r = render_report(d,"v1","v1",extract_meta(mapping_v1),extract_meta(mapping_v1),"v1","v1")
        assert "Nenhuma diferença" in r
