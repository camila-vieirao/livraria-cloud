import os
import uuid

import boto3

EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg", "gif"}


def extensao_valida(nome_arquivo):
    if "." not in nome_arquivo:
        return False
    extensao = nome_arquivo.rsplit(".", 1)[1].lower()
    return extensao in EXTENSOES_PERMITIDAS


def get_s3_client():
    return boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def upload_capa(conteudo, nome_arquivo, content_type, client=None):
    if not extensao_valida(nome_arquivo):
        raise ValueError("extensao de arquivo nao permitida")

    extensao = nome_arquivo.rsplit(".", 1)[1].lower()
    bucket = os.environ["AWS_BUCKET_NAME"]
    regiao = os.environ.get("AWS_REGION", "us-east-1")
    prefixo = os.environ.get("STORAGE_PREFIX", "gallery")
    chave = f"{prefixo}/{uuid.uuid4().hex}.{extensao}"

    s3 = client or get_s3_client()
    s3.put_object(Bucket=bucket, Key=chave, Body=conteudo, ContentType=content_type)

    return f"https://{bucket}.s3.{regiao}.amazonaws.com/{chave}"
