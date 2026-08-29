# ADR-006 — Validação pública de documentos via hash SHA-256 + QR Code

**Status:** Aceito (retroativo)
**Data:** 2026-08-28
**Autor:** @architect
**Contexto de origem:** decisão implícita promovida a ADR durante o `*audit`

---

## Contexto

Documentos assinados digitalmente (laudos, prescrições, altas) circulam em papel ou PDF
fora do sistema. Terceiros — o próprio paciente, outra unidade de saúde, um convênio —
precisam **conferir a autenticidade** de um documento sem ter acesso/login ao SGHSC.

## Decisão

Cada documento assinado registra um **hash SHA-256** do PDF e um **código de validação
curto** (`codigo_validacao`, único). Um **QR Code** aponta para uma rota **pública**
`/certificado/validar/<codigo>` (sem `@login_required`), que exibe os dados do documento
e permite conferir a integridade.

- Model `DocumentoAssinado`: `hash_documento` (SHA-256, indexado), `codigo_validacao`
  (unique, indexado), `pdf_path`, `qrcode_path`, vínculo ao assinante/paciente e
  referência polimórfica leve (`origem_tipo`/`origem_id`).
- Geração de QR via `cert_service.gerar_qrcode_validacao`.
- A cobertura PAdES (`ENTIRE_FILE`) garante que qualquer alteração posterior no PDF seja
  detectada na verificação.

## Consequências

**Positivas**
- Qualquer pessoa confere autenticidade sem credenciais — transparência e confiança.
- Código curto no QR mantém a URL legível; o hash garante integridade.
- Desacoplado do tipo de documento (referência polimórfica).

**Negativas / trade-offs**
- A rota pública precisa ser **cuidadosamente limitada** para não vazar dados sensíveis
  (LGPD): expor apenas o mínimo necessário para validação, sem PII clínica desnecessária.
- Referência polimórfica (`origem_tipo`/`origem_id`) não tem FK — integridade fica a
  cargo da aplicação (ver observação no `datamodel.md`).
- Convém futuramente **rate limiting** na rota pública para evitar enumeração de códigos.

## Alternativas consideradas

- **Validação apenas offline (verificar a assinatura no leitor de PDF):** correta, mas
  exige que o validador saiba/consiga fazer isso; o QR simplifica para o cidadão comum.
- **Portal autenticado para validação:** cria barreira de acesso desnecessária para um
  ato de conferência pública.

## Referências
- `app/models/certificado.py` (`DocumentoAssinado`)
- `app/routes/certificado.py` (rota pública `/validar/<codigo>`)
- `app/services/cert_service.py`
