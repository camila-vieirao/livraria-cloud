from unittest.mock import MagicMock

import pytest

from app import storage


@pytest.fixture
def bucket_env(monkeypatch):
    monkeypatch.setenv("AWS_BUCKET_NAME", "meu-bucket")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("STORAGE_PREFIX", "gallery")


def test_extensao_valida_aceita_png():
    assert storage.extensao_valida("foto.png") is True


def test_extensao_valida_aceita_maiusculas():
    assert storage.extensao_valida("FOTO.JPG") is True


def test_extensao_valida_rejeita_sem_ponto():
    assert storage.extensao_valida("semextensao") is False


def test_extensao_valida_rejeita_tipo_nao_permitido():
    assert storage.extensao_valida("script.exe") is False


def test_get_s3_client_usa_regiao_do_ambiente(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-2")
    chamada = MagicMock()
    monkeypatch.setattr(storage.boto3, "client", chamada)

    storage.get_s3_client()

    chamada.assert_called_once_with("s3", region_name="us-east-2")


def test_get_s3_client_usa_regiao_padrao(monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)
    chamada = MagicMock()
    monkeypatch.setattr(storage.boto3, "client", chamada)

    storage.get_s3_client()

    chamada.assert_called_once_with("s3", region_name="us-east-1")


def test_upload_capa_envia_ao_s3_com_cliente_informado(bucket_env):
    s3 = MagicMock()

    url = storage.upload_capa(b"conteudo", "capa.png", "image/png", client=s3)

    argumentos = s3.put_object.call_args.kwargs
    assert argumentos["Bucket"] == "meu-bucket"
    assert argumentos["Key"].startswith("gallery/")
    assert argumentos["Key"].endswith(".png")
    assert argumentos["Body"] == b"conteudo"
    assert argumentos["ContentType"] == "image/png"
    assert url.startswith("https://meu-bucket.s3.us-east-1.amazonaws.com/gallery/")


def test_upload_capa_usa_cliente_padrao_quando_nao_informado(bucket_env, monkeypatch):
    cliente_falso = MagicMock()
    monkeypatch.setattr(storage, "get_s3_client", lambda: cliente_falso)

    storage.upload_capa(b"conteudo", "capa.jpg", "image/jpeg")

    cliente_falso.put_object.assert_called_once()


def test_upload_capa_rejeita_extensao_invalida(bucket_env):
    s3 = MagicMock()

    with pytest.raises(ValueError):
        storage.upload_capa(b"conteudo", "virus.exe", "application/octet-stream", client=s3)

    s3.put_object.assert_not_called()
