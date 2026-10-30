import io

import pytest

from app import create_app, db, storage


def upload_falso(conteudo, nome_arquivo, content_type, client=None):
    if not storage.extensao_valida(nome_arquivo):
        raise ValueError("extensao de arquivo nao permitida")
    return f"https://fake-s3.local/gallery/{nome_arquivo}"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(storage, "upload_capa", upload_falso)
    app = create_app()
    app.config["TESTING"] = True

    conn = db.get_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM livros")
    conn.commit()
    conn.close()

    with app.test_client() as c:
        yield c


def criar_livro(client, titulo="Dom Casmurro", autor="Machado de Assis"):
    r = client.post("/livros", json={"titulo": titulo, "autor": autor})
    return r.get_json()["id"]


def test_home_responde_200(client):
    assert client.get("/").status_code == 200


def test_health_retorna_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_ready_conecta_no_banco(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ready"}


def test_criar_livro_retorna_201(client):
    r = client.post("/livros", json={"titulo": "O Hobbit", "autor": "J. R. R. Tolkien"})
    assert r.status_code == 201
    assert r.get_json()["titulo"] == "O Hobbit"


def test_criar_livro_sem_dados_retorna_400(client):
    r = client.post("/livros", json={"titulo": "", "autor": ""})
    assert r.status_code == 400


def test_listar_mostra_livro_criado(client):
    criar_livro(client, titulo="Memorias Postumas")
    lista = client.get("/livros").get_json()
    assert any(livro["titulo"] == "Memorias Postumas" for livro in lista)


def test_upload_capa_ok(client):
    livro_id = criar_livro(client)
    dados = {"capa": (io.BytesIO(b"imagem"), "capa.png")}
    r = client.post(f"/livros/{livro_id}/capa", data=dados, content_type="multipart/form-data")
    assert r.status_code == 200
    assert r.get_json()["capa_url"].startswith("https://fake-s3.local/")


def test_upload_sem_arquivo_retorna_400(client):
    livro_id = criar_livro(client)
    r = client.post(f"/livros/{livro_id}/capa", data={}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_upload_extensao_invalida_retorna_400(client):
    livro_id = criar_livro(client)
    dados = {"capa": (io.BytesIO(b"x"), "virus.exe")}
    r = client.post(f"/livros/{livro_id}/capa", data=dados, content_type="multipart/form-data")
    assert r.status_code == 400


def test_upload_livro_inexistente_retorna_404(client):
    dados = {"capa": (io.BytesIO(b"x"), "capa.png")}
    r = client.post("/livros/999/capa", data=dados, content_type="multipart/form-data")
    assert r.status_code == 404


def test_ver_capa_redireciona_para_s3(client):
    livro_id = criar_livro(client)
    dados = {"capa": (io.BytesIO(b"x"), "capa.png")}
    client.post(f"/livros/{livro_id}/capa", data=dados, content_type="multipart/form-data")

    r = client.get(f"/livros/{livro_id}/capa")
    assert r.status_code == 302
    assert r.headers["Location"].startswith("https://fake-s3.local/")


def test_ver_capa_sem_capa_retorna_404(client):
    livro_id = criar_livro(client)
    assert client.get(f"/livros/{livro_id}/capa").status_code == 404


def test_ver_capa_livro_inexistente_retorna_404(client):
    assert client.get("/livros/999/capa").status_code == 404


def test_home_serve_o_painel(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Livraria Cloud" in r.data
    r.close()


def test_info_expoe_configuracao_sem_segredos(client, monkeypatch):
    monkeypatch.setenv("AWS_BUCKET_NAME", "bucket-teste")
    monkeypatch.setenv("BUILD_ID", "42")
    dados = client.get("/info").get_json()
    assert dados["versao"] == "42"
    assert dados["bucket"] == "bucket-teste"
    assert not any("senha" in chave or "password" in chave for chave in dados)


def test_logs_registra_requisicoes(client):
    client.get("/health")
    ultimas = client.get("/logs").get_json()
    assert any(item["caminho"] == "/health" and item["status"] == 200 for item in ultimas)


def test_logs_ignora_polling_do_painel(client):
    client.get("/info", headers={"X-Painel": "1"})
    ultimas = client.get("/logs").get_json()
    assert not any(item["caminho"] == "/info" for item in ultimas)


def test_excluir_livro_ok(client):
    livro_id = criar_livro(client)
    assert client.delete(f"/livros/{livro_id}").status_code == 200
    lista = client.get("/livros").get_json()
    assert all(livro["id"] != livro_id for livro in lista)


def test_excluir_livro_inexistente_retorna_404(client):
    assert client.delete("/livros/999").status_code == 404
