from .worker import celery_app
from .config import settings
from .email_client import EmailClient, EmailConnectionError
from .nlp_processor import NlpProcessor
from .database.session import SessionLocal
from .database import models
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery_app.task(name="eia.tasks.process_all_accounts_task")
def process_all_accounts_task():
    """
    Celery task to scan and process emails for all configured accounts.
    """
    if not settings or not settings.email_accounts:
        logger.warning("No email accounts configured. Skipping email processing.")
        return

    logger.info("Starting periodic email scan for all accounts...")
    nlp_processor = NlpProcessor(catalog_path=settings.product_catalog_path)

    for account_config in settings.email_accounts:
        logger.info(f"Processing account: {account_config.email}")
        try:
            with EmailClient(account_config) as client:
                db = SessionLocal()
                try:
                    for folder in account_config.folders_to_scan:
                        logger.info(f"Scanning folder: '{folder}'")
                        emails_to_mark_read = []

                        unread_emails = client.fetch_unread_emails(folder=folder)

                        for email_data in unread_emails:
                            uid = email_data['uid']

                            # 1. Check if email has already been processed
                            is_processed = db.query(models.ProcessedEmail).filter_by(
                                account=account_config.email,
                                uid=str(uid),
                                folder=folder
                            ).first()

                            if is_processed:
                                logger.info(f"Email UID {uid} already processed. Skipping.")
                                continue

                            logger.info(f"Processing new email - UID: {uid}, Subject: {email_data['subject']}")

                            # 2. Mark as processed in DB immediately to prevent race conditions
                            processed_email_entry = models.ProcessedEmail(
                                account=account_config.email,
                                uid=str(uid),
                                folder=folder
                            )
                            db.add(processed_email_entry)
                            db.commit() # Commit this first

                            # 3. Analyze with NLP
                            nlp_result = nlp_processor.analyze(email_data['body'])

                            # 4. If relevant, create an opportunity
                            if nlp_result['es_relevante']:
                                logger.info(f"Relevant opportunity found in email UID {uid}.")

                                # Create the opportunity record
                                new_opportunity = models.Opportunity(
                                    source_email=processed_email_entry,
                                    subject=email_data['subject'],
                                    sender=email_data['from'],
                                    original_body=email_data['body'],
                                    classification=nlp_result['clasificacion'],
                                    classification_confidence=nlp_result['confianza_clasificacion'],
                                    summary=nlp_result['resumen'],
                                    is_relevant=nlp_result['es_relevante'],
                                    relevance_confidence=nlp_result['confianza_relevancia'],
                                    entity_name=nlp_result['entidades'].get('entidad'),
                                    entity_contact_email=nlp_result['entidades'].get('contacto_email'),
                                    entity_deadline=nlp_result['entidades'].get('fecha_limite'),
                                    entity_amount=nlp_result['entidades'].get('monto'),
                                    status='pending_review'
                                )

                                # Add associated products
                                for product_name in nlp_result['entidades'].get('productos', []):
                                    new_opportunity.products.append(
                                        models.OpportunityProduct(product_name=product_name)
                                    )

                                db.add(new_opportunity)
                                db.commit()
                                logger.info(f"Opportunity saved to database with ID: {new_opportunity.id}")

                            # 5. Add to list to be marked as read on the server
                            emails_to_mark_read.append(uid)

                        # 6. Mark emails as read on IMAP server
                        if settings.imap.mark_as_seen and emails_to_mark_read:
                            client.mark_as_read(emails_to_mark_read)

                finally:
                    db.close()

        except EmailConnectionError as e:
            logger.error(f"Failed to connect to email account {account_config.email}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing account {account_config.email}: {e}", exc_info=True)

    logger.info("Email scan finished.")
    return "Email processing complete for all accounts."