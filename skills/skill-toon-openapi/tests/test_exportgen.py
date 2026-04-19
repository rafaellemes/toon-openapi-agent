"""
Testes unitários do exportador de contexto TooN — sem rede.
"""
import sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/export"))
from export_context import (
    build_export_block, detect_auth_from_mapping, filter_operations,
)

@pytest.fixture
def mapping():
    base = "https://petstore3.swagger.io/api/v3"
    return {
        "addPet": {
            "method": "POST", "path": "/pet", "base_url": base,
            "full_url": f"{base}/pet",
            "params_toon": ["body.name:s!", "body.status:s?"],
            "summary": "Add a new pet", "tags": ["pet"],
            "responses": ["200", "405"], "security": {"scheme": "bearer"},
        },
        "getPetById": {
            "method": "GET", "path": "/pet/{petId}", "base_url": base,
            "full_url": f"{base}/pet/{{petId}}",
            "params_toon": ["petId:i!"],
            "summary": "Find pet by ID", "tags": ["pet"],
            "responses": ["200", "404"], "security": {"scheme": "bearer"},
        },
        "getInventory": {
            "method": "GET", "path": "/store/inventory", "base_url": base,
            "full_url": f"{base}/store/inventory",
            "params_toon": [],
            "summary": "Returns inventories", "tags": ["store"],
            "responses": ["200"], "security": {"scheme": "apikey", "name": "X-Api-Key"},
        },
        "createUser": {
            "method": "POST", "path": "/user", "base_url": base,
            "full_url": f"{base}/user",
            "params_toon": ["body.username:s!", "body.email:s!", "body.age:i?"],
            "summary": "Create user", "tags": ["user"],
            "responses": ["200"], "security": {},
        },
    }


class TestDetectAuthFromMapping:
    def test_bearer(self, mapping):
        auth = detect_auth_from_mapping({"addPet": mapping["addPet"]})
        assert auth.get("scheme") == "bearer"

    def test_apikey(self, mapping):
        auth = detect_auth_from_mapping({"getInventory": mapping["getInventory"]})
        assert auth.get("scheme") == "apikey"

    def test_sem_auth(self, mapping):
        assert not detect_auth_from_mapping({"createUser": mapping["createUser"]}).get("scheme")

    def test_vazio(self):
        assert detect_auth_from_mapping({}) == {}


class TestFilterOperations:
    def test_completo(self, mapping):
        assert len(filter_operations(mapping, None, None)) == len(mapping)

    def test_por_tag(self, mapping):
        ops = filter_operations(mapping, None, "pet")
        assert "addPet" in ops and "getInventory" not in ops

    def test_tag_case_insensitive(self, mapping):
        assert "addPet" in filter_operations(mapping, None, "PET")

    def test_por_operation(self, mapping):
        ops = filter_operations(mapping, "addPet", None)
        assert list(ops.keys()) == ["addPet"]

    def test_operation_inexistente(self, mapping):
        with pytest.raises(KeyError):
            filter_operations(mapping, "naoExiste", None)

    def test_tag_inexistente(self, mapping):
        with pytest.raises(KeyError):
            filter_operations(mapping, None, "xxx")


class TestBuildExportBlockCompacto:
    """Testa o bloco padrão (sem --params)."""

    def _build(self, mapping, ops=None, auth=None, with_params=False):
        ops  = ops  or mapping
        auth = auth or detect_auth_from_mapping(mapping)
        return build_export_block(
            ops=ops,
            namespace="petstore-api",
            auth=auth,
            title="Swagger Petstore",
            base_url="https://petstore3.swagger.io/api/v3",
            with_params=with_params,
        )

    def test_cabecalho_api_e_base(self, mapping):
        block = self._build(mapping)
        assert "Swagger Petstore" in block
        assert "petstore3.swagger.io" in block

    def test_separadores_presentes(self, mapping):
        block = self._build(mapping)
        assert block.count("---") >= 2

    def test_metodo_path_operationid(self, mapping):
        block = self._build(mapping)
        assert "POST  /pet -> addPet" in block
        assert "GET   /pet/{petId} -> getPetById" in block

    def test_summary_presente(self, mapping):
        block = self._build(mapping)
        assert "Add a new pet" in block
        assert "Find pet by ID" in block

    def test_tags_presentes(self, mapping):
        block = self._build(mapping)
        assert "[pet]" in block

    def test_auth_bearer_descrita(self, mapping):
        block = self._build(mapping)
        assert "bearer" in block.lower() or "Bearer" in block

    def test_auth_nao_definida(self, mapping):
        block = build_export_block(
            ops={"createUser": mapping["createUser"]},
            namespace="petstore-api",
            auth={},
            title="Swagger Petstore",
            base_url="https://petstore3.swagger.io/api/v3",
            with_params=False,
        )
        assert "não definida" in block or "placeholder" in block.lower()

    def test_rodape_com_contagem(self, mapping):
        block = self._build(mapping)
        assert str(len(mapping)) in block

    def test_rodape_com_namespace(self, mapping):
        block = self._build(mapping)
        assert "petstore-api" in block

    def test_rodape_com_dica_uso(self, mapping):
        block = self._build(mapping)
        assert "toon-openapi" in block

    def test_sem_json_exposto(self, mapping):
        """Bloco não deve conter JSON bruto nem chaves de mapping."""
        block = self._build(mapping)
        assert '"full_url"'   not in block
        assert '"params_toon"' not in block
        assert '"responses"'  not in block


class TestBuildExportBlockComParams:
    """Testa o bloco com --params."""

    def _build_params(self, mapping, ops=None):
        ops  = ops or mapping
        auth = detect_auth_from_mapping(mapping)
        return build_export_block(
            ops=ops,
            namespace="petstore-api",
            auth=auth,
            title="Swagger Petstore",
            base_url="https://petstore3.swagger.io/api/v3",
            with_params=True,
        )

    def test_params_inline_presentes(self, mapping):
        block = self._build_params(mapping)
        # params_toon devem aparecer indentados após a linha da operação
        assert "body.name:s!" in block
        assert "body.status:s?" in block

    def test_params_path_presentes(self, mapping):
        block = self._build_params(mapping)
        assert "petId:i!" in block

    def test_sem_params_reportado(self, mapping):
        """Endpoint sem params deve indicar isso ou simplesmente não ter linha de params."""
        ops   = {"getInventory": mapping["getInventory"]}
        block = self._build_params(mapping, ops=ops)
        # Não deve conter params que não existem
        assert "body." not in block

    def test_estrutura_indentada(self, mapping):
        """Params devem aparecer indentados em relação à linha da operação."""
        block = self._build_params(mapping)
        lines = block.splitlines()
        addpet_idx = next(i for i, l in enumerate(lines) if "addPet" in l)
        # Próxima linha com conteúdo deve estar indentada
        next_content = next(l for l in lines[addpet_idx+1:] if l.strip())
        assert next_content.startswith("  ") or next_content.startswith("\t")


class TestBuildExportBlockEscopo:
    """Testa filtragem de escopo."""

    def test_por_tag_apenas_endpoints_da_tag(self, mapping):
        ops   = filter_operations(mapping, None, "pet")
        auth  = detect_auth_from_mapping(mapping)
        block = build_export_block(ops, "petstore-api", auth,
                                   "Swagger Petstore",
                                   "https://petstore3.swagger.io/api/v3", False)
        assert "addPet"      in block
        assert "getPetById"  in block
        assert "getInventory" not in block
        assert "createUser"  not in block

    def test_operacao_unica(self, mapping):
        ops   = filter_operations(mapping, "addPet", None)
        auth  = detect_auth_from_mapping(mapping)
        block = build_export_block(ops, "petstore-api", auth,
                                   "Swagger Petstore",
                                   "https://petstore3.swagger.io/api/v3", False)
        assert "addPet"     in block
        assert "getPetById" not in block

    def test_contagem_reflecte_escopo(self, mapping):
        ops   = filter_operations(mapping, None, "pet")  # 2 endpoints
        auth  = detect_auth_from_mapping(mapping)
        block = build_export_block(ops, "petstore-api", auth,
                                   "Swagger Petstore",
                                   "https://petstore3.swagger.io/api/v3", False)
        assert "2" in block  # contagem no rodapé
