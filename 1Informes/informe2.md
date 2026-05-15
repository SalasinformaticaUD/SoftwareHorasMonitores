monitoresASUD@gmail.com
monitores123


FECHA: 11/05/2026
TURNO: 8am-12pm
MONITOR: Jhojan Stiven Aragón Ramirez
AVANCES:

* Se dejó funcionando el envío de correos a monitores.
* Cuenta configurada actualmente:
     Correo: monitoresASUD@gmail.com
    Contraseña: monitores123
* De momento, cualquier correo registrado puede iniciar sesión. Aún no se ha implementado la recuperación de contraseña.
* El inicio de sesión de monitores ahora únicamente muestra las horas correspondientes a cada monitor.
* La consulta pública dejó de ser pública; ahora solo pueden acceder los líderes.

FUNCIONA:

* Carga de monitores.
* Carga de horarios.

NO FUNCIONA:

* Visualización general de horarios. Actualmente se pueden consultar horarios monitor por monitor, pero aún falta implementar una vista global con todos los horarios.
* Posibles errores en algunas rutas que retornan “Forbidden” y todavía no se manejan correctamente.
* Visualizacion de horarios unicamente funciona en Chrome

NO MODIFICAR:

* Atributo ubicación del horario, ya que los monitores de laboratorio también tienen un salón asignado.

SIGUIENTE PASO:

* Arreglar el calendario semanal en la sección de Horarios, ya que la visualización presenta algunos problemas.
* Permitir editar cada monitor (solo falta agregar el botón correspondiente).
* Realizar pruebas generales del sistema. Si todo funciona correctamente, quedarían listos los módulos 1 y 2 y se podría iniciar el desarrollo del módulo 3.


# Cambiar DNS manualmente (Google DNS)
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" `
-ServerAddresses 8.8.8.8,8.8.4.4

# Restaurar DNS automático (DHCP/red institucional)
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" `
-ResetServerAddresses

# Limpiar caché DNS
ipconfig /flushdns

# Ver configuración actual
ipconfig /all

# Probar resolución DNS
nslookup smtp.gmail.com

# Probar conectividad SMTP
Test-NetConnection smtp.gmail.com -Port 587