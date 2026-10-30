import logging
import os
import socket
import sys
import time
from collections import deque
from datetime import datetime

from flask import Flask, g, jsonify, redirect, request

from . import db, storage

INICIO = time.time()


def buscar_livro(livro_id):
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, titulo, autor, capa_url FROM livros WHERE id = %s",
                (livro_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # capas de ate 5 MB
    db.init_db()

    # ---------- Observabilidade: logs no container e no painel ----------
    logger = logging.getLogger("livraria")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    ultimas_requisicoes = deque(maxlen=60)

    @app.before_request
    def marcar_inicio():
        g.inicio = time.perf_counter()

    @app.after_request
    def registrar_requisicao(resp):
        # O painel faz polling com este cabecalho; nao polui o log.
        if request.headers.get("X-Painel") == "1":
            return resp
        ms = int((time.perf_counter() - g.get("inicio", time.perf_counter())) * 1000)
        logger.info("%s %s -> %s (%d ms)", request.method, request.path, resp.status_code, ms)
        ultimas_requisicoes.append(
            {
                "hora": datetime.now().strftime("%H:%M:%S"),
                "metodo": request.method,
                "caminho": request.path,
                "status": resp.status_code,
                "ms": ms,
            }
        )
        return resp

    @app.route("/")
    def home():
        return app.send_static_file("index.html")

    @app.route("/info")
    def info():
        return jsonify(
            versao=os.environ.get("BUILD_ID", "local"),
            container=socket.gethostname(),
            uptime_segundos=int(time.time() - INICIO),
            db_host=os.environ.get("DB_HOST", "127.0.0.1"),
            db_nome=os.environ.get("DB_NAME", "livraria"),
            bucket=os.environ.get("AWS_BUCKET_NAME", ""),
            regiao=os.environ.get("AWS_REGION", "us-east-1"),
            prefixo=os.environ.get("STORAGE_PREFIX", "gallery"),
        )

    @app.route("/logs")
    def logs():
        return jsonify(list(reversed(ultimas_requisicoes)))

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    @app.route("/ready")
    def ready():
        try:
            conn = db.get_conn()
            conn.ping()
            conn.close()
            return jsonify(status="ready")
        except Exception as e:
            return jsonify(status="erro", detalhe=str(e)), 503

    @app.route("/livros", methods=["GET"])
    def listar():
        conn = db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, titulo, autor, capa_url FROM livros ORDER BY id")
                return jsonify(cur.fetchall())
        finally:
            conn.close()

    @app.route("/livros", methods=["POST"])
    def criar():
        dados = request.get_json(silent=True) or {}
        titulo = (dados.get("titulo") or "").strip()
        autor = (dados.get("autor") or "").strip()
        if not titulo or not autor:
            return jsonify(erro="titulo e autor sao obrigatorios"), 400

        conn = db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO livros (titulo, autor) VALUES (%s, %s)", (titulo, autor)
                )
                novo_id = cur.lastrowid
            conn.commit()
        finally:
            conn.close()
        return jsonify(id=novo_id, titulo=titulo, autor=autor), 201

    @app.route("/livros/<int:livro_id>", methods=["DELETE"])
    def excluir(livro_id):
        conn = db.get_conn()
        try:
            with conn.cursor() as cur:
                apagados = cur.execute("DELETE FROM livros WHERE id = %s", (livro_id,))
            conn.commit()
        finally:
            conn.close()
        if not apagados:
            return jsonify(erro="livro nao encontrado"), 404
        return jsonify(id=livro_id, removido=True)

    @app.route("/livros/<int:livro_id>/capa", methods=["POST"])
    def enviar_capa(livro_id):
        arquivo = request.files.get("capa")
        if arquivo is None or arquivo.filename == "":
            return jsonify(erro="envie o arquivo no campo 'capa'"), 400

        if buscar_livro(livro_id) is None:
            return jsonify(erro="livro nao encontrado"), 404

        try:
            url = storage.upload_capa(arquivo.read(), arquivo.filename, arquivo.mimetype)
        except ValueError as e:
            return jsonify(erro=str(e)), 400

        conn = db.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE livros SET capa_url = %s WHERE id = %s", (url, livro_id))
            conn.commit()
        finally:
            conn.close()
        return jsonify(id=livro_id, capa_url=url), 200

    @app.route("/livros/<int:livro_id>/capa", methods=["GET"])
    def ver_capa(livro_id):
        livro = buscar_livro(livro_id)
        if livro is None or not livro["capa_url"]:
            return jsonify(erro="capa nao encontrada"), 404
        return redirect(livro["capa_url"])

    return app
