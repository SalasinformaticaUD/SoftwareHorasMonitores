# Informe 6 - Modulos paralelos_Backend

FECHA: 20/08/2026  
TURNO: 8:00 p. m. - 10:00 p. m.  
MONITOR: Kaleth Molina Diaz

## AVANCES:

* Se realizó la integración de la rama `software_instalado` hacia la rama `main`.

* Se verificó inicialmente el estado del repositorio antes de concluir el merge.

* Se confirmó que la rama `software_instalado` contenía el trabajo más reciente del módulo **Gestión de Software Instalado en Aulas**.

* Se ejecutó el proceso de merge desde `main` para incorporar los cambios realizados en `software_instalado`.

* Durante el merge se identificaron conflictos en servicios de módulos ya existentes.

* Se resolvieron los conflictos de los servicios ajenos al módulo `software` conservando la versión de `main`, debido a que allí existían implementaciones más completas que las versiones heredadas de scaffold.

* Se resolvió el conflicto principal en `backend/src/software/software.service.ts`, integrando la lógica preparada para el módulo **Software Instalado**.

* Se conservó la arquitectura actual del backend utilizando el `PrismaService` global del proyecto.

* Se evitó introducir un segundo cliente Prisma exclusivo para el módulo `software`, manteniendo consistencia con el resto del backend.

* Se incorporó la preparación necesaria para futuras importaciones de software instalado desde archivo, sin depender todavía de un formato definitivo de archivo.

* Se mantuvo la lógica de catálogo de software.

* Se mantuvo la relación entre software y aulas mediante `AulaSoftware`.

* Se mantuvo la validación de unicidad para evitar duplicados en software por nombre y versión.

* Se mantuvo la validación de unicidad para evitar asociaciones duplicadas entre aula y software.

* Se incorporó el DTO `ImportarSoftwareDto` para representar la estructura lógica que posteriormente podrá reutilizarse al implementar la importación desde archivo.

* Se incorporó la entidad `ImportacionSoftware` para conservar el historial de procesos de importación.

* Se incorporó en Prisma el soporte para registrar resultados de importación mediante el enum `ResultadoImportacionSoftware`.

* Se mantuvieron los métodos reutilizables para futuras importaciones, como `upsertCatalogEntry`, `ensureAulaAssociation` e `importInventory`.

* Se mantuvo el método para consultar el historial de importaciones de software.

* Se conservaron las pruebas unitarias del módulo `software` relacionadas con creación, normalización, duplicidad, asociaciones, búsqueda por múltiples softwares e importación.

* Se corrigió una advertencia de ESLint en `backend/src/practicas-libres/practicas-libres.service.ts`, eliminando una directiva `eslint-disable` que ya no era necesaria.

* Se corrigieron errores de ESLint en `backend/test/aulas.e2e-spec.ts`, tipando explícitamente las respuestas del cuerpo HTTP y ajustando mocks que no necesitaban funciones `async`.

* Se aplicó formato con Prettier únicamente a los archivos necesarios para dejar el lint sin errores.

* Se ejecutó la validación del schema de Prisma.

* Se generó nuevamente el cliente Prisma para que TypeScript reconociera las estructuras añadidas al schema.

* Se ejecutó la compilación del backend.

* Se ejecutó la verificación TypeScript sin emisión de archivos.

* Se ejecutaron las pruebas automatizadas del backend.

* Se ejecutó ESLint en modo diagnóstico sin aplicar correcciones automáticas globales.

* Se creó el commit de merge en `main` con el identificador `6f08319`.

## FUNCIONA:

* La rama `main` contiene ahora los cambios realizados en `software_instalado`.

* El árbol de trabajo quedó limpio después del merge.

* El módulo `software` conserva la gestión del catálogo de software.

* El módulo `software` conserva la asociación entre software y aulas mediante `AulaSoftware`.

* El módulo `software` conserva las validaciones de duplicidad para software y asociaciones.

* El módulo `software` quedó preparado para reutilizar lógica en una futura importación desde archivo.

* El historial de importaciones queda representado mediante `ImportacionSoftware`.

* El schema de Prisma es válido.

* El cliente Prisma se generó correctamente.

* `npm run build` compila correctamente el backend.

* `npx tsc --noEmit --incremental false` finaliza sin errores.

* La suite de pruebas del backend finaliza correctamente con 8 suites aprobadas y 48 pruebas aprobadas.

* ESLint finaliza sin errores.

* Los conflictos de merge fueron resueltos y el merge quedó concluido mediante commit.

## NO FUNCIONA:

* No se realizó `git push` hacia el repositorio remoto.

* La rama `main` local quedó por delante de `origin/main` por 2 commits.

* No se implementó todavía la lectura real de archivos para importación de software, porque el formato definitivo del archivo aún no está definido.

* No se ejecutaron migraciones de base de datos.

* No se realizaron pruebas manuales funcionales mediante Postman o Swagger.

* No se validó el flujo de importación contra una base de datos PostgreSQL real.

## NO MODIFICAR:

* No eliminar el uso del `PrismaService` global en `SoftwareService` sin revisar la arquitectura general del backend.

* No crear un segundo cliente Prisma exclusivo para `software` si no existe una razón técnica validada.

* No eliminar las validaciones de unicidad del catálogo de software.

* No eliminar las validaciones de unicidad de la asociación entre software y aula.

* No eliminar los DTOs del módulo `software` relacionados con creación, actualización, asociación, búsqueda e importación preparada.

* No eliminar la entidad `ImportacionSoftware`, ya que permite conservar historial de futuras importaciones.

* No modificar el schema de Prisma sin generar y revisar la migración correspondiente.

* No ejecutar comandos destructivos sobre la base de datos.

* No modificar módulos ajenos a `software` salvo para correcciones puntuales verificadas de compilación, pruebas o lint.

* IMPORTANTE: NO HACER PUSH bajo ninguna circunstancia en esta etapa.

## SIGUIENTE PASO:

* Mantener los cambios únicamente de forma local hasta que el equipo autorice explícitamente la publicación.

* Revisar si debe generarse una migración formal para los cambios de Prisma relacionados con `ImportacionSoftware`.

* Definir el formato final del archivo de importación de software instalado.

* Implementar posteriormente la lectura real del archivo de importación.

* Reutilizar la lógica ya preparada en `SoftwareService` para normalizar filas, crear o actualizar software y asociarlo con aulas.

* Probar el flujo completo de importación con datos reales o de prueba controlados.

* Validar el historial de importaciones desde el endpoint correspondiente.

* Ejecutar pruebas funcionales manuales mediante Postman o Swagger.

* Mantener como verificación mínima previa a futuras entregas: Prisma validate, Prisma generate, build, TypeScript, pruebas y ESLint.

## VERIFICACIÓN LOCAL:

Ejecutado desde la carpeta `backend`:

```powershell
cd "C:\Users\MONITORES\Documents\Software Monitorias\backend"
npx prisma validate
npx prisma generate
npm run build
npx tsc --noEmit --incremental false
npm test -- --runInBand
npx eslint "{src,apps,libs,test}/**/*.ts" --no-fix
```

Resultados:

```text
npx prisma validate
Estado: OK
Mensaje: The schema at prisma\schema.prisma is valid

npx prisma generate
Estado: OK
Mensaje: Generated Prisma Client (7.9.1) to .\generated\prisma

npm run build
Estado: OK
Mensaje: nest build finalizó sin errores

npx tsc --noEmit --incremental false
Estado: OK
Mensaje: finalizó sin errores

npm test -- --runInBand
Estado: OK
Resultado: 8 suites aprobadas, 48 pruebas aprobadas

npx eslint "{src,apps,libs,test}/**/*.ts" --no-fix
Estado: OK
Mensaje: finalizó sin errores
```

## ESTADO FINAL:

La rama `main` quedó con el merge de `software_instalado` aplicado localmente mediante el commit:

```text
6f08319 Merge branch 'software_instalado' into main
```

Estado: Merge completado localmente. IMPORTANTE: NO HACER PUSH. Los cambios deben permanecer locales hasta nueva autorización.
