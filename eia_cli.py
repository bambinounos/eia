import click
import os
import sys

# Ensure the project root is in the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from eia.config import settings, load_config
from eia.tasks import process_all_accounts_task
from scripts.init_db import initialize_database

@click.group()
def cli():
    """
    Email Intelligence Analyzer (EIA) Command-Line Interface.

    A tool for managing the EIA application, from database setup to task execution.
    """
    # Check if config is loaded, as it's needed for most commands
    if not settings:
        click.secho("Error: Could not load configuration from 'config.yml'.", fg="red")
        click.secho("Please ensure 'config.yml' exists and is correctly formatted.", fg="yellow")
        sys.exit(1)
    pass

@cli.command("init-db")
def init_db_command():
    """
    Initializes the database by creating all necessary tables.

    This command should be run once during the initial setup.
    """
    click.confirm("This will create new tables in the database. Are you sure?", abort=True)
    try:
        initialize_database()
        click.secho("Database initialized successfully!", fg="green")
    except Exception as e:
        click.secho(f"Database initialization failed: {e}", fg="red")
        sys.exit(1)

@cli.command("scan-emails")
@click.option('--async', 'is_async', is_flag=True, help="Run the scan asynchronously via Celery worker.")
def scan_emails_command(is_async):
    """
    Triggers a scan for new emails in all configured accounts.

    By default, this runs the task directly (synchronously). Use the --async flag
    to queue the task with Celery, which requires a worker to be running.
    """
    click.echo("Triggering email scan...")
    if is_async:
        try:
            task = process_all_accounts_task.delay()
            click.secho(f"Email scan has been queued asynchronously. Task ID: {task.id}", fg="green")
        except Exception as e:
            click.secho(f"Error queuing task with Celery: {e}", fg="red")
            click.secho("Is the Redis broker running and accessible?", fg="yellow")
            sys.exit(1)
    else:
        click.echo("Running scan synchronously. This may take a while...")
        try:
            result = process_all_accounts_task()
            click.secho(f"Synchronous scan finished. Result: {result}", fg="green")
        except Exception as e:
            click.secho(f"An error occurred during the synchronous scan: {e}", fg="red")
            sys.exit(1)

@cli.command("check-config")
def check_config_command():
    """
    Loads and displays the current application configuration.

    This is useful for verifying that 'config.yml' is being read correctly.
    """
    click.echo("Loading and validating configuration...")
    try:
        # The settings object is already loaded, but we can re-load to be sure
        config = load_config()
        click.secho("Configuration loaded successfully!", fg="green")
        click.echo("---")
        click.echo(f"Database URL: {config.database.url}")
        click.echo(f"Redis URL: {config.redis.url}")
        click.echo(f"Scan Interval: {config.imap.scan_interval_minutes} minutes")
        click.echo(f"Number of Email Accounts: {len(config.email_accounts)}")
        for i, acc in enumerate(config.email_accounts):
            click.echo(f"  - Account #{i+1}: {acc.email} on {acc.imap_server}")
        click.echo("---")
    except (FileNotFoundError, ValueError) as e:
        click.secho(f"Failed to load or validate configuration: {e}", fg="red")
        sys.exit(1)

if __name__ == '__main__':
    cli()