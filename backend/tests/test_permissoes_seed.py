"""
tests/test_permissoes_seed.py — Testes do seed idempotente de permissões (Story S-01).
"""

from app.extensions import db
from app.models.usuario import Perfil, Permissao, TipoPerfil
from app.security.permissoes import CATALOGO, seed_permissoes


def test_seed_cria_todas_as_permissoes(app):
    with app.app_context():
        total = Permissao.query.count()
        assert total == len(CATALOGO)


def test_seed_e_idempotente(app):
    """Rodar o seed duas vezes não duplica permissões nem cria associações extras."""
    with app.app_context():
        antes = Permissao.query.count()
        resumo = seed_permissoes()
        depois = Permissao.query.count()
        assert antes == depois
        assert resumo["permissoes_criadas"] == 0


def test_medico_tem_permissao_prescrever(app):
    with app.app_context():
        perfil = Perfil.query.filter_by(tipo=TipoPerfil.MEDICO).first()
        assert perfil is not None
        assert perfil.tem_permissao("internacao.prescrever")
        assert not perfil.tem_permissao("financeiro.ver")


def test_curinga_expande_modulo(app):
    """Farmacêutico recebe 'farmacia.*' → deve ter todas as permissões de farmácia.

    O perfil Farmacêutico agora é criado automaticamente por seed_perfis_padrao()
    (chamado dentro de seed_permissoes), então apenas o obtemos.
    """
    with app.app_context():
        perfil = Perfil.query.filter_by(tipo=TipoPerfil.FARMACEUTICO).first()
        assert perfil is not None, "seed deveria ter criado o perfil Farmacêutico"
        assert perfil.tem_permissao("farmacia.ver")
        assert perfil.tem_permissao("farmacia.gerir")
        assert perfil.tem_permissao("farmacia.dispensar")


def test_seed_cria_perfis_padrao(app):
    """seed_permissoes deve garantir os 15 perfis padrão no banco."""
    with app.app_context():
        assert Perfil.query.count() >= 15
