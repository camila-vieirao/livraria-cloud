# Livraria Cloud

API Flask que cadastra livros no Amazon RDS MySQL e guarda a capa de cada livro no Amazon S3.
Pipeline no Azure DevOps: build com lint, testes com cobertura (Quality Gate 100% em storage.py), deploy em container Docker na EC2 com health check.

Rotas: GET /, GET /health, GET /ready, GET e POST /livros, POST e GET /livros/<id>/capa.
