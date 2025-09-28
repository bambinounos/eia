# Deployment Guide for Email Intelligence Analyzer (EIA)

This guide provides instructions for deploying the EIA application using Docker and setting up Apache2 as a reverse proxy on a production server (e.g., Ubuntu ARM).

## Prerequisites

1.  **Docker and Docker Compose**: Ensure `docker` and `docker-compose` are installed on your server.
2.  **Apache2**: The Apache web server should be installed (`sudo apt-get install apache2`).
3.  **Configuration Files**:
    *   Copy `config.yml.example` to `config.yml` and fill in your production details (database credentials, email accounts, etc.).
    *   Ensure your `catalog.yml` is configured as needed.

    **Important**: The `docker-compose.yml` file assumes the database credentials are `user:password` and the database name is `eia_db`. You MUST update the `database.url` in your `config.yml` to match these credentials for the containers to connect:
    ```yaml
    database:
      url: "postgresql://user:password@db/eia_db" # Use 'db' as the hostname
    ```
    Similarly, update the Redis URL:
    ```yaml
    redis:
      url: "redis://redis:6379/0" # Use 'redis' as the hostname
    ```

## Step 1: Build and Run with Docker Compose

The `docker-compose.yml` file orchestrates all the necessary services: the backend API, Celery worker, Celery Beat scheduler, PostgreSQL database, and Redis.

1.  **Build the Docker images**:
    From the project root directory, run the build command. This will build the image defined in the `Dockerfile`.
    ```bash
    docker-compose build
    ```

2.  **Initialize the Database**:
    Before starting the services for the first time, you need to run the database initialization script. `docker-compose run` starts a one-off container for a service.
    ```bash
    docker-compose run --rm backend python eia_cli.py init-db
    ```
    This command starts a temporary `backend` container, runs the `init-db` command from our CLI, and then removes the container.

3.  **Start all services**:
    Start the entire application stack in detached mode (`-d`).
    ```bash
    docker-compose up -d
    ```

4.  **Verify the services are running**:
    You can check the status of the running containers:
    ```bash
    docker-compose ps
    ```
    You should see `eia_backend`, `eia_worker`, `eia_beat`, `eia_db`, and `eia_redis` with a status of `Up`. You can also check the logs for a specific service:
    ```bash
    docker-compose logs -f backend
    ```

## Step 2: Configure Apache2 as a Reverse Proxy

A reverse proxy is essential for a production setup. It handles incoming HTTP(S) requests and forwards them to the appropriate application container. This setup also makes it easy to manage SSL/TLS certificates.

1.  **Enable necessary Apache modules**:
    ```bash
    sudo a2enmod proxy
    sudo a2enmod proxy_http
    sudo systemctl restart apache2
    ```

2.  **Create an Apache site configuration file**:
    Create a new configuration file for your application. Replace `your_domain.com` with your actual domain name.
    ```bash
    sudo nano /etc/apache2/sites-available/eia.conf
    ```

3.  **Add the reverse proxy configuration**:
    Paste the following configuration into the file. This tells Apache to forward all requests for `your_domain.com` to the Gunicorn server running inside our Docker container on port 8000.

    ```apache
    <VirtualHost *:80>
        ServerName your_domain.com
        ServerAdmin webmaster@localhost

        # Redirect HTTP to HTTPS (recommended for production)
        # Uncomment the following lines after setting up SSL with Certbot
        # RewriteEngine On
        # RewriteCond %{HTTPS} off
        # RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]

        ErrorLog ${APACHE_LOG_DIR}/eia-error.log
        CustomLog ${APACHE_LOG_DIR}/eia-access.log combined
    </VirtualHost>

    # For HTTPS configuration (after running Certbot)
    # <IfModule mod_ssl.c>
    # <VirtualHost *:443>
    #     ServerName your_domain.com
    #
    #     ProxyPreserveHost On
    #     ProxyRequests Off
    #     ProxyPass / http://127.0.0.1:8000/
    #     ProxyPassReverse / http://127.0.0.1:8000/
    #
    #     SSLEngine on
    #     SSLCertificateFile /etc/letsencrypt/live/your_domain.com/fullchain.pem
    #     SSLCertificateKeyFile /etc/letsencrypt/live/your_domain.com/privkey.pem
    #     Include /etc/letsencrypt/options-ssl-apache.conf
    # </VirtualHost>
    # </IfModule>
    ```
    **Note**: The above example includes a placeholder for HTTPS. For a production site, you should secure it with SSL. The easiest way is using **Certbot** (`sudo apt-get install certbot python3-certbot-apache`), which will automatically obtain a certificate and configure the Apache file for you.

4.  **Enable the new site and restart Apache**:
    ```bash
    sudo a2ensite eia.conf
    sudo systemctl restart apache2
    ```

Your EIA application should now be accessible at `http://your_domain.com`.

## Managing the Application

*   **To stop the application**: `docker-compose down`
*   **To view logs**: `docker-compose logs -f <service_name>` (e.g., `backend`, `worker`)
*   **To update the application**:
    1.  Pull the latest code (`git pull`).
    2.  Rebuild the images: `docker-compose build`
    3.  Restart the services: `docker-compose up -d`
*   **To run a CLI command**: `docker-compose run --rm backend python eia_cli.py <command>`