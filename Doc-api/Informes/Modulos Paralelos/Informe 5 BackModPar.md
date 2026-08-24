# Informe 5 - Backend

FECHA: 20/08/2026  
MONITORES: Ivan Felipe Prado Blanco 8:00 am - 10:00am // 2:00pm - 4:00pm; Kaleth Molina Diaz

## AVANCES:

* Se continuó con el desarrollo y la validación del módulo **Gestión de Software Instalado en Aulas**, tomando como punto de partida el estado y los siguientes pasos documentados en el Informe 4.
* Se revisó el estado actualizado del repositorio antes de realizar cambios, conservando las modificaciones existentes en otros módulos y en el frontend.
* Se revisó la implementación actual de `SoftwareService`, `SoftwareController`, los DTOs del módulo y las relaciones definidas en Prisma.
* Se confirmó que el módulo ya contaba con una base inicial de pruebas unitarias para creación, normalización, duplicidad, importación y búsqueda por múltiples softwares.
* Se amplió `software.service.spec.ts` de 5 a 20 pruebas unitarias.
* Se agregaron pruebas para la creación de software y la normalización de nombre, versión y descripción.
* Se verificó la conversión del error `P2002` de Prisma en `ConflictException` durante la creación y actualización de software.
* Se agregó una prueba para comprobar que los errores de persistencia diferentes de `P2002` sean propagados correctamente.
* Se agregaron pruebas para consultar el catálogo completo y comprobar su ordenamiento e inclusión de las aulas asociadas.
* Se agregaron pruebas para consultar un software específico y manejar mediante `NotFoundException` la consulta de un registro inexistente.
* Se agregaron pruebas para actualizar software, normalizar únicamente los campos enviados y evitar actualizaciones sobre registros inexistentes.
* Se agregaron pruebas para eliminar software existente.
* Se agregaron pruebas para asociar software y aulas existentes.
* Se verificó que no se cree una asociación cuando el aula no existe.
* Se mantuvo y verificó el manejo de asociaciones duplicadas mediante `ConflictException`.
* Se agregaron pruebas para eliminar asociaciones y manejar el intento de eliminar una asociación inexistente.
* Se agregaron pruebas para consultar los softwares instalados en un aula y las aulas asociadas a un software.
* Se fortaleció la prueba de búsqueda por múltiples softwares para verificar la estructura completa de la consulta Prisma con condición `AND`.
* Se agregó una prueba para garantizar asociaciones mediante `upsert` durante futuros procesos de importación.
* Se creó `test/software.e2e-spec.ts` con pruebas HTTP para los endpoints del módulo.
* Se probaron las operaciones de creación, consulta general, consulta individual, actualización y eliminación de software.
* Se probaron las rutas para crear, consultar y eliminar asociaciones entre software y aulas.
* Se probó la búsqueda de aulas que contienen todos los softwares solicitados.
* Se agregaron pruebas de validación para nombres vacíos, versiones ausentes, campos no permitidos, UUID inválidos, arreglos vacíos, UUID duplicados y valores que no corresponden a UUID.
* Se verificó la respuesta HTTP `409 Conflict` al intentar registrar una asociación duplicada.
* Las pruebas HTTP se implementaron con el servicio simulado para evitar que su ejecución dependa de una base de datos externa.
* Se ajustó `test/app.e2e-spec.ts` para reemplazar el proveedor de Prisma durante la prueba general de la aplicación.
* Se ajustó `test/jest-e2e.json` para que Jest resuelva correctamente los imports con extensión `.js` utilizados por NodeNext cuando la fuente generada por Prisma se encuentra en TypeScript.
* Se reprodujeron los diagnósticos del proyecto utilizando Jest, TypeScript y ESLint por separado.
* Se identificó que un error atribuido inicialmente a `software.service.spec.ts` provenía realmente de las firmas de dos tablas `it.each` en `software.e2e-spec.ts`.
* Se reemplazaron las filas posicionales de dichas tablas por objetos con las propiedades `body` y `descripcion`, conservando nombres legibles para las pruebas y eliminando los errores de TypeScript y ESLint.
* Se aplicó formato con Prettier a los archivos de pruebas modificados.
* Se verificó que los cambios no introdujeran errores de espacios o formato mediante `git diff --check`.
* No se modificó el código productivo del módulo ni las relaciones de Prisma, debido a que los problemas encontrados correspondían únicamente a la cobertura y configuración de pruebas.

## FUNCIONA:

* Las 20 pruebas unitarias de `SoftwareService` se ejecutan correctamente.
* La suite unitaria completa del backend supera 22 de 22 pruebas distribuidas en 3 suites.
* La suite E2E completa supera 16 de 16 pruebas distribuidas en 2 suites.
* Los endpoints de software cuentan con validación HTTP automatizada para datos válidos e inválidos.
* La creación de software valida, transforma y filtra los campos recibidos.
* La actualización y eliminación de software se encuentran cubiertas por pruebas.
* La consulta general e individual de software se encuentra cubierta por pruebas.
* La asociación y eliminación de software en aulas se encuentra cubierta por pruebas.
* El intento de crear una asociación duplicada produce una respuesta `409 Conflict` en las pruebas HTTP.
* Las consultas de software por aula y de aulas por software se encuentran cubiertas por pruebas.
* La búsqueda de aulas por múltiples softwares valida arreglos no vacíos, UUID únicos y UUID válidos.
* Jest puede resolver el cliente generado de Prisma utilizado por los imports configurados para NodeNext.
* La prueba E2E general puede inicializar `AppModule` sin requerir una conexión real a PostgreSQL.
* `npx tsc --noEmit --incremental false` finaliza sin errores.
* ESLint finaliza sin errores en los archivos revisados del módulo y sus pruebas.
* `npm run build` compila correctamente el backend.
* Prettier mantiene el formato esperado de los archivos modificados.

## NO FUNCIONA:

* Todavía no se han realizado pruebas funcionales manuales completas mediante Postman o Swagger.
* Las pruebas E2E del módulo utilizan un `SoftwareService` simulado y no validan la persistencia real en PostgreSQL.
* No existe todavía una base de datos exclusiva y aislada para pruebas automatizadas.
* No se ha probado automáticamente el ciclo completo contra Prisma real: crear software, crear aula, asociarlos, consultarlos y eliminar la asociación.
* No se ha configurado todavía la preparación y limpieza automática de datos antes y después de las pruebas de integración con base de datos.
* No se ha generado todavía un reporte formal de cobertura con umbrales mínimos exigidos para el módulo.

## NO MODIFICAR:

* No eliminar ni reducir las validaciones implementadas en los DTOs del módulo `software`.
* No eliminar los decoradores `@IsUUID()`, `@IsArray()`, `@ArrayMinSize()` o `@ArrayUnique()`.
* No reemplazar los tipos definidos por `any` para ocultar diagnósticos de TypeScript.
* No eliminar las pruebas de casos inválidos para conseguir que la suite pase.
* No eliminar el manejo de `NotFoundException` y `ConflictException`.
* No modificar las relaciones de Prisma entre `Software`, `Aula` y `AulaSoftware` sin verificar previamente su necesidad.
* No convertir las pruebas E2E actuales en pruebas dependientes de la base de datos de desarrollo.
* No utilizar información real de producción o desarrollo al implementar pruebas de integración.
* No modificar funcionalidades de otros módulos desde las pruebas del módulo `software`.
* No realizar refactorizaciones generales que no sean necesarias para la funcionalidad o validación del módulo.
* No atribuir un diagnóstico a un archivo sin reproducir primero el error mediante Jest, TypeScript o ESLint.

## SIGUIENTE PASO:

* Configurar una base de datos PostgreSQL exclusiva para pruebas.
* Crear variables de entorno separadas para el entorno de pruebas y evitar el uso accidental de la base de datos de desarrollo.
* Implementar preparación y limpieza automática de datos para pruebas de integración.
* Crear una prueba E2E con Prisma real que valide el flujo completo del módulo.
* Validar la creación de software y aula, su asociación, las consultas relacionadas y la eliminación de la asociación dentro del mismo flujo aislado.
* Probar las restricciones únicas reales de la base de datos para software y asociaciones.
* Ejecutar pruebas funcionales manuales mediante Postman o Swagger una vez configurado el entorno de pruebas.
* Generar un reporte de cobertura del módulo con `npm run test:cov`.
* Definir umbrales mínimos de cobertura para líneas, funciones y ramas del módulo `software`.
* Mantener la ejecución de `npm run build`, pruebas unitarias, pruebas E2E, TypeScript y ESLint como verificación previa a cada entrega.

## VERIFICACIÓN LOCAL:

Ejecutar desde la carpeta `backend`:

```powershell
cd "C:\Users\MONITORES\Documents\Software Monitorias\backend"
npm run build
npx tsc --noEmit --incremental false
npx eslint src/software test/software.e2e-spec.ts
npm test -- --runInBand
npm run test:e2e -- --runInBand
```

Estado: Cobertura unitaria y HTTP completada para el módulo de software. Pendiente la integración automatizada con una base de datos PostgreSQL exclusiva para pruebas.
