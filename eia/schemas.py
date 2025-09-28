import datetime
from pydantic import BaseModel
from typing import List, Optional

# This file contains the Pydantic models (schemas) that define the structure
# of the data for the API requests and responses.
# Separating them from the database models is a good practice as it decouples
# the API's public contract from the internal database structure.

# --- Schemas for Opportunity Products ---

class OpportunityProductSchema(BaseModel):
    """
    Schema for a product associated with an opportunity.
    """
    product_name: str

    class Config:
        # This allows the Pydantic model to be created from an ORM object
        orm_mode = True


# --- Schemas for Opportunities ---

class OpportunityBase(BaseModel):
    """
    Base schema for an opportunity, containing common fields.
    """
    subject: str
    sender: str
    classification: str
    summary: Optional[str]
    status: str
    is_relevant: bool
    entity_name: Optional[str]
    entity_contact_email: Optional[str] = None
    entity_deadline: Optional[datetime.date] = None
    entity_amount: Optional[float] = None


class OpportunitySchema(OpportunityBase):
    """
    The main schema for representing a single opportunity in API responses.
    """
    id: int
    detected_at: datetime.datetime
    products: List[OpportunityProductSchema] = []

    class Config:
        orm_mode = True


class OpportunityListResponse(BaseModel):
    """
    Schema for the response when listing multiple opportunities.
    """
    total: int
    opportunities: List[OpportunitySchema]


# --- Schema for triggering a manual scan ---
class ManualScanRequest(BaseModel):
    """
    Request body for manually triggering an email scan.
    Allows specifying a particular account or all accounts.
    """
    account_email: Optional[str] = None # If null, scans all accounts
    force_rescan_all: bool = False # If true, ignores "seen" flags (for debugging)