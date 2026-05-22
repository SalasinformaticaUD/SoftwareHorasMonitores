FECHA: 21/05/2026
TURNO:  12m - 10 pm, 4pm - 10pm
MONITOR: Kevin Rincon - Sergio Nicolás Mendivelso

**NOTA: La presentación del 22 de mayo a las 10 am del aplicativo se va a hacer corriendo desde la terminal del VSCode usando el comando: "python manage.py runserver" Y luego accediendo a la URL: http://127.0.0.1:8000**

AVANCES:
- Se cambió la forma de ver registros y la liena de tiempo asosciada. Ahora en línea de tiempo multinivel se pueden observar los registros de un solo día.
- Se quitó la consulta como módulo, y se anexó el buscador de monitores desde el dashboard.
- Se pueden ver los registros de las horas extra que están por aprobar
- Se modificó parte de la interfaz gráfica del modulo de inconsistencias para generar mejor contraste con la página.
- Se subieron los registros actualizados de todos los monitores hasta el día de hoy. 

FUNCIONA:

- Todo el aplicativo, ya se puede aprobar por la autoridad De Diego. :D

NO FUNCIONA:

- No se puede completar la subida a docker porque los apagones cerraron la sesión.

NO MODIFICAR:

- No modificar el aplicativo a menos que Diego u otro de los técnicos lo solicite.

SIGUIENTE PASO:

- Esperar la aprobación de la autoridad de Diego :D.

Luego de la aprobación, se puede subir el aplicativo al docker, y luego al servidor. Para subir aplicativo al docker se debe hacer lo siguiente:

- Generar los archivos FINALES de excel de: Monitores, HorarioMonitores ---> Con todos los datos completos. Revisar los siguientes archivos como guía para realizar los archivos finales:

Monitores registrados (Nombre, códigos, correo, etc. Seguir el formato establecido) "C:\Users\ud\Downloads\MonitoresHastaElMomento.xlsx"

HorarioMonitores: "C:\Users\ud\Downloads\HorariosMonitores.xlsx"


- Logearse en docker y hacer el docker compose build, para subir el aplicativo a la nube
- La imagen de docker genera las tablas SQL, pero las deja vacias. Luego de montar el docker en la nube, se debe subir toda la información FINAL con el siguiente orden:

- Monitores
- HorarioMonitores
- Registro (Extraido directamente de CrossChex)
