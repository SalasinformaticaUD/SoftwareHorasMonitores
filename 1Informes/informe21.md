FECHA: 20/05/2026
TURNO: 4 pm - 8 pm, 6pm - 10pm
MONITOR: Daniel Pérez Madera - Sergio Nicolás Mendivelso

AVANCES:
- Los Modales contenian errores, en los que mandaban mensajes de error cuando se hacía algo correcto o viceversa
- El módulo de excepciones generaba error al no poner datos. Ahora no se puede enviar el formulario hasta llenar los datos correspondientes.
- el archivo base.html tenía algunos errores a al hora de generar los modales. Se corrigió exitosamente.
- Se avanzó en la investigación de la implementación del módulo 5. Se utilizará Azure Active Directory, utilizando el servicio MIcrosoft Entra ID. Este servicio genera la autenticación por medio del mismo Microsoft y una lista de correos válidos
- Los correos institucionales se pueden vincular, pero es necesario obtener el Tenant ID de los correos de la Universidad correspondientes. Esto se debe hacer desde administración
- Como el Azure no funciona sin una suscripción, se debe solicitar a la Administración una cuenta con los permisos necesarios para utilizar el servicio de Microsoft Entra ID.
- Se redactó la solicitud para pedir tanto la suscripción como los Tenant ID de los correos anexados.

FUNCIONA:

- Modales, advertencias, errores y formularios incompletos.

NO FUNCIONA:

- No se tiene acceso a una cuenta de Azure para poder empezar a realizar la autenticación con Microsoft

NO MODIFICAR:

- Lógica actual de emparejamiento, cálculo de horas e inconsistencias.
- Logica y diseño linea del tiempo
- Logica de las inconsistencias y anotaciones

SIGUIENTE PASO:
- Enviar la solicitud para una cuenta de Azure con acceso al servicio Microsoft Entra ID y solicitar los códigos Tenant que corresponden al código de identificación de cada correo creado para un usuario. Se anexa archivo de google docs de la solicitud: https://docs.google.com/document/d/1yMKl64xA6G1quh9ONaqBP6VPoarirwyWeylWOLqkbqI/edit?usp=sharing


- Una vez teniendo el correo con accesos y los Tenant ID, se puede empezar a hacer la implementación de la verificación por Microsoft Azure. Se anexa video del paso a paso de la implementación: https://www.youtube.com/watch?v=t02stKhdxi4