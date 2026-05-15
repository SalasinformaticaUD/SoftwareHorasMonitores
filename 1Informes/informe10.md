FECHA: 14/05/2026
TURNO: 12 pm - 8 pm
MONITOR: Kevin David Rincon Valencia

AVANCES:

* Ya se realiza la lectura de registros crudos desde CrossChex.
* Se implementó el emparejamiento inteligente de marcaciones para cálculo automático de horas.
* Se agregó la ventana de tolerancia de 5 minutos para detección de marcaciones repetidas.
* Se implementó la detección de inconsistencias:

  * Marcaciones impares.
  * Errores de finalización de jornada.
  * Emparejamientos menores a 30 minutos.
  * Marcaciones duplicadas.
* Se reorganizó y corrigió el módulo de inconsistencias para visualizar correctamente los diferentes tipos de error.
* Se cargaron registros de prueba:

  * Monitores de aulas: del 1 de febrero al 1 de marzo.
  * Monitores de laboratorios: del 1 de abril al 1 de mayo.
* Se estableció que para deshabilitar una inconsistencia es obligatorio realizar una anotación asociada.

FUNCIONA:

* Lectura de registros desde CrossChex.
* Emparejamiento automático de entradas y salidas.
* Cálculo de horas.
* Detección automática de inconsistencias.
* Visualización de inconsistencias en el módulo correspondiente.

NO FUNCIONA:

* Creacion de contraseña, solo deja poner algunas contraseñas

* Las marcaciones duplicadas ya se invalidan automáticamente, pero aún aparecen visualmente en el módulo de inconsistencias.

NO MODIFICAR:

* Lógica actual de emparejamiento inteligente y validación de inconsistencias.

SIGUIENTE PASO:
* Revisar informe9
* Terminar la funcion de creacion de acta (Electrica), colocando el contenido correcto 
* Recoleccion de correos de monitores y actualizacion de los mismos (Electrica y fisica)
* Realizar pruebas del requisito actas de compromiso para verificacion de funcionalidad completa
* Evitar que las marcaciones duplicadas invalidadas aparezcan en el módulo de inconsistencias.
* Realizar pruebas funcionales con los registros ya cargados por parte del líder.
* Iniciar generación automática de memorandos por llegadas tarde.
* Finalizar el módulo 3.
* Realizar pruebas completas del módulo 2, el cual ya se encuentra terminado.
