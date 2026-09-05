# Story Q-SEC-01 — Autenticação em dois fatores (2FA/TOTP)

**Épico:** Segurança ISO 27001 (FR-SEC-01) — Controle **A.8.5** (autenticação segura)
**Prioridade:** P0 — bloqueia go-live SAAS
**Status:** A fazer
**Origem:** `docs/iso27001-gap-analysis.md`, consultoria do cliente
**Branch:** `quiron`
**Depende de:** Q-MT-00 (model de usuário ajustado)

---

## Contexto
Hoje o login é só usuário + senha. A ISO 27001 (A.8.5) e a proteção de dados de saúde pedem
um segundo fator para contas privilegiadas. **Decisão do cliente:** 2FA obrigatório **apenas
para Super-Admin e Administradores** (perfis clínicos ficam de fora para não travar estações
compartilhadas do hospital).

## Descrição
Como **Super-Admin/Administrador**, quero ativar 2FA por app autenticador (TOTP), para que o
acesso à minha conta exija um segundo fator além da senha.

## Critérios de Aceite
- [ ] TOTP via `pyotp` (compatível com Google Authenticator/Authy/etc.).
- [ ] Enrollment com **QR Code** (segredo gerado no servidor, exibido uma vez) + confirmação por código.
- [ ] `Usuario` guarda `totp_secret` (armazenado cifrado — ver Q-SEC-03) e `totp_habilitado`.
- [ ] **Obrigatório** para Super-Admin e Administradores: sem 2FA ativo, o login exige o
  enrollment antes de liberar o acesso.
- [ ] Fluxo de login: senha correta → pede código TOTP → valida (com janela de tolerância) → sessão.
- [ ] **Códigos de backup** (uso único) gerados no enrollment, para recuperação.
- [ ] Perfis clínicos **não** são forçados (podem ser habilitados opcionalmente no futuro).
- [ ] Eventos de 2FA (ativação, falha de código) entram na auditoria de segurança (Q-SEC-02).
- [ ] Testes: login com/sem 2FA, código inválido/expirado, backup code, enforcement por perfil.

## Tarefas
1. Adicionar `pyotp` (versão pinada) ao `requirements.txt`.
2. Campos no `Usuario` (`totp_secret` cifrado, `totp_habilitado`, códigos de backup) + migração.
3. Telas de enrollment (QR) e de verificação no login (`routes/auth.py` + templates).
4. Enforcement por perfil (Super-Admin/Administrador) no fluxo de login.
5. Códigos de backup (geração, armazenamento com hash, consumo único).
6. Testes (`tests/test_2fa.py`).

## Notas
- O `totp_secret` é dado sensível: cifrar em repouso (integra com Q-SEC-03).
- Rate limiting já existente no login (S-09) também protege a verificação do 2º fator.
- Recuperação de conta sem o dispositivo: via códigos de backup ou reset por outro admin/Super-Admin.
