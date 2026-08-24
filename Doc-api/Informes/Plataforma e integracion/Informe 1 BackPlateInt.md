# Informe 2 - Backend

FECHA: 18/08/2026  
AUTORES: Tecnico Juan Bustos y Asistencial Kevin Rincon de Aulas de Software

## AVANCES

* Se corrigieron las cosas que estaban mal en el informe 1.
* Se revisó el documento de análisis y especificación de requisitos para identificar los módulos funcionales requeridos por el sistema.
* Se verificó la configuración actual de NestJS y el esquema de datos definido con Prisma.
* Se creo la bd dentro de pgadmin y se conecto.
* Se generaron recursos NestJS con comunicación REST API para los dominios funcionales y transversales del backend.
* Se conservaron los módulos existentes de `auth` y `horario`.
* Se crearon los módulos de disponibilidad de aulas, asistencia docente, prácticas libres, préstamos docentes, préstamos audiovisuales, software, aulas, multas, observaciones, limpieza, tareas operativas, credenciales, reportes y panel operativo.
* Se crearon los módulos transversales de usuarios, roles, permisos, dependencias y auditoría.
* Cada recurso generado contiene su módulo, controlador, servicio, DTO de creación, DTO de actualización y entidad inicial.
* Todos los módulos fueron registrados en `src/app.module.ts`.
* Se ajustaron los identificadores recibidos por las rutas REST para manejarlos como `string`, de acuerdo con los UUID definidos en Prisma.
* Se creó `src/MODULES.md` con la relación entre cada módulo, su ruta REST y el rango de requerimientos funcionales correspondiente.
* Se eliminaron `src/app.controller.ts` y `src/app.service.ts`, debido a que el módulo raíz solamente debe integrar los módulos funcionales.
* Se actualizó la prueba e2e para verificar que la aplicación no exponga una ruta raíz genérica.

## ESTRUCTURA FUNCIONAL

Los recursos principales quedaron organizados de la siguiente manera:

* `horario`: RF-001 a RF-010.
* `disponibilidad-aulas`: RF-011 a RF-020.
* `asistencia-docente`: RF-021 a RF-030.
* `practicas-libres`: RF-031 a RF-048.
* `prestamos-docentes`: RF-049 a RF-058.
* `prestamos-audiovisuales`: RF-059 a RF-071.
* `software`: RF-072 a RF-081.
* `aulas`: RF-082 a RF-091.
* `multas`: RF-092 a RF-102.
* `observaciones`: RF-103 a RF-110.
* `limpieza-aulas`: RF-111 a RF-120.
* `tareas-operativas`: RF-121 a RF-132.
* `credenciales`: RF-133 a RF-142.
* `reportes`: RF-143 a RF-155.
* `panel-operativo`: RF-156 a RF-165.

## FUNCIONA

* La aplicación reconoce e importa todos los módulos desde `AppModule`.
* La estructura base de controladores y servicios REST compila correctamente.
* El backend supera las pruebas automatizadas existentes: 2 suites y 2 pruebas aprobadas.
* Los controladores utilizan identificadores compatibles con los UUID del modelo de datos.
* El módulo raíz ya no depende de un controlador o servicio de ejemplo.

## PENDIENTE

* Esperar plan de implementación.
* Seguir con la metodologia Scrum.
* Continuar con plan de desarrollo explicado en el documento.


## SIGUIENTE PASO

* Crear un `PrismaModule` y un `PrismaService` compartidos.
* Implementar primero los módulos transversales de usuarios, autenticación, roles y permisos.
* Completar los DTO y operaciones CRUD de aulas, horarios y catálogos académicos.
* Implementar posteriormente disponibilidad, préstamos y asistencia docente, ya que dependen de la información anterior.
* Añadir pruebas unitarias y e2e para cada módulo a medida que se implemente su lógica de negocio.

## VERIFICACIÓN LOCAL

Ejecutar desde la carpeta `backend`:

```powershell
cd "C:\Users\MONITORES\Documents\Software Monitorias\backend"
npm run build
npm test -- --runInBand
```
