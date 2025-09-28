# Manual de Instalación en Producción - Email Intelligence Analyzer (EIA)

Esta guía detalla los pasos para desplegar la aplicación EIA en un entorno de producción, desde la configuración inicial del servidor hasta que sea accesible a través de un dominio web con HTTPS.

**Arquitectura de destino:** Servidor Ubuntu (22.04 o superior) en arquitectura ARM.

## 1. Prerrequisitos

Antes de comenzar, asegúrese de tener lo siguiente:

- **Un servidor con Ubuntu 22.04 (ARM)**: Se necesita acceso `root` o un usuario con privilegios `sudo`.
- **Un nombre de dominio registrado**: Deberá poder configurar los registros DNS de este dominio.
- **Software requerido**: Git, Docker, Docker Compose y Apache2.

### Instalación del Software Necesario

Conéctese a su servidor y ejecute los siguientes comandos para instalar todo el software requerido.

1.  **Actualizar el sistema:**
    ```bash
    sudo apt-get update && sudo apt-get upgrade -y
    ```

2.  **Instalar Git y Apache2:**
    ```bash
    sudo apt-get install -y git apache2
    ```

3.  **Instalar Docker y Docker Compose:**
    El script oficial de Docker es la forma más sencilla de instalar ambas herramientas en una máquina ARM.
    ```bash
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    ```
    Después de la instalación, agregue su usuario al grupo de Docker para poder ejecutar comandos sin `sudo` (requiere cerrar sesión y volver a iniciarla para que el cambio surta efecto).
    ```bash
    sudo usermod -aG docker ${USER}
    ```

## 2. Configuración Inicial del Servidor y Dominio

### Paso 2.1: Apuntar el Dominio al Servidor

1.  **Obtenga la dirección IP de su servidor:**
    ```bash
    hostname -I | awk '{print $1}'
    ```
2.  **Cree un registro DNS 'A':**
    - Acceda al panel de control de su proveedor de dominio.
    - Vaya a la sección de gestión de DNS.
    - Cree un nuevo **registro de tipo 'A'**.
      - **Host/Nombre**: `@` (para el dominio raíz, ej: `sudominio.com`) o `www` (para `www.sudominio.com`).
      - **Valor/Apunta a**: La dirección IP de su servidor obtenida anteriormente.
    - Guarde los cambios. La propagación del DNS puede tardar desde unos minutos hasta varias horas.

### Paso 2.2: Configurar el Firewall (UFW)

Para mejorar la seguridad, configuraremos el firewall para permitir solo el tráfico necesario (SSH, HTTP y HTTPS).

1.  **Permitir el tráfico esencial:**
    ```bash
    sudo ufw allow OpenSSH
    sudo ufw allow 'Apache Full'
    ```
    `'Apache Full'` abre tanto el puerto 80 (HTTP) como el 443 (HTTPS).

2.  **Habilitar el firewall:**
    ```bash
    sudo ufw enable
    ```
    Cuando se le solicite, escriba `y` y presione Enter para confirmar.

3.  **Verificar el estado:**
    ```bash
    sudo ufw status
    ```
    Debería ver que el firewall está activo y que las reglas para OpenSSH y Apache Full están permitidas.

## 3. Despliegue de la Aplicación

Con el servidor preparado, el siguiente paso es desplegar la aplicación EIA.

### Paso 3.1: Clonar el Repositorio

Clone el código fuente del proyecto desde su repositorio de Git. Reemplace `<URL_DEL_REPOSITORIO>` con la URL correcta.

```bash
git clone <URL_DEL_REPOSITORIO> eia
cd eia
```

### Paso 3.2: Configurar la Aplicación

La aplicación utiliza un archivo `config.yml` para gestionar sus ajustes.

1.  **Copie el archivo de ejemplo:**
    ```bash
    cp config.yml.example config.yml
    ```

2.  **Edite el archivo de configuración:**
    Abra el archivo `config.yml` con un editor de texto como `nano`.
    ```bash
    nano config.yml
    ```
    **¡MUY IMPORTANTE!** Para que los contenedores de Docker se comuniquen entre sí, debe usar los nombres de los servicios de Docker como nombres de host en las URLs de conexión. Asegúrese de que las siguientes líneas estén configuradas exactamente así:
    ```yaml
    database:
      # Usa 'db' como hostname, que es el nombre del servicio en docker-compose.yml
      url: "postgresql://user:password@db/eia_db"

    redis:
      # Usa 'redis' como hostname
      url: "redis://redis:6379/0"
    ```
    Además, configure el resto de los parámetros según sus necesidades (cuentas de correo, etc.). Guarde el archivo y salga del editor.

### Paso 3.3: Construir e Iniciar los Contenedores

1.  **Construir las imágenes de Docker:**
    Este comando construye la imagen para la aplicación EIA según se define en el `Dockerfile`. Puede tardar varios minutos la primera vez.
    ```bash
    docker-compose build
    ```

2.  **Inicializar la Base de Datos:**
    Antes de iniciar la aplicación por primera vez, es necesario crear el esquema de la base de datos.
    ```bash
    docker-compose run --rm backend python eia_cli.py init-db
    ```

3.  **Iniciar todos los servicios:**
    Este comando iniciará todos los servicios (backend, worker, beat, db, redis) en segundo plano.
    ```bash
    docker-compose up -d
    ```

4.  **Verificar que los servicios estén en ejecución:**
    ```bash
    docker-compose ps
    ```
    Todos los contenedores deberían mostrar el estado `Up` o `running`. Si alguno no lo está, puede inspeccionar sus logs con el comando `docker-compose logs -f <nombre_del_servicio>`.

## 4. Configuración del Servidor Web y HTTPS

En este punto, la aplicación EIA se está ejecutando dentro de contenedores de Docker, pero no es accesible desde el exterior. Configuraremos Apache como un **proxy inverso** para dirigir el tráfico de su dominio a la aplicación y, a continuación, aseguraremos la conexión con HTTPS.

### Paso 4.1: Configurar Apache como Proxy Inverso

1.  **Habilitar los módulos de Apache necesarios:**
    ```bash
    sudo a2enmod proxy
    sudo a2enmod proxy_http
    sudo systemctl restart apache2
    ```

2.  **Crear un archivo de configuración del sitio:**
    Cree un nuevo archivo de configuración para su dominio. Reemplace `sudominio.com` con su nombre de dominio real.
    ```bash
    sudo nano /etc/apache2/sites-available/sudominio.com.conf
    ```

3.  **Añadir la configuración del Virtual Host:**
    Copie y pegue la siguiente configuración en el archivo. No olvide reemplazar `sudominio.com` y `webmaster@sudominio.com` con sus datos.

    ```apache
    <VirtualHost *:80>
        ServerName sudominio.com
        ServerAlias www.sudominio.com
        ServerAdmin webmaster@sudominio.com

        # Redirección a HTTPS (será gestionada por Certbot más adelante)

        # Configuración del Proxy Inverso
        ProxyPreserveHost On
        ProxyPass / http://127.0.0.1:8000/
        ProxyPassReverse / http://127.0.0.1:8000/

        ErrorLog ${APACHE_LOG_DIR}/sudominio-error.log
        CustomLog ${APACHE_LOG_DIR}/sudominio-access.log combined
    </VirtualHost>
    ```
    Guarde el archivo y salga del editor.

4.  **Habilitar el nuevo sitio:**
    ```bash
    sudo a2ensite sudominio.com.conf
    sudo systemctl restart apache2
    ```
    En este momento, si su DNS ya se ha propagado, debería poder acceder a `http://sudominio.com` y ver la interfaz de la aplicación.

### Paso 4.2: Asegurar el Dominio con HTTPS usando Certbot

1.  **Instalar Certbot:**
    Certbot es una herramienta que automatiza la obtención e instalación de certificados SSL/TLS de Let's Encrypt.
    ```bash
    sudo apt-get install -y certbot python3-certbot-apache
    ```

2.  **Obtener e Instalar el Certificado SSL:**
    Ejecute Certbot, que leerá su configuración de Apache y le guiará en el proceso. Reemplace `sudominio.com` con su dominio.
    ```bash
    sudo certbot --apache -d sudominio.com -d www.sudominio.com
    ```
    - Le pedirá una dirección de correo electrónico para notificaciones urgentes.
    - Le pedirá que acepte los Términos de Servicio.
    - Le preguntará si desea redirigir todo el tráfico HTTP a HTTPS. **Se recomienda encarecidamente seleccionar la opción de redirección (normalmente la opción 2)**.

3.  **Verificar la renovación automática:**
    Certbot configura una tarea programada (`cron job`) para renovar automáticamente los certificados antes de que expiren. Puede verificar que funciona con este comando:
    ```bash
    sudo certbot renew --dry-run
    ```
    Si el "dry run" (simulacro) tiene éxito, no necesita hacer nada más.

## 5. Verificación y Mantenimiento

### Paso 5.1: Verificación Final

Abra su navegador web y navegue a `https://sudominio.com`. Debería ser redirigido automáticamente a la versión segura (HTTPS) del sitio y ver la interfaz de la aplicación EIA.

¡Felicidades! Su aplicación está desplegada y lista para ser utilizada en un entorno de producción.

### Paso 5.2: Comandos de Mantenimiento

A continuación se presenta una lista de comandos útiles para gestionar su aplicación.

-   **Para detener todos los servicios:**
    ```bash
    cd ~/eia # Asegúrese de estar en el directorio del proyecto
    docker-compose down
    ```

-   **Para iniciar todos los servicios:**
    ```bash
    cd ~/eia
    docker-compose up -d
    ```

-   **Para ver los logs de un servicio específico (ej: backend):**
    ```bash
    cd ~/eia
    docker-compose logs -f backend
    ```

-   **Para actualizar la aplicación con los últimos cambios de código:**
    ```bash
    cd ~/eia
    git pull # Descargar los últimos cambios
    docker-compose build # Reconstruir la imagen con los cambios
    docker-compose up -d # Reiniciar los contenedores
    ```

-   **Para ejecutar un comando de la CLI de la aplicación (ej: `some-command`):**
    ```bash
    cd ~/eia
    docker-compose run --rm backend python eia_cli.py some-command
    ```