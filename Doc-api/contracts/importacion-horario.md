# Contrato de importacion de horarios JSON_V1 y JSON_V2

Fecha de definicion: 21/08/2026

`POST /horario/importar` recibe una carga JSON transaccional. Un futuro lector de Excel
debera convertir sus filas a uno de estos contratos antes de invocar el servicio de
importacion.

## Solicitud

```json
{
  "formato": "JSON_V1",
  "periodoId": "00000000-0000-4000-8000-000000000001",
  "nombreArchivo": "horario-2026-3.json",
  "clases": [
    {
      "aulaId": "00000000-0000-4000-8000-000000000002",
      "docenteId": "00000000-0000-4000-8000-000000000003",
      "asignaturaId": "00000000-0000-4000-8000-000000000004",
      "proyectoCurricularId": "00000000-0000-4000-8000-000000000005",
      "diaSemana": 1,
      "horaInicio": "08:00",
      "horaFin": "10:00",
      "grupo": "020-81",
      "inscritos": 25
    }
  ]
}
```

`nombreArchivo`, `proyectoCurricularId` e `inscritos` son opcionales. El lote debe
contener entre 1 y 500 clases. Los catalogos referenciados deben existir previamente;
la creacion automatica de docentes o asignaturas no forma parte de `JSON_V1`.

## Catalogos incompletos con JSON_V2

`JSON_V2` conserva la misma estructura, pero cada fila puede reemplazar `docenteId` y
`asignaturaId` por los objetos siguientes:

```json
{
  "formato": "JSON_V2",
  "periodoId": "00000000-0000-4000-8000-000000000001",
  "clases": [
    {
      "aulaId": "00000000-0000-4000-8000-000000000002",
      "docente": {
        "documento": "123456",
        "nombre": "Docente Nuevo",
        "correo": "docente@udistrital.edu.co"
      },
      "asignatura": {
        "codigo": "SIS-101",
        "nombre": "Programacion I"
      },
      "diaSemana": 1,
      "horaInicio": "08:00",
      "horaFin": "10:00",
      "grupo": "020-81"
    }
  ]
}
```

En cada fila `JSON_V2` debe enviarse exactamente una alternativa para cada catalogo:
`docenteId` o `docente`, y `asignaturaId` o `asignatura`. El docente se actualiza o crea
por `documento`; la asignatura se actualiza o crea por `codigo`. El correo del docente es
opcional y se normaliza a minusculas.

## Reglas atomicas

- Todas las clases pertenecen al `periodoId` de la raiz.
- Cada fila usa las mismas validaciones del registro manual.
- Se validan UUID, dia de semana, horas, grupo, inscritos y referencias.
- Se rechazan cruces con clases existentes y entre filas del mismo lote.
- En `JSON_V2`, los upserts de catalogos forman parte de la misma transaccion.
- Toda la operacion se ejecuta en una transaccion: una fila invalida revierte el lote.
- Los errores de negocio indican la fila, usando numeracion desde 1.

## Respuesta exitosa

La respuesta incluye `formato`, `periodoId`, `nombreArchivo`, `totalRecibidas`,
`totalCreadas` y las clases creadas con sus relaciones principales.
