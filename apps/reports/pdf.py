"""Generadores de Acta de Compromiso por dependencia.

Este modulo define una clase padre para generar PDFs de actas y tres clases
hijas, una por dependencia. La clase de Salas de Software conserva el contenido
actual del acta existente; las otras dependencias tienen contenido propio.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.common.choices import DepartmentChoices
from apps.monitors.models import PROJECT_CHOICES


# ---------------------------------------------------------------------------
# Colores institucionales
# ---------------------------------------------------------------------------
ROJO_UD = colors.HexColor("#8B1A1A")
VERDE_TABLA = colors.HexColor("#C5D9A4")
GRIS_BORDE = colors.HexColor("#888888")
NEGRO = colors.black


# ---------------------------------------------------------------------------
# Estilos de párrafo reutilizables
# ---------------------------------------------------------------------------
_BASE = getSampleStyleSheet()["Normal"]


def _style(**kwargs) -> ParagraphStyle:
    base = dict(
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=NEGRO,
        spaceAfter=0,
        spaceBefore=0,
    )
    base.update(kwargs)
    return ParagraphStyle("_", **base)


ESTILO_NORMAL = _style()
ESTILO_BOLD = _style(fontName="Helvetica-Bold")
ESTILO_TITULO = _style(fontName="Helvetica-Bold", fontSize=13, alignment=1, spaceAfter=2)
ESTILO_SUBTITULO = _style(fontName="Helvetica-Bold", fontSize=11, alignment=1, spaceAfter=4)
ESTILO_SECCION = _style(fontName="Helvetica-Bold", fontSize=9, spaceAfter=2)
ESTILO_ITEM = _style(fontSize=9, leftIndent=12)
ESTILO_HEADER_TABLA = _style(fontName="Helvetica-Bold", fontSize=8, alignment=1, textColor=NEGRO)
ESTILO_CELDA_TABLA = _style(fontSize=8, alignment=1)


STATIC_BRANDING_DIR = Path(__file__).resolve().parents[2] / "static" / "branding"


@dataclass
class HorarioMonitor:
    """Una fila de la tabla de horarios."""
    asignatura: str = "NO APLICA"
    grupo: str = "-"
    docente: str = "SALAS SISTEMAS"
    proyecto_curricular: str = "-"
    dia_hora: str = ""
    laboratorio: str = "608 Almacén"


@dataclass
class ActaCompromisoData:
    """Datos necesarios para generar el acta de compromiso."""
    semestre: str
    nombre_completo: str
    codigo: str
    correo: str
    numero_documento: str = ""
    proyecto_curricular: str = ""
    telefono: str = ""
    horarios: list[HorarioMonitor] = field(default_factory=list)
    logo_path: Path | None = None


@dataclass(frozen=True)
class ActDocumentData:
    """Datos de documento antiguo para compatibilidad de pruebas."""
    document_type: str
    full_name: str
    code: str
    email: str
    body: str
    extra_fields: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Contenido: Salas de Software
# ---------------------------------------------------------------------------

COMPROMISO_ITEMS = [
    ("1.", "La hora de llegada a la monitoria es cinco (5) minutos antes del inicio del turno asignado. "
           "Usted debe presentarse en el Almacén de Laboratorios de Ingeniería, anunciarse con uno de los "
           "laboratoristas y esperar las asignaciones de apertura de salas o entrega de equipos."),
    ("2.", "Se contará como retardo a partir de los primeros cinco (5) minutos posteriores al inicio de la "
           "jornada; con tres retardos acumulados se le pasará memorando y si reincide se cancelará la monitoria."),
    ("3.", "Si el monitor llega cinco (5) minutos tarde al inicio de su turno, se realizará el descuento de "
           "treinta (30) minutos de la franja monitoria asignada."),
    ("4.", "Si el monitor llega treinta (30) minutos tarde, se realizará el descuento de una (1) hora de la "
           "franja de monitoría asignada."),
    ("5.", "El monitor debe cumplir con la totalidad de la jornada asignada, permaneciendo en el almacén para "
           "apoyar las solicitudes de estudiantes y docentes, la apertura de salas, la entrega de equipos, entre otros."),
]

ACTIVIDADES_ITEMS = [
    ("1.", "Realizar la apertura y cierre de las salas de informática, garantizando que al inicio se encuentren "
           "en condiciones de orden, aseo y seguridad."),
    ("2.", "Controlar la entrega y recepción de equipos audiovisuales (video beams, periféricos), verificando que "
           "se encuentren completos, en buen estado y debidamente registrados."),
    ("3.", "Apoyar en la organización y control del almacén (Sala 608), manteniendo los equipos y materiales "
           "clasificados, identificados y en condiciones adecuadas para su uso."),
    ("4.", "Participar en los procesos de verificación de inventarios, actualizando registros y reportando "
           "novedades detectadas."),
    ("5.", "Colaborar con los técnicos en actividades de instalación y configuración de software según el "
           "cronograma académico o las solicitudes institucionales."),
    ("6.", "Apoyar en actividades de mantenimiento preventivo de equipos de cómputo (limpieza básica, validación "
           "de funcionamiento) y reportar oportunamente anomalías que requieran revisión especializada."),
    ("7.", "Apoyar en tareas de conectividad de red, como organización de cableado, revisión de puntos de "
           "conexión y reporte de fallas."),
    ("8.", "Mantener actualizados los registros digitales y bases de datos correspondientes a la apertura de "
           "salas, préstamos y devoluciones de equipos y materiales."),
    ("9.", "Atender y brindar soporte técnico básico a docentes y estudiantes en el uso de los equipos, software "
           "y recursos de las salas de informática, orientando las solicitudes y canalizando los casos que "
           "requieran soporte especializado."),
    ("10.", "Garantizar la trazabilidad de todos los procesos de apoyo mediante el uso de formatos, registros "
            "digitales y controles establecidos por el laboratorio."),
    ("11.", "Colaborar en actividades extraordinarias, tales como preparación de equipos para eventos académicos, "
            "simulaciones, capacitaciones o pruebas especiales que requieran soporte adicional."),
    ("12.", "Realizar rondas periódicas en las salas de informática para verificar el correcto uso de los equipos, "
            "el cumplimiento de las normas de uso y el adecuado funcionamiento de los recursos durante la jornada académica."),
    ("13.", "Informar inmediatamente al personal del laboratorio cualquier situación irregular detectada en el "
            "desarrollo de las actividades, dejando constancia en el registro correspondiente."),
    ("14.", "Verificar diariamente el estado físico de las salas de informática, incluyendo equipos, mobiliario y "
            "condiciones generales, reportando oportunamente cualquier anomalía detectada."),
    ("15.", "Apoyar en el desarrollo e implementación de proyectos orientados a mejorar la gestión, automatización "
            "y control de los procesos de los laboratorios, así como la organización, registro y visualización de la "
            "información para facilitar el seguimiento y la toma de decisiones."),
]

DEBERES_ITEMS = [
    ("1.", "Velar por el buen uso de los equipos y mobiliario de la sala, evitando daños, movimientos no "
           "autorizados o usos indebidos."),
    ("2.", "Prohibir el consumo de alimentos o bebidas dentro de las salas."),
    ("3.", "No permitir el traslado de equipos de una sala a otra sin autorización expresa del personal del laboratorio."),
    ("4.", "Confirmar y reportar cualquier anomalía o daño de equipos al personal del laboratorio, verificando "
           "previamente la situación antes de emitir el reporte."),
    ("5.", "Informar oportunamente cualquier irregularidad en los préstamos o en el uso de las salas, dejando "
           "constancia clara en el registro."),
    ("6.", "Brindar apoyo básico a estudiantes y docentes en el uso inicial de software, equipos audiovisuales y "
           "computadores, canalizando solicitudes complejas al personal técnico."),
    ("7.", "Garantizar que los equipos audiovisuales entregados (video beams, periféricos, etc.) se devuelvan "
           "completos, en buen estado y dentro del tiempo asignado."),
    ("8.", "Apoyar en la conectividad de red en las salas cuando sea requerido, asegurando que el cableado y los "
           "puntos de conexión estén en orden."),
    ("9.", "Apoyar la correcta utilización de las credenciales institucionales, software con licencia y recursos "
           "de red, evitando usos indebidos."),
    ("10.", "Apoyar en el desarrollo de inventarios periódicos de equipos y materiales de las salas de informática "
            "y del almacén."),
    ("11.", "Promover el cuidado colectivo de los equipos, recordando a los estudiantes las normas de uso y disciplina."),
    ("12.", "Evitar el uso personal de los equipos o tiempo de la monitoria en actividades no relacionadas con el servicio."),
    ("13.", "Estar disponible en todo momento de la jornada para atender requerimientos inmediatos de "
            "laboratoristas, docentes y estudiantes."),
    ("14.", "Mantener trato cordial, respetuoso y colaborativo con la comunidad universitaria, proyectando una "
            "actitud de servicio."),
    ("15.", "Cumplir con todas las instrucciones impartidas por los laboratoristas y la coordinación de "
            "laboratorios, asegurando la continuidad del servicio en las salas de informática."),
]

CAUSALES_ITEMS = [
    ("1.", "Realizar actividades personales que no corresponden a la práctica o clase durante su monitoria."),
    ("2.", "Ausentarse de la sala de informática y soporte técnico 609 sin previo aviso al personal."),
    ("3.", "NO ASISTIR A UNA MONITORIA (existen casos especiales como las salidas de campo, para esto debe "
           "pasarlo por escrito a la coordinación de Los Laboratorios de Ingeniería designando un compañero "
           "como reemplazo.)"),
    ("4.", "Llevarse las llaves de la sala se considera una falta gravísima (Recuerde que hay más clases "
           "programadas en ese espacio)."),
    ("5.", "No reportar el desorden o mal estado la sala (aseo, butacas, etc.)."),
    ("6.", "Permitir el ingreso de personal no autorizado."),
]


# ---------------------------------------------------------------------------
# Contenido: Física
# ---------------------------------------------------------------------------

COMPROMISO_FISICA_ITEMS = [
    ("1.", "La hora de llegada a la Monitoria es cinco (5) minutos antes de la hora par en la que inicia "
           "la clase o práctica. Usted debe presentarse en el Laboratorio de Física, anunciar su llegada "
           "al técnico o laboratorista de turno, registrar su hora de llegada en el formato de asistencia "
           "correspondiente y esperar al docente para dar apertura a la sala de Laboratorio donde se "
           "realizará la práctica."),
    ("2.", "El monitor deberá realizar el registro de sus horas de monitoria en el formato de control de "
           "asistencia dispuesto por los Laboratorios de Ingeniería, el cual se diligencia en el Almacén "
           "609 de Ingeniería, ubicado en el sexto (6°) piso. Este registro deberá realizarse por cada "
           "bloque correspondiente a dos (2) horas de monitoria, con el fin de llevar el control y la "
           "debida actualización de la asistencia de los monitores asignados durante el semestre académico."),
    ("3.", "Si el docente no llega o cancela el laboratorio, usted debe informar al personal del Laboratorio "
           "y permanecer disponible para apoyar actividades académicas o de organización general del "
           "Laboratorio, previa indicación. Por ningún motivo se puede ausentar sin previa autorización."),
    ("4.", "Se anotará retardo a partir de los primeros cinco (5) minutos después de la hora par; con tres "
           "retardos acumulados se le pasará un memorando y si reincide se cancelará la Monitoria."),
    ("5.", "Los Laboratorios deben entregarse puntualmente; por ello es importante que inicie el cierre de "
           "bancos con al menos <b>quince (15) minutos</b> de anticipación a la finalización de la práctica, "
           "evitando inconvenientes con el docente de la siguiente clase. Durante este proceso deberá "
           "verificar que el material prestado se encuentre completo y debidamente ubicado en su respectivo "
           "banco, así como comprobar que los formatos correspondientes hayan sido diligenciados correctamente "
           "el Formato SIGUD de préstamo de equipos (SOLICITUD DE MATERIALES, EQUIPOS E INSUMOS)."),
    ("6.", "Desde el momento en que recibe las llaves de la sala y/o de los bancos es responsable de su "
           "adecuado uso, control y custodia del espacio asignado durante el tiempo de la monitoria. Esto "
           "implica velar por el cumplimiento de las normas del laboratorio, supervisar que los bancos "
           "permanezcan organizados y cerrados cuando corresponda, y garantizar que el acceso al espacio se "
           "realice únicamente por parte de los estudiantes autorizados para la práctica."),
]

ACTIVIDADES_FISICA_ITEMS = [
    ("1.", "Revise el Laboratorio al recibirlo (seguridad, orden y aseo) e informa cualquier novedad al "
           "personal laboratorista."),
    ("2.", "Apoyar la apertura y disposición inicial del laboratorio bajo orientación del personal "
           "laboratorista, verificando condiciones generales del espacio sin asumir funciones técnicas "
           "especializadas."),
    ("3.", "Asegúrese de que cada estudiante entregue el banco en buen estado (aseo y orden)."),
    ("4.", "Usted debe entregar el Laboratorio en óptimas condiciones generales."),
    ("5.", "Recuerde pedir el carné al estudiante responsable del banco de trabajo <b>ANTES DE ABRIRLO.</b>"),
    ("6.", "Revise que las fichas que entrega a cada estudiante estén debidamente diligenciadas en esfero "
           "dentro del tiempo establecido."),
    ("7.", "Firme la carpeta de control de asistencia por cada monitoria (sin importar si hubo apertura de "
           "la sala), tanto al inicio como al final de la monitoria."),
    ("8.", "Recuérdale al docente firmar la carpeta correspondiente."),
    ("9.", "Dar apoyo durante el laboratorio al Docente y velar por el buen uso de los equipos por parte "
           "de los estudiantes, informando oportunamente cualquier anomalía del personal del Laboratorio."),
    ("10.", "Diligencie la base de datos a diario de cada una de las monitorias que realizó (solamente si "
            "se hizo la apertura de la sala para clase)."),
    ("11.", "Si pide las llaves de los bancos de trabajo debe revisarlos todos así no hayan sido asignadas "
            "a ningún estudiante; si hay anomalías realice la observación en su ficha de monitoria en el "
            "espacio de <b>observaciones</b> y comuníquelo al personal del Laboratorio."),
    ("12.", "Avisar al personal de Laboratorios de Física cuando se terminen las clases del semestre."),
    ("13.", "En caso de presentarse algún inconveniente o anomalía durante la Monitoria con los equipos y "
            "no tener carné de estudiante responsable; la Responsabilidad es del Monitor."),
    ("14.", "Apoyar cuando sea requerido, la organización general de los montajes previamente establecidos "
            "por el docente para la práctica, orientando a los estudiantes en la disposición adecuada de "
            "los elementos."),
    ("15.", "No se permite realizar dentro y sobre las mesas de los módulos, soldaduras, cortes y en general "
            "trabajos que dañen o puedan dañar las mesas de los bancos de trabajo. Utilizar las mesas "
            "ubicadas fuera de los laboratorios."),
]

DEBERES_INTRO_FISICA = (
    "Desde el momento que usted recibe las llaves de la sala y/o de los bancos es RESPONSABLE de esta. "
    "Por eso, es importante que siga atentamente las siguientes directrices:"
)

DEBERES_FISICA_ITEMS = [
    ("1.", "Asegúrese que los estudiantes revisen el banco asignado desde el inicio verificando que los "
           "equipos y el material se encuentren completos."),
    ("2.", "Los 15 primeros minutos usted podrá hacer reporte de cualquier anomalía encontrada y la "
           "responsabilidad es del Monitor que entregó la sala."),
    ("3.", "Los estudiantes que ingresan a la sala deben ser exclusivamente de la asignatura programada. "
           "En el caso de prácticas adicionales, deberán contar con la autorización previa del equipo de "
           "Laboratorios de Física, quienes realizarán la verificación en la base de datos y harán entrega "
           "de la ficha correspondiente para la asignación del banco de trabajo."),
    ("4.", "Debe existir un responsable por banco de trabajo, por lo cual usted debe exigir carné que lo "
           "acredite como estudiante activo de la Universidad Distrital F.J.C."),
    ("5.", "Indique a cada estudiante que diligencie la ficha con los datos completos, relacionando los "
           "equipos y material asignado en su banco de trabajo. En caso de requerir material adicional, "
           "este deberá registrarse en la misma ficha dentro de los primeros quince (15) minutos de "
           "iniciada la clase. Finalizado este tiempo, el monitor deberá recoger las fichas debidamente "
           "diligenciadas y anexarlas a los carnés previamente recolectados. En el caso de las prácticas "
           "adicionales, la entrega de equipos o material adicional solo se realizará durante los primeros "
           "treinta (30) minutos."),
    ("6.", "Está prohibido el consumo de bebidas o alimentos dentro de las salas."),
    ("7.", "En el caso de las Prácticas adicionales solo deben estar tres (3) estudiantes por banco de trabajo."),
    ("8.", "El monitor no puede estar acompañado de amigos o compañeros que no tengan asignado un banco "
           "de trabajo."),
    ("9.", "Los equipos deben permanecer siempre sobre el banco de trabajo; por ningún motivo deben "
           "ubicarse sobre sillas, butacas o en el piso."),
    ("10.", "No se permite el traslado de equipos de una sala a otra sin la autorización del personal del "
            "Laboratorio de Ingeniería o Laboratorios de Física."),
    ("11.", "Si algún estudiante reporta un equipo dañado del banco de trabajo que tiene asignado, usted "
            "deberá verificar inicialmente la situación antes de informar al personal del Laboratorio, sin "
            "realizar intervenciones técnicas. En caso de omitir el procedimiento establecido, podrá ser "
            "objeto de llamado de atención como monitor de la práctica o clase."),
    ("12.", "Exigir orden, aseo y disciplina por parte de los estudiantes dentro de la sala o laboratorio."),
    ("13.", "Por ningún motivo el banco de trabajo puede quedar solo y abierto; si un banco es abandonado, "
            "deberá cerrarlo inmediatamente y reportar la situación al personal de Laboratorios, reteniendo "
            "el carné correspondiente."),
    ("14.", "En el caso de las clases, el estudiante no podrá ausentarse por más de treinta (30) minutos "
            "sin autorización; de presentarse esta situación, deberá informar al personal del Laboratorio "
            "de Física salvo excepciones previamente autorizadas."),
]

CAUSALES_FISICA_ITEMS = [
    ("1.", "Realizar actividades personales que no correspondan a la práctica o clase durante el tiempo "
           "de monitoria."),
    ("2.", "Ausentarse del laboratorio sin previo aviso o autorización del personal del laboratorio."),
    ("3.", "NO ASISTIR A UNA MONITORIA PROGRAMADA. En casos especiales, como salidas de campo u otras "
           "actividades académicas, deberá informarlo previamente y por escrito, al personal de Laboratorios "
           "de Física y a la coordinación de los Laboratorios de Ingeniería, designando un compañero como "
           "reemplazo con la debida autorización."),
    ("4.", "Reportar un equipo para revisión sin haber verificado previamente su estado o sin emitir un "
           "concepto inicial sobre la novedad presentada."),
    ("5.", "No entregar las fichas de soporte de la monitoria cuando se haya realizado apertura de bancos "
           "de trabajo."),
    ("6.", "<b>Llevarse las llaves de la sala y/o de los bancos se considera una falta gravísima</b> "
           "teniendo en cuenta que hay más clases programadas en el mismo espacio y durante el día."),
    ("7.", "Entregar el laboratorio en desorden o en mal estado, sin verificar el aseo del espacio, la "
           "correcta ubicación de butacas y el cierre adecuado de los bancos de trabajo."),
    ("8.", "Abrir bancos sin pedir carné del estudiante que estará a cargo y/o revisarlos con anterioridad."),
    ("9.", "Permitir el ingreso de personal no autorizado o de estudiantes que no tengan asignado un banco "
           "de trabajo."),
]


class BaseCommitmentActPdfGenerator:
    """Clase padre para generar actas de compromiso en PDF."""

    welcome_text: ClassVar[str] = (
        "Bienvenido al equipo de monitorias. A continuacion encontrara las responsabilidades "
        "y compromisos asociados a su apoyo academico y administrativo."
    )
    deberes_intro: ClassVar[str] = (
        "Durante su turno, el monitor debe realizar tareas operativas y de apoyo que garanticen "
        "el cumplimiento de las actividades asignadas."
    )
    commitment_items: ClassVar[list[tuple[str, str]]] = [
        ("1.", "Cumplir puntualmente con los horarios asignados por la dependencia."),
        ("2.", "Registrar oportunamente sus marcaciones y reportar novedades al lider."),
        ("3.", "Atender con responsabilidad las instrucciones del personal encargado."),
    ]
    activity_items: ClassVar[list[tuple[str, str]]] = [
        ("1.", "Apoyar las actividades academicas, administrativas o de laboratorio asignadas."),
        ("2.", "Mantener actualizados los registros solicitados por la dependencia."),
    ]
    duty_items: ClassVar[list[tuple[str, str]]] = [
        ("1.", "Mantener trato respetuoso con estudiantes, docentes y personal administrativo."),
        ("2.", "Cuidar los recursos fisicos, tecnologicos y documentales asignados."),
    ]
    sanction_items: ClassVar[list[tuple[str, str]]] = [
        ("1.", "Incumplir horarios o abandonar el turno sin autorizacion."),
        ("2.", "Usar el tiempo de monitoria para actividades no relacionadas con el servicio."),
    ]
    # Texto de cierre tras causales (None = usar el genérico de generate_acta_compromiso)
    sanction_closing_text: ClassVar[str | None] = None
    # Texto de responsabilidad compartida (None = usar el genérico)
    responsibility_text: ClassVar[str | None] = None

    def __init__(self, data: ActaCompromisoData):
        self.data = data

    def generate(self) -> bytes:
        return generate_acta_compromiso(self.data, generator=self)

    def schedule_row_for(self, schedule) -> HorarioMonitor:
        return HorarioMonitor(
            asignatura=schedule.asignatura or "NO APLICA",
            grupo=schedule.grupo or "-",
            docente=schedule.docente or "DEPENDENCIA",
            proyecto_curricular=project_label(schedule.proyecto_curricular) or project_label(self.data.proyecto_curricular) or "-",
            dia_hora=format_schedule_day_time(schedule),
            laboratorio=schedule.location or "-",
        )


class SoftwareRoomsCommitmentActPdfGenerator(BaseCommitmentActPdfGenerator):
    """Generador de acta para Salas de Software."""

    welcome_text = (
        "Bienvenido al equipo de trabajo de los Laboratorios de la Facultad de Ingenieria, "
        "a continuacion, encontrara temas importantes para realizar su Monitoria Academica:"
    )
    commitment_items = COMPROMISO_ITEMS
    activity_items = ACTIVIDADES_ITEMS
    deberes_intro = (
        "Durante su turno, el monitor debe realizar tareas operativas y de apoyo que garanticen "
        "la apertura de salas, la entrega de equipos y el orden en los procesos del laboratorio. Como son:"
    )
    duty_items = DEBERES_ITEMS
    sanction_items = CAUSALES_ITEMS

    def schedule_row_for(self, schedule) -> HorarioMonitor:
        return HorarioMonitor(
            asignatura="NO APLICA",
            grupo="-",
            docente="SALAS SISTEMAS",
            proyecto_curricular="-",
            dia_hora=format_schedule_day_time(schedule),
            laboratorio=schedule.location or "608 Almacen",
        )


class PhysicsCommitmentActPdfGenerator(BaseCommitmentActPdfGenerator):
    """Generador de acta para monitores de Física.

    Contenido fiel al acta física firmada del semestre 2026-I.
    """

    welcome_text = (
        "Bienvenido al equipo de trabajo de los Laboratorios de la Facultad de Ingeniería, "
        "a continuación, encontrará temas importantes para realizar su Monitoria Académica:"
    )
    commitment_items = COMPROMISO_FISICA_ITEMS
    activity_items = ACTIVIDADES_FISICA_ITEMS
    deberes_intro = DEBERES_INTRO_FISICA
    duty_items = DEBERES_FISICA_ITEMS
    sanction_items = CAUSALES_FISICA_ITEMS

    sanction_closing_text = (
        "El incumplimiento de las disposiciones anteriormente mencionadas podrá generar llamados de "
        "atención por parte del personal de Laboratorios o de la coordinación de los Laboratorios de "
        "Ingeniería y, en caso de reincidencia, podrá derivar en la cancelación de la monitoria."
    )

    # Datos fijos de la responsable de Física
    RESPONSABLE_NOMBRE: ClassVar[str] = "Ma. Alejandra Buitrago Pacheco"
    RESPONSABLE_CC: ClassVar[str] = "1010003986"
    RESPONSABLE_CARGO: ClassVar[str] = "Asistencial Laboratorios de Física de la Facultad de Ingeniería"

    responsibility_text = (
        "RECUERDE QUE LA RESPONSABILIDAD SOBRE LOS EQUIPOS, MATERIALES, MOBILIARIO Y DEMÁS ELEMENTOS "
        "PERTENECIENTES A LOS LABORATORIOS ES COMPARTIDA, SIEMPRE Y CUANDO SE REALICE EL PROCESO "
        "ADECUADO DE VERIFICACIÓN, REGISTRO Y CONTROL ESTABLECIDO EN LOS FORMATOS Y PROCEDIMIENTOS "
        "DEL LABORATORIO.\n"
        "EN CASO DE NO REALIZARSE EL PROCEDIMIENTO CORRESPONDIENTE PARA LA ASIGNACIÓN, CONTROL Y "
        "ENTREGA DE EQUIPOS O BANCOS DE TRABAJO, LA RESPONSABILIDAD PODRÁ RECAER SOBRE EL MONITOR "
        "ENCARGADO DE LA PRÁCTICA."
    )

    def schedule_row_for(self, schedule) -> HorarioMonitor:
        return HorarioMonitor(
            asignatura="NO APLICA",
            grupo="-",
            docente="LABORATORIOS DE FÍSICA",
            proyecto_curricular=project_label(self.data.proyecto_curricular) or "-",
            dia_hora=format_schedule_day_time(schedule),
            laboratorio=schedule.location or "-",
        )


    def schedule_row_for(self, schedule) -> HorarioMonitor:
        return BaseCommitmentActPdfGenerator.schedule_row_for(self, schedule)


class ElectricalLabsCommitmentActPdfGenerator(BaseCommitmentActPdfGenerator):
    """Generador de acta para monitores de Laboratorios."""

    welcome_text = (
        "Bienvenido al equipo de monitorias de Laboratorios. Este documento establece los compromisos "
        "para apoyar practicas, equipos y espacios asignados por la dependencia."
    )
    activity_items =  [
    ("1.", "Revise el Laboratorio al recibirlo (seguridad, orden y aseo)."),
    
    ("2.", "Asegúrese de que cada estudiante entregue el banco en buen estado (aseo y orden)."),
    
    ("3.", "Usted debe entregar el Laboratorio en óptimas condiciones."),
    
    ("4.", "Recuerde pedir el carné al estudiante responsable del banco de trabajo <b><u>ANTES DE ABRIRLO</u></b>."),
    
    ("5.", "Revise que las fichas que le entrega a cada estudiante estén debidamente diligenciadas en esfero."),
    
    ("6.", "Firme la carpeta de control de asistencia por cada monitoria (sin importar si hubo apertura de la sala), tanto al inicio como al final de la monitoria."),
    
    ("7.", "Recuérdale al docente firmar la carpeta."),
    
    ("8.", "Dar apoyo durante el laboratorio al Docente y velar por el buen uso de los equipos que estén usando los estudiantes."),
    
    ("9.", "Diligencie la base de datos a diario de cada una de las monitorias que realizó (solamente si se hizo la apertura de la sala para clase)."),
    
    ("10.", "Si pide las llaves de los bancos de trabajo debe revisarlos todos así no hayan sido asignadas a ningún estudiante (si hay anomalías realice la observación en su ficha de monitoria y comuníquelo al personal del Laboratorio)."),
    
    ("11.", "Avisar al personal de Almacén cuando se terminen las clases del semestre."),
    
    ("12.", "En caso de presentarse algún inconveniente o anomalía durante la Monitoria con los equipos y no tener carné de estudiante responsable; la Responsabilidad es del Monitor."),
    
    ("13.", "No se permite realizar dentro y sobre las mesas de los módulos, soldaduras, cortes y en general trabajos que dañen o puedan dañar las mesas de los bancos de trabajo. Utilizar las mesas ubicadas fuera de los laboratorios."),
    
    ("14.", "Será <b>responsable del uso, cuidado y custodia</b> del chaleco que le sea asignado durante todo el tiempo que dure su monitoria."),
    ]

    duty_items = [
    ("1.", "Asegúrese que los estudiantes revisen el banco asignado desde el inicio (equipos y material completos)."),
    
    ("2.", "Los 15 primeros minutos usted podrá hacer reporte de cualquier anomalía que encuentre y la responsabilidad es del Monitor que entregó la sala."),
    
    ("3.", "Los estudiantes que ingresan a la sala deben ser exclusivamente de la asignatura ó en el caso de prácticas adicionales con la autorización de uno de los laboratoristas del Almacén quien les entrega ficha con la asignación de un banco después de haber revisado la base de datos."),
    
    ("4.", "Debe existir un responsable por banco de trabajo, por lo cual usted debe exigir carné que lo acredite como estudiante activo de la Universidad Distrital F.J.C. (revisar histórico de pagos)."),
    
    ("5.", "Indique a cada estudiante que diligencie la ficha con los datos completos, relacionando los equipos y material del banco de trabajo y si necesita material adicional debe relacionarlo en la ficha (recuerde que se realiza dentro de los primeros 15 minutos de inicio de la clase luego de este tiempo debe recoger las fichas y adjuntarlas al carné previamente recogidos). En el caso de las prácticas adicionales se entrega equipos o material solo en los primeros 30 minutos."),
    
    ("6.", "Está prohibido el consumo de bebidas o alimentos dentro de las salas."),
    
    ("7.", "En el caso de las Prácticas adicionales solo deben estar tres (3) estudiantes por banco de trabajo."),
    
    ("8.", "El monitor no puede estar acompañado de amigos o compañeros que no tengan asignado un banco de trabajo."),
    
    ("9.", "Los equipos siempre deben estar en el banco de trabajo (por ningún motivo sobre las sillas o butacas, o en el piso)."),
    
    ("10.", "No se permite el traslado de equipos de una sala a otra sin la autorización del personal del Laboratorio de Ingeniería."),
    
    ("11.", "Si algún estudiante hace el reporte de un equipo dañado del banco de trabajo que tiene asignado, usted debe verificar primero antes de informar al personal del Laboratorio verificando que realmente el equipo necesita revisión o mantenimiento y no que es por mal uso de este; si no se hace el debido proceso se hará acreedor de una sanción como monitor de la práctica o clase."),
    
    ("12.", "Exija orden, aseo y disciplina por parte de los estudiantes en la sala o laboratorio."),
    
    ("13.", "Por ningún motivo el banco de trabajo puede quedar solo y abierto, si se abandona de un banco, inmediatamente debe cerrar el banco y hacer el reporte al personal de Laboratorios reteniendo el carné."),
    
    ("14.", "En el caso de las clases el docente no se puede ausentar más de 30 minutos, de lo contrario debe hacer el reporte en el Almacén de Laboratorio (existen excepciones con autorización)."),
    
    ("15.", "<b>Es obligatorio portar el chaleco institucional durante toda la jornada de monitoria y en los espacios académicos en los que se desarrollen sus funciones.</b>"),
    ]


def _items_table(items: list[tuple[str, str]]) -> Table:
    """Convierte una lista de (numero, texto) en una tabla alineada."""
    data = [
        [
            Paragraph(num, _style(fontName="Helvetica", fontSize=9)),
            Paragraph(txt, ESTILO_NORMAL),
        ]
        for num, txt in items
    ]
    t = Table(data, colWidths=[10 * mm, None])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _horarios_table(horarios: list[HorarioMonitor]) -> Table:
    """Construye la tabla de horarios estilo el acta real."""
    headers = [
        Paragraph("", ESTILO_HEADER_TABLA),
        Paragraph("ASIGNATURA", ESTILO_HEADER_TABLA),
        Paragraph("GRUPO", ESTILO_HEADER_TABLA),
        Paragraph("DOCENTE", ESTILO_HEADER_TABLA),
        Paragraph("PROYECTO\nCURRICULAR", ESTILO_HEADER_TABLA),
        Paragraph("DÍA/HORA", ESTILO_HEADER_TABLA),
        Paragraph("LABORATORIO", ESTILO_HEADER_TABLA),
    ]
    rows = [headers]
    for i, h in enumerate(horarios, start=1):
        rows.append([
            Paragraph(str(i), ESTILO_CELDA_TABLA),
            Paragraph(h.asignatura, ESTILO_CELDA_TABLA),
            Paragraph(h.grupo, ESTILO_CELDA_TABLA),
            Paragraph(h.docente, ESTILO_CELDA_TABLA),
            Paragraph(h.proyecto_curricular, ESTILO_CELDA_TABLA),
            Paragraph(h.dia_hora, ESTILO_CELDA_TABLA),
            Paragraph(h.laboratorio, ESTILO_CELDA_TABLA),
        ])

    col_widths = [8 * mm, 32 * mm, 14 * mm, 28 * mm, 28 * mm, 28 * mm, 28 * mm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERDE_TABLA),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def project_label(value: str) -> str:
    return dict(PROJECT_CHOICES).get(value, value or "")


def format_schedule_day_time(schedule) -> str:
    return (
        f"{schedule.get_weekday_display()} "
        f"{schedule.start_time.strftime('%H:%M')} - {schedule.end_time.strftime('%H:%M')}"
    )


def generate_acta_compromiso(data: ActaCompromisoData, *, generator: BaseCommitmentActPdfGenerator | None = None) -> bytes:
    """Genera el PDF del acta de compromiso y retorna los bytes."""
    generator = generator or SoftwareRoomsCommitmentActPdfGenerator(data)
    buffer = io.BytesIO()

    W, H = letter
    margin = 18 * mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        pageCompression=0,
    )

    story: list = []

    logo_el = None
    if data.logo_path and data.logo_path.exists():
        logo_el = Image(str(data.logo_path), width=38 * mm, height=18 * mm)
        logo_el.hAlign = "LEFT"

    titulo_lines = [
        Paragraph(f"MONITORIAS {data.semestre}", ESTILO_TITULO),
        Paragraph("ACTIVIDADES, COMPROMISOS, DEBERES Y CAUSALES", ESTILO_SUBTITULO),
    ]

    if logo_el:
        story.append(logo_el)
        story.append(Spacer(1, 2 * mm))
    for p in titulo_lines:
        story.append(p)

    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>DATOS DEL MONITOR</b>", ESTILO_SECCION))
    story.append(Paragraph(f"NOMBRE COMPLETO: {data.nombre_completo}", ESTILO_NORMAL))
    story.append(Paragraph(f"CÓDIGO: {data.codigo}", ESTILO_NORMAL))
    story.append(Paragraph(f"No. DE DOCUMENTO: {data.numero_documento or '-'}", ESTILO_NORMAL))
    story.append(Paragraph(f"No. TELEFONO MÓVIL: {data.telefono or '-'}", ESTILO_NORMAL))
    story.append(Paragraph(f"PROYECTO CURRICULAR: {project_label(data.proyecto_curricular) or '-'}", ESTILO_NORMAL))
    story.append(Paragraph(
        f'CORREO ELECTRÓNICO: <font color="#0000EE"><u>{data.correo}</u></font>',
        ESTILO_NORMAL,
    ))
    story.append(Spacer(1, 3 * mm))

    story.append(_horarios_table(data.horarios))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>Respetado(a) Monitor(a):</b>", ESTILO_NORMAL))
    story.append(Paragraph(generator.welcome_text, ESTILO_NORMAL))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("<b>COMPROMISO DURANTE EL TIEMPO DE LA MONITORIA.</b>", ESTILO_SECCION))
    story.append(_items_table(generator.commitment_items))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("<b>ACTIVIDADES IMPORTANTES DURANTE SU MONITORIA</b>", ESTILO_SECCION))
    story.append(_items_table(generator.activity_items))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph(
        "<b>DEBERES DURANTE LA MONITORIA (LA CLASE O PRÁCTICA).</b>", ESTILO_SECCION,
    ))
    story.append(Paragraph(generator.deberes_intro, ESTILO_NORMAL))
    story.append(Spacer(1, 1 * mm))
    story.append(_items_table(generator.duty_items))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("<b>CAUSALES DE SANCIÓN O LLAMADO DE ATENCIÓN</b>", ESTILO_SECCION))
    story.append(_items_table(generator.sanction_items))
    story.append(Spacer(1, 3 * mm))

    # Párrafo de cierre de causales (específico por dependencia si existe)
    if generator.sanction_closing_text:
        story.append(Paragraph(generator.sanction_closing_text, ESTILO_NORMAL))
        story.append(Spacer(1, 3 * mm))

    # Párrafo de responsabilidad compartida
    if generator.responsibility_text:
        # Física usa texto en mayúsculas y negrita
        for line in generator.responsibility_text.split("\n"):
            story.append(Paragraph(f"<b>{line}</b>", ESTILO_NORMAL))
        story.append(Spacer(1, 3 * mm))
    else:
        story.append(Paragraph(
            "<b>RECUERDE QUE LA RESPONSABILIDAD DE LOS EQUIPOS ES COMPARTIDA, "
            "SI NO SE REALIZA EL PROCESO ADECUADO.</b>",
            ESTILO_NORMAL,
        ))
        story.append(Spacer(1, 3 * mm))

    story.append(Paragraph(
        "Teniendo en cuenta que leí, entendí y comprendí ACEPTO las normas y compromisos como Monitor "
        f"Académico para el semestre {data.semestre}",
        ESTILO_NORMAL,
    ))
    story.append(Spacer(1, 14 * mm))

    # Bloque de firmas: doble columna para Física, simple para el resto
    if isinstance(generator, PhysicsCommitmentActPdfGenerator):
        proyecto_label_str = project_label(data.proyecto_curricular) or "-"
        firma_data = [
            [
                HRFlowable(width="100%", thickness=0.8, color=NEGRO),
                "",
                HRFlowable(width="100%", thickness=0.8, color=NEGRO),
            ],
            [
                Paragraph(f"Firma Monitor/a: {data.nombre_completo}", _style(fontSize=8)),
                "",
                Paragraph(f"Firma responsable: {generator.RESPONSABLE_NOMBRE}", _style(fontSize=8)),
            ],
            [
                Paragraph(f"C.C. {data.numero_documento or '-'}", _style(fontSize=8)),
                "",
                Paragraph(f"C.C. {generator.RESPONSABLE_CC}", _style(fontSize=8)),
            ],
            [
                Paragraph(f"Estudiante Proyecto Curricular: {proyecto_label_str}", _style(fontSize=8)),
                "",
                Paragraph(generator.RESPONSABLE_CARGO, _style(fontSize=8)),
            ],
        ]
        firma_table = Table(firma_data, colWidths=[80 * mm, 15 * mm, None])
        firma_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(firma_table)
    else:
        firma_table = Table(
            [[HRFlowable(width="100%", thickness=0.8, color=NEGRO), ""]],
            colWidths=[60 * mm, None],
        )
        firma_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(firma_table)
        story.append(Paragraph("FIRMA", ESTILO_NORMAL))
        story.append(Paragraph(f"{data.nombre_completo}", ESTILO_NORMAL))
        story.append(Paragraph(f"C.C. {data.numero_documento or '-'}", ESTILO_NORMAL))

    def _add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRIS_BORDE)
        page = canvas.getPageNumber()
        canvas.drawRightString(W - margin, 8 * mm, f"Página {page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    return buffer.getvalue()


def generate_act_pdf(document: ActDocumentData) -> bytes:
    """Genera un PDF de acta usando el esquema antiguo de ActDocumentData."""
    data = ActaCompromisoData(
        semestre="2026-I",
        nombre_completo=document.full_name,
        codigo=document.code,
        correo=document.email,
        numero_documento=document.extra_fields.get("Numero de documento", ""),
        proyecto_curricular=document.extra_fields.get("Proyecto curricular", ""),
        telefono=document.extra_fields.get("Telefono", ""),
        horarios=[],
        logo_path=STATIC_BRANDING_DIR / "lab-logo.jpg",
    )
    return generate_acta_compromiso(data)


def commitment_act_generator_for_department(department: str) -> type[BaseCommitmentActPdfGenerator]:
    """Selecciona la clase generadora de acta segun dependencia."""
    return {
        DepartmentChoices.INFORMATICS_LABS: SoftwareRoomsCommitmentActPdfGenerator,
        DepartmentChoices.PHYSICS: PhysicsCommitmentActPdfGenerator,
        DepartmentChoices.ELECTRICAL: ElectricalLabsCommitmentActPdfGenerator,
    }.get(department, BaseCommitmentActPdfGenerator)


def build_monitor_commitment_act_pdf(*, monitor, user) -> bytes:
    """Genera el acta de compromiso para un monitor autenticado en Django."""
    monitor_user = getattr(monitor, "user", None)
    data = ActaCompromisoData(
        semestre=getattr(monitor, "semestre", "2026-I"),
        nombre_completo=monitor.full_name,
        codigo=monitor.codigo_estudiante,
        correo=getattr(monitor_user, "email", "") or getattr(user, "email", ""),
        numero_documento=monitor.numero_documento,
        proyecto_curricular=monitor.proyecto_curricular,
        telefono=monitor.telefono,
        horarios=[],
        logo_path=STATIC_BRANDING_DIR / "lab-logo.jpg",
    )
    generator_class = commitment_act_generator_for_department(monitor.department)
    generator = generator_class(data)
    schedules = list(monitor.schedules.filter(is_active=True).order_by("weekday", "start_time"))
    data.horarios = [generator.schedule_row_for(schedule) for schedule in schedules]
    if not data.horarios:
        data.horarios = [
            HorarioMonitor(
                asignatura="NO APLICA",
                grupo="-",
                docente="SALAS SISTEMAS" if monitor.department == DepartmentChoices.INFORMATICS_LABS else "DEPENDENCIA",
                proyecto_curricular="-" if monitor.department == DepartmentChoices.INFORMATICS_LABS else project_label(monitor.proyecto_curricular) or "-",
                dia_hora="Pendiente",
                laboratorio="608 Almacen" if monitor.department == DepartmentChoices.INFORMATICS_LABS else "-",
            )
        ]
    return generator.generate()
