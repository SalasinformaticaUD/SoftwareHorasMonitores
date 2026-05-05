import re
from datetime import date, datetime, time
from pathlib import Path
from typing import Dict, List, Optional

from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date, parse_datetime, parse_time

from apps.common.utils import normalize_text

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm"}
HEADER_ALIASES = {
    "departamento": "department",
    "nro._usuario": "num_user",
    "nro_usuario": "num_user",
    "numero_de_usuario": "num_user",
    "numero_usuario": "num_user",
    "id_de_usuario": "id_user",
    "id_usuario": "id_user",
    "nombre": "full_name",
    "fecha_inicio": "entry_at",
    "fecha_fin": "exit_at",
    "descripciÃ³n_de_la_excepciÃ³n": "description",
    "descripcion_de_la_excepcion": "description",
    "descripci_n_de_la_excepci_n": "description",
    "descripcion": "description",
    "description": "description",
    "tiempo_trabajado": "worked_time",
    "dÃ­as_de_trabajo": "days_worked",
    "dias_de_trabajo": "days_worked",
    "d_as_de_trabajo": "days_worked",
    "days_worked": "days_worked",
    "tiempo_de_trabajo": "working_time",
    "working_time": "working_time",
    "observaciones": "observations",
    "observations": "observations",
}


def validate_excel_extension(file_name: str) -> None:
    if Path(file_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValidationError("Solo se permiten archivos Excel .xlsx o .xlsm.")


def normalize_header(value: str) -> str:
    normalized = normalize_text(str(value or ""))
    normalized = normalized.replace(" ", "_").replace("-", "_").replace("/", "_")
    normalized = re.sub(r"[^a-z0-9._]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_.")


def resolve_headers(headers: List[str]) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for index, header in enumerate(headers):
        alias = HEADER_ALIASES.get(normalize_header(str(header)))
        if alias and alias not in mapping:
            mapping[alias] = index
    missing = {
        "Departmento",
        "num_user",
        "id_user",
        "full_name",
        "entry_at",
        "exit_at",
        "description",
        "worked_time",
        "days_worked",
        "working_time",
        "observations",
    } - set(mapping)
    if missing:
        raise ValidationError(f"Encabezados faltantes en el Excel: {', '.join(sorted(missing))}.")
    return mapping


def coerce_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = parse_date(str(value))
    if parsed is None:
        raise ValidationError("No fue posible interpretar la fecha del registro.")
    return parsed


def coerce_time(value) -> time:
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    parsed = parse_time(str(value))
    if parsed is None:
        raise ValidationError("No fue posible interpretar la hora del registro.")
    return parsed


def coerce_datetime(value, fallback_date: Optional[date] = None) -> datetime:
    if isinstance(value, datetime):
        return value
    parsed = parse_datetime(str(value))
    if parsed:
        return parsed
    if fallback_date is not None:
        return datetime.combine(fallback_date, coerce_time(value))
    raise ValidationError("No fue posible interpretar la fecha y hora del registro.")
