# Livraria Cloud

Aplicação Flask que cadastra livros no Amazon RDS MySQL e guarda a capa de cada livro no Amazon S3.
Tem um painel web na raiz (`/`) para demonstrar o ambiente: estado da aplicação, do banco e do S3,
cadastro de livros com capa e registro das últimas requisições.

Pipeline no Azure DevOps: build com lint, testes com cobertura (Quality Gate de 100% em `storage.py`),
deploy em container Docker na EC2 e validação por health e readiness check.

## Rotas

| Rota | O que faz |
|------|-----------|
| `GET /` | Painel web |
| `GET /health` | A aplicação está respondendo |
| `GET /ready` | A aplicação está pronta (conecta no banco) |
| `GET /info` | Build, container, uptime, host do banco e bucket (sem senhas) |
| `GET /logs` | Últimas 60 requisições recebidas pelo container |
| `GET /livros`, `POST /livros` | Lista e cadastra livros |
| `DELETE /livros/<id>` | Remove o livro |
| `POST /livros/<id>/capa`, `GET /livros/<id>/capa` | Envia a capa ao S3 e abre a capa |

## Rodar localmente

```bash
pip install -r requirements.txt
# precisa de um MySQL local; ajuste as variáveis se necessário
export DB_HOST=127.0.0.1 DB_USER=root DB_PASSWORD=root DB_NAME=livraria
export AWS_BUCKET_NAME=seu-bucket AWS_REGION=us-east-1   # + credenciais AWS para o upload
flask --app "app:create_app" run --port 3000
```

Abra http://localhost:3000. Testes: `pytest tests/unit` e `pytest tests/integration` (este precisa do MySQL).
