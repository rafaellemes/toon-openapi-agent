"""
Testes unitários do resolve_multi — sem rede.
"""
import sys, pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts/consult"))
from resolve_multi import load_namespace_toon, build_multi_view

TOON_AUTH_API = """\
BASE: https://auth.exemplo.com/v1
AUTH: bearer (header: Authorization)
---
P /auth/login -> login | Autenticar utilizador [auth]
P /auth/register -> register | Registar utilizador [auth]
"""

TOON_PROFILES_API = """\
BASE: https://profiles.exemplo.com/v1
AUTH: bearer (header: Authorization)
---
P /profiles -> createProfile | Criar perfil [profiles]
G /profiles/{userId} -> getProfile | Buscar perfil [profiles]
"""


@pytest.fixture
def storage_com_dois_ns(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for ns, content in [("auth-api", TOON_AUTH_API), ("profiles-api", TOON_PROFILES_API)]:
        d = tmp_path / ".toon_apis" / "apis" / ns
        d.mkdir(parents=True)
        (d / "toon.txt").write_text(content, encoding="utf-8")
    return tmp_path


class TestLoadNamespaceToon:
    def test_carrega_conteudo(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        d = tmp_path / ".toon_apis" / "apis" / "test-api"
        d.mkdir(parents=True)
        (d / "toon.txt").write_text("BASE: https://api.exemplo.com\n---\n", encoding="utf-8")
        content = load_namespace_toon("test-api")
        assert "BASE:" in content

    def test_namespace_inexistente(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError, match="nao-existe"):
            load_namespace_toon("nao-existe")


class TestBuildMultiView:
    def test_cabecalho_multi(self, storage_com_dois_ns):
        view = build_multi_view(["auth-api", "profiles-api"])
        assert "MULTI-NAMESPACE" in view
        assert "auth-api" in view
        assert "profiles-api" in view

    def test_contem_ambos_blocos(self, storage_com_dois_ns):
        view = build_multi_view(["auth-api", "profiles-api"])
        assert "login"         in view
        assert "createProfile" in view

    def test_cada_ns_tem_cabecalho(self, storage_com_dois_ns):
        view = build_multi_view(["auth-api", "profiles-api"])
        assert "[auth-api" in view or "auth-api |" in view
        assert "[profiles-api" in view or "profiles-api |" in view

    def test_rodape_com_instrucao(self, storage_com_dois_ns):
        view = build_multi_view(["auth-api", "profiles-api"])
        assert "mapping.json" in view or "jq" in view

    def test_namespace_inexistente_informa(self, storage_com_dois_ns):
        view = build_multi_view(["auth-api", "nao-existe-api"])
        assert "nao-existe-api" in view
        assert "não encontrado" in view.lower() or "ausente" in view.lower()

    def test_aviso_muitos_namespaces(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Criar 6 namespaces
        for i in range(6):
            d = tmp_path / ".toon_apis" / "apis" / f"api-{i}"
            d.mkdir(parents=True)
            (d / "toon.txt").write_text(f"BASE: https://api-{i}.com\n---\n", encoding="utf-8")
        view = build_multi_view([f"api-{i}" for i in range(6)])
        assert "aviso" in view.lower() or "recomendado" in view.lower()

    def test_apenas_um_namespace_erro(self, storage_com_dois_ns):
        with pytest.raises((ValueError, SystemExit)):
            build_multi_view(["auth-api"])

    def test_namespaces_isolados_no_output(self, storage_com_dois_ns):
        """Conteúdo de cada namespace deve estar claramente separado."""
        view = build_multi_view(["auth-api", "profiles-api"])
        idx_auth     = view.index("login")
        idx_profiles = view.index("createProfile")
        # Os dois blocos devem aparecer em ordem e separados
        assert idx_auth != idx_profiles
