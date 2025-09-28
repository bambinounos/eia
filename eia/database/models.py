import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    Text,
    ForeignKey,
    Date,
    Enum,
    UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base

# Base class for our declarative models
Base = declarative_base()

class OpportunityStatus(Enum):
    PENDING = "pending_review"
    APPROVED = "approved"
    DISCARDED = "discarded"

class ProcessedEmail(Base):
    """
    Keeps track of emails that have been processed to prevent duplicates.
    """
    __tablename__ = "processed_emails"

    id = Column(Integer, primary_key=True)
    account = Column(String, nullable=False, index=True)
    uid = Column(String, nullable=False, index=True)
    folder = Column(String, nullable=False, index=True)
    processed_at = Column(DateTime, default=datetime.datetime.utcnow)

    # A processed email might or might not result in an opportunity.
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=True)
    opportunity = relationship("Opportunity", back_populates="source_email", uselist=False)

    __table_args__ = (
        UniqueConstraint('account', 'uid', 'folder', name='_account_uid_folder_uc'),
    )

    def __repr__(self):
        return f"<ProcessedEmail(id={self.id}, account='{self.account}', uid='{self.uid}')>"


class Opportunity(Base):
    """
    Stores the details of a detected business opportunity.
    """
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True)

    # Link back to the source email
    source_email_id = Column(Integer, ForeignKey('processed_emails.id'), unique=True, nullable=False)
    source_email = relationship("ProcessedEmail", back_populates="opportunity")

    # Raw email info
    subject = Column(String, nullable=False)
    sender = Column(String, nullable=False)
    original_body = Column(Text, nullable=True)

    # NLP Analysis Results
    classification = Column(String, nullable=False, index=True)
    classification_confidence = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    is_relevant = Column(Boolean, default=False, index=True)
    relevance_confidence = Column(Float, nullable=True)

    # Extracted Entities
    entity_name = Column(String, nullable=True)
    entity_contact_email = Column(String, nullable=True)
    entity_deadline = Column(Date, nullable=True)
    entity_amount = Column(Float, nullable=True)

    # Metadata
    status = Column(String, default='pending_review', nullable=False, index=True)
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship to products
    products = relationship("OpportunityProduct", back_populates="opportunity", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Opportunity(id={self.id}, subject='{self.subject[:30]}...', status='{self.status}')>"


class OpportunityProduct(Base):
    """
    Associates an opportunity with one or more matched products from the catalog.
    """
    __tablename__ = "opportunity_products"

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    product_name = Column(String, nullable=False)

    opportunity = relationship("Opportunity", back_populates="products")

    def __repr__(self):
        return f"<OpportunityProduct(opportunity_id={self.opportunity_id}, product='{self.product_name}')>"

# Example of how to create the engine and tables
if __name__ == '__main__':
    # This is for demonstration/testing purposes.
    # The actual engine will be created in session.py using the config.
    from sqlalchemy import create_engine
    from ..config import settings

    if settings:
        # Using an in-memory SQLite database for this example.
        # In production, this would be settings.database.url
        engine = create_engine("sqlite:///:memory:")

        print("Creating database tables...")
        Base.metadata.create_all(engine)
        print("Tables created successfully.")

        # You can inspect the created tables
        from sqlalchemy.inspection import inspect
        inspector = inspect(engine)
        print("\nTables in database:")
        for table_name in inspector.get_table_names():
            print(f"- {table_name}")
            for column in inspector.get_columns(table_name):
                print(f"  - {column['name']} ({column['type']})")

    else:
        print("Could not load settings. Cannot demonstrate table creation.")