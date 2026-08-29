"""
models/paciente.py — Modelo central do paciente.

Contém todos os dados demográficos, sociais, clínicos e de contato.
É o ponto de entrada de qualquer atendimento no SGHSC.
"""

import enum
from datetime import date, datetime, timezone

from ..extensions import db

# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------

class Sexo(enum.Enum):
    MASCULINO = "M"
    FEMININO = "F"
    INDEFINIDO = "I"


class RacaCor(enum.Enum):
    BRANCA = "branca"
    PRETA = "preta"
    PARDA = "parda"
    AMARELA = "amarela"
    INDIGENA = "indígena"
    NAO_DECLARADO = "não declarado"


class EstadoCivil(enum.Enum):
    SOLTEIRO = "solteiro"
    CASADO = "casado"
    UNIAO_ESTAVEL = "união estável"
    DIVORCIADO = "divorciado"
    VIUVO = "viúvo"
    SEPARADO = "separado"
    NAO_INFORMADO = "não informado"


class TipoSanguineo(enum.Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"
    DESCONHECIDO = "desconhecido"


class StatusPaciente(enum.Enum):
    ATIVO = "ativo"
    OBITO = "óbito"
    INATIVO = "inativo"


class TipoLogradouro(enum.Enum):
    RUA = "Rua"
    AVENIDA = "Avenida"
    TRAVESSA = "Travessa"
    ALAMEDA = "Alameda"
    ESTRADA = "Estrada"
    RODOVIA = "Rodovia"
    SITIO = "Sítio"
    FAZENDA = "Fazenda"
    OUTROS = "Outros"


# ---------------------------------------------------------------------------
# Modelo: Paciente
# ---------------------------------------------------------------------------

class Paciente(db.Model):
    """
    Paciente cadastrado no SGHSC.

    Cobre todos os campos exigidos pelo Ministério da Saúde para:
    - Ficha de atendimento ambulatorial (BPA)
    - Autorização de Internação Hospitalar (AIH)
    - Prontuário Eletrônico do Paciente (PEP / CFM)
    - Cadastro nacional de usuários do SUS (CNS)
    """
    __tablename__ = "pacientes"

    id = db.Column(db.Integer, primary_key=True)

    # ------------------------------------------------------------------
    # Identificação principal
    # ------------------------------------------------------------------
    nome = db.Column(db.String(200), nullable=False, index=True)
    nome_social = db.Column(db.String(200), nullable=True)   # Nome social (trans/gênero)
    data_nascimento = db.Column(db.Date, nullable=False, index=True)
    sexo = db.Column(db.Enum(Sexo), nullable=False)
    raca_cor = db.Column(db.Enum(RacaCor), default=RacaCor.NAO_DECLARADO)
    estado_civil = db.Column(db.Enum(EstadoCivil), default=EstadoCivil.NAO_INFORMADO)
    naturalidade = db.Column(db.String(100), nullable=True)    # Cidade de nascimento
    nacionalidade = db.Column(db.String(60), default="Brasileira")
    tipo_sanguineo = db.Column(db.Enum(TipoSanguineo), default=TipoSanguineo.DESCONHECIDO)
    status = db.Column(db.Enum(StatusPaciente), default=StatusPaciente.ATIVO, nullable=False)

    # ------------------------------------------------------------------
    # Documentos
    # ------------------------------------------------------------------
    cpf = db.Column(db.String(14), unique=True, nullable=True, index=True)
    rg = db.Column(db.String(20), nullable=True)
    rg_orgao_emissor = db.Column(db.String(20), nullable=True)
    rg_uf = db.Column(db.String(2), nullable=True)
    cns = db.Column(db.String(20), unique=True, nullable=True, index=True)  # Cartão Nacional de Saúde
    cns_provisorio = db.Column(db.String(20), nullable=True)
    certidao_nascimento = db.Column(db.String(40), nullable=True)
    titulo_eleitor = db.Column(db.String(20), nullable=True)

    # ------------------------------------------------------------------
    # Dados de saúde / clínicos
    # ------------------------------------------------------------------
    plano_saude = db.Column(db.String(100), nullable=True)
    numero_carteirinha = db.Column(db.String(50), nullable=True)
    alergias = db.Column(db.Text, nullable=True)         # Texto livre — alergias conhecidas
    observacoes_clinicas = db.Column(db.Text, nullable=True)
    data_obito = db.Column(db.Date, nullable=True)
    causa_obito = db.Column(db.String(300), nullable=True)

    # ------------------------------------------------------------------
    # Dados socioeconômicos
    # ------------------------------------------------------------------
    escolaridade = db.Column(db.String(60), nullable=True)
    ocupacao = db.Column(db.String(100), nullable=True)    # CBO
    religiao = db.Column(db.String(60), nullable=True)

    # ------------------------------------------------------------------
    # Endereço
    # ------------------------------------------------------------------
    cep = db.Column(db.String(9), nullable=True)
    tipo_logradouro = db.Column(db.Enum(TipoLogradouro), default=TipoLogradouro.RUA)
    logradouro = db.Column(db.String(200), nullable=True)
    numero = db.Column(db.String(10), nullable=True)
    complemento = db.Column(db.String(80), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    uf = db.Column(db.String(2), nullable=True)
    zona = db.Column(db.String(10), nullable=True)         # urbana / rural

    # ------------------------------------------------------------------
    # Contato
    # ------------------------------------------------------------------
    telefone = db.Column(db.String(20), nullable=True)
    telefone2 = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(150), nullable=True)

    # ------------------------------------------------------------------
    # Responsável / representante legal
    # ------------------------------------------------------------------
    responsavel_nome = db.Column(db.String(200), nullable=True)
    responsavel_grau = db.Column(db.String(50), nullable=True)   # mãe, pai, cônjuge, etc.
    responsavel_cpf = db.Column(db.String(14), nullable=True)
    responsavel_telefone = db.Column(db.String(20), nullable=True)

    # ------------------------------------------------------------------
    # Filiação
    # ------------------------------------------------------------------
    nome_mae = db.Column(db.String(200), nullable=True)
    nome_pai = db.Column(db.String(200), nullable=True)

    # ------------------------------------------------------------------
    # Auditoria
    # ------------------------------------------------------------------
    criado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    atualizado_em = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    # Autor do cadastro — trilha de escrita confiável (S-07). Preenchido a partir
    # do usuário autenticado no fluxo de criação (routes/pacientes.novo).
    criado_por_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False
    )

    # ------------------------------------------------------------------
    # Relacionamentos
    # ------------------------------------------------------------------
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_id])
    prontuario = db.relationship("Prontuario", back_populates="paciente", uselist=False)
    atendimentos_emergencia = db.relationship(
        "AtendimentoEmergencia", back_populates="paciente", lazy="dynamic"
    )
    consultas_ambulatoriais = db.relationship(
        "ConsultaAmbulatorial", back_populates="paciente", lazy="dynamic"
    )

    # ------------------------------------------------------------------
    # Propriedades calculadas
    # ------------------------------------------------------------------

    @property
    def idade(self) -> int | None:
        """Calcula idade em anos completos."""
        if not self.data_nascimento:
            return None
        hoje = date.today()
        anos = hoje.year - self.data_nascimento.year
        if (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day):
            anos -= 1
        return anos

    @property
    def nome_exibicao(self) -> str:
        """Retorna nome social se cadastrado, senão nome civil."""
        return self.nome_social or self.nome

    @property
    def endereco_formatado(self) -> str:
        partes = []
        if self.tipo_logradouro:
            partes.append(self.tipo_logradouro.value)
        if self.logradouro:
            partes.append(self.logradouro)
        if self.numero:
            partes.append(f"nº {self.numero}")
        if self.complemento:
            partes.append(self.complemento)
        if self.bairro:
            partes.append(self.bairro)
        if self.cidade:
            partes.append(f"{self.cidade}/{self.uf or ''}")
        if self.cep:
            partes.append(f"CEP {self.cep}")
        return ", ".join(partes) if partes else "Endereço não cadastrado"

    def __repr__(self):
        return f"<Paciente {self.id} — {self.nome}>"
