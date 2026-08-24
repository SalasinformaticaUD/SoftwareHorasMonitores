# Informe 4 - Modulos paralelos_Backend

FECHA: 19/08/2026  
TURNO: 6:00 p. m. - 8:00 p. m.  
MONITOR: Kaleth Molina Diaz

## AVANCES:

* Se continuó con el desarrollo del módulo Gestión de Software Instalado en Aulas.

* Se realizó una revisión de la estructura del módulo `software` dentro del backend desarrollado con NestJS.

* Se implementó el DTO `CreateSoftwareDto` para la creación de registros de software.

* Se agregaron validaciones mediante `class-validator` utilizando `@IsString()`, `@IsNotEmpty()` y `@IsOptional()`.

* Se implementó `@Transform()` de `class-transformer` para realizar la limpieza de espacios en los campos de texto mediante `trim()`.

* Se implementó el DTO `CreateAulaSoftwareDto` para realizar la asociación entre un aula y un software mediante sus respectivos UUID.

* Se implementó el DTO `BuscarAulasPorSoftwareDto` para recibir uno o varios identificadores de software.

* Se agregaron validaciones de UUID mediante `@IsUUID()`.

* Se agregaron validaciones de arreglos mediante `@IsArray()`, `@ArrayMinSize(1)` y `@ArrayUnique()` para la búsqueda por múltiples softwares.

* Se configuró el `ValidationPipe` en el `SoftwareController` utilizando `transform`, `whitelist` y `forbidNonWhitelisted`.

* Se implementaron los endpoints correspondientes a la creación, consulta, actualización y eliminación de software.

* Se implementó el endpoint para asociar software a un aula.

* Se implementó el endpoint para eliminar una asociación entre software y aula.

* Se implementaron consultas para obtener los softwares asociados a un aula.

* Se implementaron consultas para obtener las aulas donde se encuentra instalado un software.

* Se implementó la búsqueda de aulas que cuentan con múltiples softwares específicos.

* Se desarrolló la lógica correspondiente en `SoftwareService` utilizando Prisma.

* Se implementó la validación de existencia del aula y del software antes de realizar una asociación.

* Se implementó el manejo de asociaciones duplicadas mediante la validación del código de error `P2002` de Prisma.

* Se implementó el manejo de errores mediante `NotFoundException` y `ConflictException`.

* Se implementó la normalización de los datos de software mediante `trim()` antes de almacenarlos o actualizarlos.

* Se revisaron las relaciones entre las entidades de software, aulas y la entidad intermedia utilizada para las asignaciones.

* Se verificó la compilación del módulo mediante `npm run build`.

* Se realizó una revisión específica del módulo mediante ESLint utilizando `npx eslint src/software --fix`.

## FUNCIONA:

* El módulo permite crear registros de software.
* El módulo permite consultar todos los softwares registrados.
* El módulo permite consultar un software específico mediante su UUID.
* El módulo permite actualizar información de software existente.
* El módulo permite eliminar software existente.
* El módulo permite asociar un software existente a un aula existente.
* Se valida que el aula y el software existan antes de crear una asociación.
* Se evita la creación de asociaciones duplicadas entre un aula y un software.
* El módulo permite eliminar asociaciones entre aulas y software.
* El módulo permite consultar los softwares instalados en un aula.
* El módulo permite consultar las aulas asociadas a un software.
* El módulo permite buscar aulas que tengan instalados varios softwares.
* Los datos recibidos mediante los DTOs cuentan con validaciones.
* La información recibida en las solicitudes es transformada y filtrada mediante `ValidationPipe`.
* La persistencia de la información se realiza mediante Prisma.

## NO FUNCIONA:

* No se han realizado todavía pruebas funcionales completas de todos los endpoints mediante una herramienta de pruebas como Postman o Swagger.
* No se han implementado todavía pruebas unitarias específicas para las reglas de negocio del módulo.
* No se han implementado todavía pruebas E2E para validar el flujo completo de gestión y asignación de software.

## NO MODIFICAR:

* No eliminar las validaciones implementadas en los DTOs.
* No eliminar los decoradores `@IsUUID()`, `@IsArray()`, `@ArrayMinSize()` o `@ArrayUnique()` para solucionar advertencias del editor.
* No reemplazar los tipos definidos por `any`.
* No modificar las relaciones de Prisma relacionadas con software y aulas sin verificar previamente su necesidad.
* No eliminar el manejo de `NotFoundException` y `ConflictException`.
* No modificar funcionalidades de otros módulos desde el módulo de software.
* No realizar refactorizaciones generales que no sean necesarias para la funcionalidad de Gestión de Software Instalado en Aulas.

## SIGUIENTE PASO:

* Realizar pruebas funcionales de los endpoints del módulo.
* Validar la creación de software con información válida e inválida.
* Validar la actualización y eliminación de software.
* Probar la asociación de software a un aula.
* Verificar el comportamiento al intentar registrar una asociación duplicada.
* Probar la eliminación de una asociación existente.
* Validar la consulta de softwares instalados en un aula.
* Validar la consulta de aulas asociadas a un software.
* Probar la búsqueda de aulas utilizando múltiples softwares.
* Implementar pruebas unitarias para las principales operaciones del `SoftwareService`.
* Implementar pruebas E2E para validar el flujo completo del módulo.