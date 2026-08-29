"""
models/internacao.py — Módulo de Internação Hospitalar.

Fluxo: admissão → leito → prescrição médica → evolução/controles → alta
"""

import enum
from datetime import datetime, timezone

from ..extensions import db

# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------

class TipoLeito(enum.Enum):
    ENFERMARIA = "enfermaria"
    UTI_ADULTO = "UTI adulto"
    UTI_NEONATAL = "UTI neonatal"
    ISOLAMENTO = "isolamento"
    MATERNIDADE = "maternidade"
    PEDIATRIA = "pediatria"
    OBSERVACAO = "observação"
    CIRURGICO = "cirúrgico"
    SEMI_INTENSIVO = "semi-intensivo"


class StatusLeito(enum.Enum):
    LIVRE = "livre"
    OCUPADO = "ocupado"
    RESERVADO = "reservado"
    LIMPEZA = "limpeza"
    MANUTENCAO = "manutenção"
    BLOQUEADO = "bloqueado"


class TipoInternacao(enum.Enum):
    ELETIVA = "eletiva"
    URGENCIA = "urgência"
    EMERGENCIA = "emergência"
    OBSTETRICIA = "obstetrícia"
    PSIQUIATRIA = "psiquiatria"


class TipoAlta(enum.Enum):
    ALTA_MEDICA = "alta médica"
    ALTA_A_PEDIDO = "alta a pedido"
    TRANSFERENCIA = "transferência"
    OBITO = "óbito"
    EVASAO = "evasão"
    ALTA_ADMINISTRATIVA = "alta administrativa"


class CondicaoAlta(enum.Enum):
    CURADO = "curado"
    MELHORADO = "melhorado"
    INALTERADO = "inalterado"
    PIORADO = "piorado"
    OBITO = "óbito"


class StatusInternacao(enum.Enum):
    ATIVA = "ativa"
    ALTA = "alta"
    TRANSFERIDA = "transferida"
    OBITO = "óbito"


class ViaAdministracao(enum.Enum):
    ORAL = "VO"
    ENDOVENOSA = "EV"
    INTRAMUSCULAR = "IM"
    SUBCUTANEA = "SC"
    SUBLINGUAL = "SL"
    INALATORIA = "INL"
    TOPICA = "TOP"
    RETAL = "RET"
    NASAL = "NAS"
    OCULAR = "OFT"
    SONDA = "SNG/SNE"
    OUTRO = "outro"


class FrequenciaAdministracao(enum.Enum):
    UNICA = "dose única"
    SE_NECESSARIO = "se necessário"
    CADA_4H = "de 4/4h"
    CADA_6H = "de 6/6h"
    CADA_8H = "de 8/8h"
    CADA_12H = "de 12/12h"
    CADA_24H = "1x ao dia"
    CADA_48H = "a cada 48h"
    CONTINUO = "contínuo"
    OUTRO = "outro"


class TipoItemPrescricao(enum.Enum):
    MEDICAMENTO = "medicamento"
    SOLUCAO = "solução"
    DIETA = "dieta"
    CUIDADO = "cuidado"
    PROCEDIMENTO = "procedimento"
    CONSULTORIA = "consultoria"
    EXAME = "exame"
    HEMODERIVADO = "hemoderivado"


class StatusItemPrescricao(enum.Enum):
    ATIVO = "ativo"
    SUSPENSO = "suspenso"
    CONCLUIDO = "concluído"
    CANCELADO = "cancelado"


# ---------------------------------------------------------------------------
# Modelo: Leito
# ---------------------------------------------------------------------------

class Leito(db.Model):
    """
    Leito hospitalar. Unidade física de ocupação.
    O status é atualizado automaticamente nas operações de internação.
    """
    __tablename__ = "leitos"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    tipo = db.Column(db.Enum(TipoLeito), nullable=False)
    andar = db.Column(db.String(20), nullable=True)   # ex: "1º andar", "Térreo"
    ala = db.Column(db.String(50), nullable=True)     # ex: "Ala A", "Maternidade"
    quarto = db.Column(db.String(20), nullable=True)  # ex: "101", "202A"
    status = db.Column(db.Enum(StatusLeito), default=StatusLeito.LIVRE, nullable=False, index=True)
    isolamento = db.Column(db.Boolean, default=False, nullable=False)  # CCIH
    motivo_bloqueio = db.Column(db.String(200), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    internacoes = db.relationship("Internacao", back_populates="leito", lazy="dynamic")

    @property
    def internacao_ativa(self):
        """Retorna a internação ativa no leito, se houver."""
        return self.internacoes.filter_by(status=StatusInternacao.ATIVA).first()

    @property
    def cor_status(self) -> str:
        """Retorna classe CSS Bootstrap para o card do leito no mapa."""
        cores = {
            StatusLeito.LIVRE:      "success",
            StatusLeito.OCUPADO:    "danger",
            StatusLeito.RESERVADO:  "warning",
            StatusLeito.LIMPEZA:    "info",
            StatusLeito.MANUTENCAO: "secondary",
            StatusLeito.BLOQUEADO:  "dark",
        }
        return cores.get(self.status, "secondary")

    def __repr__(self):
        return f"<Leito {self.numero} — {self.status.value}>"


# ---------------------------------------------------------------------------
# Modelo: Internacao
# ---------------------------------------------------------------------------

class Internacao(db.Model):
    """
    Internação hospitalar. Cobre todo o ciclo: admissão → leito → alta.
    Vincula paciente, leito, prescrições e evoluções.
    """
    __tablename__ = "internacoes"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)

    # Vínculo
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)
    leito_id = db.Column(db.Integer, db.ForeignKey("leitos.id"), nullable=False)
    medico_responsavel_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    # Admissão
    admissao_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True
    )
    tipo = db.Column(db.Enum(TipoInternacao), nullable=False)
    motivo = db.Column(db.String(500), nullable=False)
    hipotese_diagnostica = db.Column(db.String(500), nullable=True)
    cid10_principal = db.Column(db.String(10), nullable=True)
    cid10_secundario = db.Column(db.String(10), nullable=True)
    convenio = db.Column(db.String(100), nullable=True)   # SUS, Unimed, etc.
    numero_aih = db.Column(db.String(20), nullable=True)  # AIH do SUS
    admitido_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    observacoes_admissao = db.Column(db.Text, nullable=True)

    # Origem (de onde veio o paciente)
    origem_pa = db.Column(db.Boolean, default=False)  # veio do PA
    atendimento_emergencia_id = db.Column(
        db.Integer, db.ForeignKey("atendimentos_emergencia.id"), nullable=True
    )

    # Status
    status = db.Column(db.Enum(StatusInternacao), default=StatusInternacao.ATIVA, nullable=False)

    # Alta
    alta_em = db.Column(db.DateTime(timezone=True), nullable=True)
    tipo_alta = db.Column(db.Enum(TipoAlta), nullable=True)
    condicao_alta = db.Column(db.Enum(CondicaoAlta), nullable=True)
    diagnostico_principal_alta = db.Column(db.String(500), nullable=True)
    resumo_alta = db.Column(db.Text, nullable=True)
    orientacoes_alta = db.Column(db.Text, nullable=True)
    retorno_dias = db.Column(db.Integer, nullable=True)
    alta_assinada = db.Column(db.Boolean, default=False)
    alta_pdf_path = db.Column(db.String(500), nullable=True)
    dado_alta_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    paciente = db.relationship("Paciente", foreign_keys=[paciente_id])
    leito = db.relationship("Leito", back_populates="internacoes")
    medico_responsavel = db.relationship("Usuario", foreign_keys=[medico_responsavel_id])
    admitido_por = db.relationship("Usuario", foreign_keys=[admitido_por_id])
    dado_alta_por = db.relationship("Usuario", foreign_keys=[dado_alta_por_id])
    atendimento_origem = db.relationship("AtendimentoEmergencia", foreign_keys=[atendimento_emergencia_id])

    prescricoes_medicas = db.relationship(
        "PrescricaoMedica", back_populates="internacao",
        order_by="PrescricaoMedica.criado_em.desc()", lazy="dynamic"
    )
    prescricoes_enfermagem = db.relationship(
        "PrescricaoEnfermagem", back_populates="internacao",
        order_by="PrescricaoEnfermagem.criado_em.desc()", lazy="dynamic"
    )
    controles = db.relationship(
        "ControlesPaciente", back_populates="internacao",
        order_by="ControlesPaciente.registrado_em.desc()", lazy="dynamic"
    )
    evolucoes_medicas = db.relationship(
        "EvolucaoMedica", back_populates="internacao",
        order_by="EvolucaoMedica.registrado_em.desc()", lazy="dynamic"
    )
    evolucoes_enfermagem = db.relationship(
        "EvolucaoEnfermagem", back_populates="internacao",
        order_by="EvolucaoEnfermagem.registrado_em.desc()", lazy="dynamic"
    )
    transferencias = db.relationship(
        "TransferenciaLeito", back_populates="internacao",
        order_by="TransferenciaLeito.realizada_em.desc()", lazy="dynamic"
    )

    @property
    def dias_internado(self) -> int:
        fim = self.alta_em or datetime.now(timezone.utc)
        inicio = self.admissao_em
        # Robustez a datetimes naive/aware. O SQLite (testes) devolve datetimes
        # sem timezone mesmo em colunas DateTime(timezone=True); normalizamos
        # para UTC-aware antes de subtrair para evitar TypeError.
        if inicio is not None and inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=timezone.utc)
        if fim.tzinfo is None:
            fim = fim.replace(tzinfo=timezone.utc)
        if inicio is None:
            return 0
        return max(0, (fim - inicio).days)

    @property
    def prescricao_ativa(self):
        """Última prescrição médica ativa."""
        return self.prescricoes_medicas.first()

    def __repr__(self):
        return f"<Internacao {self.numero} — {self.paciente.nome if self.paciente else '?'}>"


# ---------------------------------------------------------------------------
# Modelo: TransferenciaLeito
# ---------------------------------------------------------------------------

class TransferenciaLeito(db.Model):
    """Registro de cada transferência de leito dentro de uma internação."""
    __tablename__ = "transferencias_leito"

    id = db.Column(db.Integer, primary_key=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=False)
    leito_origem_id = db.Column(db.Integer, db.ForeignKey("leitos.id"), nullable=False)
    leito_destino_id = db.Column(db.Integer, db.ForeignKey("leitos.id"), nullable=False)
    motivo = db.Column(db.String(300), nullable=True)
    realizada_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    realizada_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    internacao = db.relationship("Internacao", back_populates="transferencias")
    leito_origem = db.relationship("Leito", foreign_keys=[leito_origem_id])
    leito_destino = db.relationship("Leito", foreign_keys=[leito_destino_id])
    realizada_por = db.relationship("Usuario", foreign_keys=[realizada_por_id])


# ---------------------------------------------------------------------------
# Modelo: PrescricaoMedica + ItemPrescricao
# ---------------------------------------------------------------------------

class PrescricaoMedica(db.Model):
    """
    Prescrição médica diária. Cada nova prescrição substitui a anterior.
    Pode ser assinada digitalmente (ICP-Brasil) via pyHanko.
    """
    __tablename__ = "prescricoes_medicas"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=False, index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    data_prescricao = db.Column(db.Date, nullable=False)
    validade_horas = db.Column(db.Integer, default=24, nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    ativa = db.Column(db.Boolean, default=True, nullable=False)

    # Assinatura digital ICP-Brasil
    assinada = db.Column(db.Boolean, default=False, nullable=False)
    assinada_em = db.Column(db.DateTime(timezone=True), nullable=True)
    assinatura_hash = db.Column(db.String(512), nullable=True)
    pdf_path = db.Column(db.String(500), nullable=True)

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    internacao = db.relationship("Internacao", back_populates="prescricoes_medicas")
    medico = db.relationship("Usuario", foreign_keys=[medico_id])
    itens = db.relationship(
        "ItemPrescricao", back_populates="prescricao",
        order_by="ItemPrescricao.ordem", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<PrescricaoMedica {self.numero} — {self.data_prescricao}>"


class ItemPrescricao(db.Model):
    """
    Item individual de uma prescrição médica.
    Pode ser medicamento, solução, dieta, cuidado, procedimento ou consultoria.
    """
    __tablename__ = "itens_prescricao"

    id = db.Column(db.Integer, primary_key=True)
    prescricao_id = db.Column(db.Integer, db.ForeignKey("prescricoes_medicas.id"), nullable=False, index=True)
    ordem = db.Column(db.Integer, default=1, nullable=False)  # ordem de exibição

    tipo = db.Column(db.Enum(TipoItemPrescricao), nullable=False)
    descricao = db.Column(db.String(300), nullable=False)   # nome do medicamento/item
    dose = db.Column(db.String(100), nullable=True)         # ex: "500mg", "100mL/h"
    via = db.Column(db.Enum(ViaAdministracao), nullable=True)
    frequencia = db.Column(db.Enum(FrequenciaAdministracao), nullable=True)
    frequencia_custom = db.Column(db.String(100), nullable=True)  # quando OUTRO
    duracao = db.Column(db.String(100), nullable=True)      # ex: "5 dias", "até nova ordem"
    horarios = db.Column(db.String(200), nullable=True)     # ex: "06h, 12h, 18h, 00h"
    diluicao = db.Column(db.String(200), nullable=True)     # ex: "diluir em 100mL SF"
    velocidade_infusao = db.Column(db.String(100), nullable=True)  # ex: "30 gotas/min"
    observacoes = db.Column(db.String(300), nullable=True)
    status = db.Column(db.Enum(StatusItemPrescricao), default=StatusItemPrescricao.ATIVO, nullable=False)
    suspenso_em = db.Column(db.DateTime(timezone=True), nullable=True)
    suspenso_motivo = db.Column(db.String(200), nullable=True)

    prescricao = db.relationship("PrescricaoMedica", back_populates="itens")

    def __repr__(self):
        return f"<ItemPrescricao {self.tipo.value}: {self.descricao}>"


# ---------------------------------------------------------------------------
# Modelo: PrescricaoEnfermagem
# ---------------------------------------------------------------------------

class PrescricaoEnfermagem(db.Model):
    """Prescrição de cuidados de enfermagem para a internação."""
    __tablename__ = "prescricoes_enfermagem"

    id = db.Column(db.Integer, primary_key=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=False, index=True)
    enfermeiro_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    data_prescricao = db.Column(db.Date, nullable=False)
    conteudo = db.Column(db.Text, nullable=False)   # lista de cuidados em texto estruturado
    observacoes = db.Column(db.Text, nullable=True)
    ativa = db.Column(db.Boolean, default=True, nullable=False)

    # Assinatura digital
    assinada = db.Column(db.Boolean, default=False)
    assinada_em = db.Column(db.DateTime(timezone=True), nullable=True)
    assinatura_hash = db.Column(db.String(512), nullable=True)
    pdf_path = db.Column(db.String(500), nullable=True)

    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    internacao = db.relationship("Internacao", back_populates="prescricoes_enfermagem")
    enfermeiro = db.relationship("Usuario", foreign_keys=[enfermeiro_id])


# ---------------------------------------------------------------------------
# Modelo: ControlesPaciente
# ---------------------------------------------------------------------------

class ControlesPaciente(db.Model):
    """
    Controles periódicos do paciente internado.
    Inclui sinais vitais, balanço hídrico e eliminações.
    Registrado a cada checagem de enfermagem (padrão: 6/6h ou horário).
    """
    __tablename__ = "controles_paciente"

    id = db.Column(db.Integer, primary_key=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=False, index=True)
    registrado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True
    )
    registrado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    # Sinais vitais
    pressao_sistolica = db.Column(db.Integer, nullable=True)
    pressao_diastolica = db.Column(db.Integer, nullable=True)
    frequencia_cardiaca = db.Column(db.Integer, nullable=True)
    frequencia_respiratoria = db.Column(db.Integer, nullable=True)
    temperatura = db.Column(db.Numeric(4, 1), nullable=True)
    saturacao_o2 = db.Column(db.Integer, nullable=True)
    glicemia_capilar = db.Column(db.Integer, nullable=True)
    escala_dor = db.Column(db.Integer, nullable=True)   # 0–10
    nivel_consciencia = db.Column(db.String(50), nullable=True)  # Glasgow / AVPU

    # Balanço hídrico — ENTRADAS (mL)
    soro_ev = db.Column(db.Integer, default=0)        # soroterapia EV
    medicacao_ev = db.Column(db.Integer, default=0)   # medicações EV diluídas
    ingesta_oral = db.Column(db.Integer, default=0)   # ingesta oral
    outros_entrada = db.Column(db.Integer, default=0) # drenos, lavagens, etc.

    # Balanço hídrico — SAÍDAS (mL)
    diurese = db.Column(db.Integer, default=0)
    drenos = db.Column(db.Integer, default=0)
    vomitos = db.Column(db.Integer, default=0)
    outros_saida = db.Column(db.Integer, default=0)

    # Eliminações
    evacuacao = db.Column(db.Boolean, default=False)
    evacuacao_caracteristicas = db.Column(db.String(200), nullable=True)

    observacoes = db.Column(db.Text, nullable=True)

    internacao = db.relationship("Internacao", back_populates="controles")
    registrado_por = db.relationship("Usuario", foreign_keys=[registrado_por_id])

    @property
    def total_entradas(self) -> int:
        return (self.soro_ev or 0) + (self.medicacao_ev or 0) + \
               (self.ingesta_oral or 0) + (self.outros_entrada or 0)

    @property
    def total_saidas(self) -> int:
        return (self.diurese or 0) + (self.drenos or 0) + \
               (self.vomitos or 0) + (self.outros_saida or 0)

    @property
    def balanco_hidrico(self) -> int:
        """Positivo = ganho hídrico. Negativo = perda hídrica."""
        return self.total_entradas - self.total_saidas

    @property
    def pressao_arterial(self) -> str:
        if self.pressao_sistolica and self.pressao_diastolica:
            return f"{self.pressao_sistolica}/{self.pressao_diastolica}"
        return "—"

    def __repr__(self):
        return f"<Controles {self.internacao_id} — {self.registrado_em}>"


# ---------------------------------------------------------------------------
# Modelo: EvolucaoMedica
# ---------------------------------------------------------------------------

class EvolucaoMedica(db.Model):
    """
    Evolução diária do médico durante a internação.
    Deve ser assinada digitalmente (documento com validade jurídica).
    """
    __tablename__ = "evolucoes_medicas"

    id = db.Column(db.Integer, primary_key=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=False, index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    registrado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True
    )

    subjetivo = db.Column(db.Text, nullable=True)    # Queixas, relato do paciente
    objetivo = db.Column(db.Text, nullable=True)     # Exame físico, resultados
    avaliacao = db.Column(db.Text, nullable=True)    # Hipótese/diagnóstico
    plano = db.Column(db.Text, nullable=True)        # Conduta planejada
    evolucao_livre = db.Column(db.Text, nullable=True)  # Campo livre (alternativo ao SOAP)

    cid10_atual = db.Column(db.String(10), nullable=True)

    # Assinatura digital ICP-Brasil
    assinada = db.Column(db.Boolean, default=False, nullable=False)
    assinada_em = db.Column(db.DateTime(timezone=True), nullable=True)
    assinatura_hash = db.Column(db.String(512), nullable=True)
    pdf_path = db.Column(db.String(500), nullable=True)

    internacao = db.relationship("Internacao", back_populates="evolucoes_medicas")
    medico = db.relationship("Usuario", foreign_keys=[medico_id])

    def __repr__(self):
        return f"<EvolucaoMedica {self.internacao_id} — {self.registrado_em}>"


# ---------------------------------------------------------------------------
# Modelo: EvolucaoEnfermagem
# ---------------------------------------------------------------------------

class EvolucaoEnfermagem(db.Model):
    """
    Evolução da equipe de enfermagem durante a internação.
    Registrada por turno (manhã, tarde, noite).
    """
    __tablename__ = "evolucoes_enfermagem"

    TURNOS = [
        ("manha", "Manhã (07h–13h)"),
        ("tarde", "Tarde (13h–19h)"),
        ("noite", "Noite (19h–07h)"),
    ]

    id = db.Column(db.Integer, primary_key=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey("internacoes.id"), nullable=False, index=True)
    profissional_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    registrado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True
    )
    turno = db.Column(db.String(10), nullable=True)  # manha, tarde, noite
    conteudo = db.Column(db.Text, nullable=False)
    observacoes = db.Column(db.Text, nullable=True)

    # Assinatura digital
    assinada = db.Column(db.Boolean, default=False)
    assinada_em = db.Column(db.DateTime(timezone=True), nullable=True)
    assinatura_hash = db.Column(db.String(512), nullable=True)
    pdf_path = db.Column(db.String(500), nullable=True)

    internacao = db.relationship("Internacao", back_populates="evolucoes_enfermagem")
    profissional = db.relationship("Usuario", foreign_keys=[profissional_id])

    def __repr__(self):
        return f"<EvolucaoEnfermagem {self.internacao_id} — {self.turno} {self.registrado_em}>"
