# ADR-002 — Assinatura digital via pyHanko com certificado A1 no servidor

**Status:** Aceito (retroativo)
**Data:** 2026-08-28
**Autor:** @architect
**Contexto de origem:** decisão implícita promovida a ADR durante o `*audit`

---

## Contexto

Documentos clínicos (prescrição, evolução, laudo de exame, laudo de alta, descrição
cirúrgica) precisam de assinatura digital com validade jurídica no padrão brasileiro
(ICP-Brasil / PAdES). O sistema roda em servidor (container), assinando documentos de
forma automatizada a partir de ações dos profissionais na interface web.

Restrições técnicas observadas: Python 3.12; dependências devem instalar sem compilação
Cython pesada; o servidor não tem token físico plugado.

## Decisão

Usar **pyHanko** (+ `cryptography`, `pyOpenSSL`) para assinatura **PAdES** de PDFs,
com **certificado A1** (arquivo `.p12`/`.pfx`) armazenado no servidor em
`CERT_STORAGE_PATH`. A senha do certificado **não** é persistida em texto puro.

- Serviço central: `app/services/cert_service.py` (`assinar_pdf`, `verificar_assinatura`,
  `gerar_qrcode_validacao`, `inspecionar_certificado`, `gerar_certificado_teste`).
- Carimbo de tempo (TSA) via `CERT_TIMESTAMP_URL` (Safeweb por padrão), com
  **degradação graciosa**: se o TSA estiver inacessível, assina sem timestamp e registra
  aviso no log.
- Em desenvolvimento, usa-se certificado **autoassinado RSA-2048** (`tipo=TESTE`),
  sem valor jurídico, apenas para validar o fluxo.

## Consequências

**Positivas**
- Pure Python, sem token físico no servidor; assinatura automatizada no fluxo web.
- PAdES detecta adulteração (cobertura `ENTIRE_FILE`).
- Troca do certificado de teste pelo A1 real não exige mudança de código (só upload).

**Negativas / trade-offs**
- A1 tem validade de ~1 ano e exige renovação; o arquivo no servidor é um ativo sensível.
- A3 (token/smartcard) fica inviável no backend (exige o dispositivo plugado).
- **Pendências conhecidas:** fluxo de PIN do A1 real em produção; ativação da validação
  da **cadeia** ICP-Brasil (`trust_roots`) — hoje só a integridade é verificada.

## Alternativas consideradas

- **A3 (token/smartcard):** maior segurança da chave, porém inviável em servidor headless.
- **Bibliotecas com binding PKCS#11 (`python-pkcs11`):** não compilava de forma estável no
  Python 3.12; descartada. Integração A3 futura via driver do fabricante no SO.
- **Certificado em nuvem (BirdID/RemoteID):** documentado como evolução futura; depende de
  contrato com certificadora.

## Referências
- `app/services/cert_service.py`, `app/models/certificado.py`
- `docs/PROJECT_STATE.md` — Fase 4 e "Como Adquirir um Certificado ICP-Brasil"
