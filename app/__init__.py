from flask import Flask, jsonify, redirect, request

from . import db, storage


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
    db.init_db()

    @app.route("/")
    def home():
        return "<h1>Livraria Cloud</h1><p><a href='/livros'>Ver livros</a></p>"

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
