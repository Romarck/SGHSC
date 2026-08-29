"""
security/password_policy.py — Política de senha do SGHSC (Story S-06).

Regras (NFR-01):
  - Comprimento mínimo de 10 caracteres.
  - Complexidade: ao menos 3 das 4 classes (minúscula, maiúscula, dígito, símbolo).
  - Bloqueio de senhas óbvias/comuns (blocklist) e de senhas que contenham o
    próprio nome de usuário.

Uso:
  - `validar_senha(senha, username=...)` -> lista de mensagens de erro (vazia = OK).
  - `SenhaForte(...)` -> validador WTForms que reaproveita `validar_senha`.
"""

import re

# Comprimento mínimo (o @si sugeriu >= 10)
COMPRIMENTO_MINIMO = 10

# Senhas/prefixos óbvios bloqueados (comparação case-insensitive).
# Lista enxuta e focada nas mais recorrentes + termos do contexto hospitalar.
SENHAS_COMUNS = frozenset({
    "123456", "1234567", "12345678", "123456789", "1234567890",
    "senha", "senha123", "password", "passw0rd", "qwerty", "qwerty123",
    "admin", "admin123", "administrador", "abc123", "111111", "000000",
    "iloveyou", "sghsc", "sghsc123", "hospital", "santacasa", "mudar123",
    "trocar123", "master", "root", "usuario", "teste", "teste123",
})


def _classes_de_caractere(senha: str) -> int:
    """Conta quantas classes distintas (minúscula/maiúscula/dígito/símbolo) há."""
    tem_minuscula = bool(re.search(r"[a-z]", senha))
    tem_maiuscula = bool(re.search(r"[A-Z]", senha))
    tem_digito = bool(re.search(r"\d", senha))
    tem_simbolo = bool(re.search(r"[^A-Za-z0-9]", senha))
    return sum([tem_minuscula, tem_maiuscula, tem_digito, tem_simbolo])


def validar_senha(senha: str, username: str = None) -> list[str]:
    """
    Valida a senha contra a política. Retorna a lista de erros (vazia = válida).

    Args:
        senha: a senha em texto plano a validar.
        username: se informado, rejeita senhas que contenham o username.
    """
    erros: list[str] = []
    senha = senha or ""

    if len(senha) < COMPRIMENTO_MINIMO:
        erros.append(
            f"A senha deve ter no mínimo {COMPRIMENTO_MINIMO} caracteres."
        )

    if _classes_de_caractere(senha) < 3:
        erros.append(
            "A senha deve combinar ao menos 3 tipos: letras minúsculas, "
            "maiúsculas, números e símbolos."
        )

    if senha.lower() in SENHAS_COMUNS:
        erros.append("Essa senha é muito comum. Escolha uma senha diferente.")

    if username and len(username) >= 3 and username.lower() in senha.lower():
        erros.append("A senha não pode conter o seu nome de usuário.")

    return erros


# ---------------------------------------------------------------------------
# Validador WTForms
# ---------------------------------------------------------------------------

class SenhaForte:
    """
    Validador WTForms que aplica `validar_senha`.

    Levanta ValidationError com a primeira mensagem de problema encontrada.
    O username é obtido do campo indicado por `username_field`, se existir no form.
    """

    def __init__(self, username_field: str = None):
        self.username_field = username_field

    def __call__(self, form, field):
        from wtforms.validators import ValidationError

        username = None
        if self.username_field and hasattr(form, self.username_field):
            username = getattr(form, self.username_field).data
        # No fluxo autenticado (troca de senha) não há campo username no form;
        # o route pode validar com o current_user separadamente.

        erros = validar_senha(field.data or "", username=username)
        if erros:
            raise ValidationError(erros[0])
