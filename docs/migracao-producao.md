# Procedimento de Migração de Banco — SGHSC (Story S-10)

> Princípio: **gerar** migração é atividade de **desenvolvimento** (com revisão
> humana e commit); **aplicar** migração em **produção** é apenas
> `flask db upgrade` de revisões já revisadas. Nunca autogerar schema no boot de
> produção.

---

## Como o boot se comporta (`entrypoint.sh`)

| `FLASK_ENV`   | O que o boot faz com o banco |
|---------------|------------------------------|
| `production`  | **Somente `flask db upgrade`** (aplica revisões commitadas). Se falhar, **aborta o boot** (exit 1) — não sobe a app com schema inconsistente. |
| dev / test    | Autogera (`flask db migrate -m auto`) por conveniência e aplica (`flask db upgrade`). |

---

## Fluxo recomendado

### 1. Desenvolvimento — gerar e revisar a migração
Após alterar os modelos (`app/models/*.py`):

```bash
docker compose exec app flask db migrate -m "descrição clara da mudança"
```

- **Revise** o arquivo gerado em `backend/migrations/versions/` (confira `upgrade()`
  e `downgrade()`; remova drops/alterações não intencionais).
- Rode a suíte e um `flask db upgrade` local para validar.
- **Commite** o arquivo de migração junto com a mudança de modelo.

### 2. Produção — aplicar a migração revisada

1. **Backup do banco ANTES de qualquer upgrade** (obrigatório):
   ```bash
   pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d_%H%M%S).sql
   # ou: docker compose exec db pg_dump -U sghsc_user sghsc > backup.sql
   ```
2. Faça o deploy da nova imagem. O boot em produção executa **apenas**
   `flask db upgrade` automaticamente.
3. Se o `upgrade` falhar, o container **não sobe** (exit 1) e registra erro claro.
   Restaure o backup se necessário e investigue a migração antes de tentar de novo.

### Aplicação manual (opcional, fora do boot)
```bash
docker compose exec app flask db upgrade      # aplica até o head
docker compose exec app flask db current      # revisão atual
docker compose exec app flask db heads         # deve haver 1 head
```

---

## Boas práticas

- **Uma revisão por mudança**, com mensagem descritiva e revisão em PR.
- Migrações que exigem backfill (ex.: coluna nova NOT NULL em tabela populada)
  devem ser feitas em passos: adicionar coluna nullable → popular → tornar NOT NULL.
- Nunca edite uma migração já aplicada em produção; crie uma nova.
- Garanta **um único head** (`flask db heads`) antes do deploy.
