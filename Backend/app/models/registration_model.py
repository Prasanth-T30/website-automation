"""
Plain data-shape reference for a `registrations` document in MongoDB.
Motor works with plain dicts, so this class exists purely as documentation /
a single source of truth for field names used across services and routes.
"""
from datetime import datetime
from typing import Optional


class RegistrationModel:
    """
    Collection: registrations
    """

    def __init__(
        self,
        registration_id: str,
        name: str,
        email: str,
        phone: str,
        college: str,
        place: str,
        department: Optional[str],
        year: Optional[str],
        domain: str,
        duration: str,
        start_date: str,
        end_date: str,
        amount: float,
        transaction_id: str,
        payment_screenshot: str,
        title: Optional[str] = None,
        applicant_type: str = "student",
        category: str = "Internship",
        status: str = "Pending",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        _id=None,
    ):
        self._id = _id
        self.registration_id = registration_id
        self.title = title
        self.name = name
        self.email = email
        self.phone = phone
        self.college = college
        self.place = place
        self.department = department
        self.year = year
        self.applicant_type = applicant_type
        self.category = category
        self.domain = domain
        self.duration = duration
        self.start_date = start_date
        self.end_date = end_date
        self.amount = amount
        self.transaction_id = transaction_id
        self.payment_screenshot = payment_screenshot
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k != "_id"}
