"""
services/indicadores_service.py — Indicadores gerenciais hospitalares.

Agrega dados dos módulos assistenciais existentes para o dashboard gerencial:
ocupação, giro de leitos, média de permanência, produção assistencial.
"""

from datetime import date, datetime, timedelta, timezone

from ..models.ambulatorio import ConsultaAmbulatorial
from ..models.emergencia import AtendimentoEmergencia
from ..models.internacao import Internacao, Leito, StatusInternacao, StatusLeito
from ..models.paciente import Paciente


def indicadores_leitos() -> dict:
    """Taxa de ocupação e distribuição de status dos leitos."""
    leitos = Leito.query.filter_by(ativo=True).all()
    total = len(leitos)
    ocupados = sum(1 for l in leitos if l.status == StatusLeito.OCUPADO)
    livres = sum(1 for l in leitos if l.status == StatusLeito.LIVRE)

    taxa_ocupacao = round((ocupados / total * 100), 1) if total else 0.0

    # Distribuição por status (para gráfico)
    por_status = {}
    for l in leitos:
        por_status[l.status.value] = por_status.get(l.status.value, 0) + 1

    return {
        "total": total,
        "ocupados": ocupados,
        "livres": livres,
        "taxa_ocupacao": taxa_ocupacao,
        "por_status": por_status,
    }


def indicadores_internacao(dias: int = 30) -> dict:
    """Giro de leitos, média de permanência e altas no período."""
    inicio = datetime.now(timezone.utc) - timedelta(days=dias)

    ativas = Internacao.query.filter_by(status=StatusInternacao.ATIVA).count()
    altas = Internacao.query.filter(
        Internacao.alta_em.isnot(None),
        Internacao.alta_em >= inicio,
    ).all()
    obitos = sum(1 for i in altas if i.status == StatusInternacao.OBITO)

    # Média de permanência (dias) das internações com alta no período
    if altas:
        media_permanencia = round(sum(i.dias_internado for i in altas) / len(altas), 1)
    else:
        media_permanencia = 0.0

    # Giro de leitos = altas / nº de leitos no período
    total_leitos = Leito.query.filter_by(ativo=True).count()
    giro = round(len(altas) / total_leitos, 2) if total_leitos else 0.0

    return {
        "periodo_dias": dias,
        "internacoes_ativas": ativas,
        "altas_periodo": len(altas),
        "obitos_periodo": obitos,
        "media_permanencia": media_permanencia,
        "giro_leitos": giro,
    }


def indicadores_producao(dias: int = 30) -> dict:
    """Produção assistencial: atendimentos de emergência e consultas no período."""
    inicio = datetime.now(timezone.utc) - timedelta(days=dias)
    hoje = date.today()

    inicio_data = (hoje - timedelta(days=dias))
    atend_periodo = AtendimentoEmergencia.query.filter(
        AtendimentoEmergencia.chegada_em >= inicio
    ).count()
    consultas_periodo = ConsultaAmbulatorial.query.filter(
        ConsultaAmbulatorial.data >= inicio_data
    ).count()
    novos_pacientes = Paciente.query.filter(Paciente.criado_em >= inicio).count()

    return {
        "periodo_dias": dias,
        "atendimentos_emergencia": atend_periodo,
        "consultas_ambulatorio": consultas_periodo,
        "novos_pacientes": novos_pacientes,
    }


def dashboard_gerencial(dias: int = 30) -> dict:
    """Consolida todos os indicadores para o dashboard gerencial."""
    return {
        "leitos": indicadores_leitos(),
        "internacao": indicadores_internacao(dias),
        "producao": indicadores_producao(dias),
        "gerado_em": datetime.now(timezone.utc),
    }
