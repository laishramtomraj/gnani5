"""registration_service.py - the registration functions the pages (and, later, the assistant) call.

No Streamlit code here. The pages only collect answers and show results; every rule lives below.

  review_registration()        validate + eligibility check, nothing is saved
  submit_registration()        re-validates, then saves; returns the confirmation with the reference number
  check_registration_status()  reference + registered email -> status (the only way to read a registration)

For the future assistant:
  * Course facts come from course_service (which reads the existing course data).
  * It may call review_registration() on answers a student chose to share, to explain eligibility.
  * It may call check_registration_status() only with the reference and email the student typed.
  * It must NOT call submit_registration() on its own, and must never call registration_db.record_status_change().
"""
from __future__ import annotations

import course_service
import registration_db
import registration_validation as validation
from data import DATA_IS_SAMPLE
from eligibility import OUTCOME_NOT_MET, check_eligibility
from registration_db import LookupRefused, RegistrationStorageError  # noqa: F401  (re-exported for callers)


class SubmissionRefused(Exception):
    """The registration was not saved because validation failed. `errors` maps field name -> message."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(errors.values()))
        self.errors = errors


def review_registration(course_id: str | None, data: dict) -> dict:
    """Validate the answers and, when they are valid, compare them with the stored eligibility rules."""
    course = course_service.get_course(course_id)
    errors = validation.validate_registration(course, data)
    cleaned = validation.normalize(data)
    eligibility = check_eligibility(course, cleaned) if course and not errors else None
    return {"course": course, "errors": errors, "cleaned": cleaned, "eligibility": eligibility}


def submit_registration(course_id: str | None, data: dict, submission_token: str,
                        eligibility_acknowledged: bool = False) -> dict:
    """Save a registration. Always re-checks the answers, so a page cannot skip validation.

    Returns {"reference", "status", "course_name", "submitted_at", "already_submitted", ...}.
    Raises SubmissionRefused (answers invalid) or RegistrationStorageError (could not be saved).
    """
    review = review_registration(course_id, data)
    if review["errors"]:
        raise SubmissionRefused(review["errors"])
    eligibility = review["eligibility"]
    if eligibility["outcome"] == OUTCOME_NOT_MET and not eligibility_acknowledged:
        raise SubmissionRefused({"eligibility_acknowledged":
                                 "Tick the box to confirm you understand your answers do not meet the stored criteria."})
    course = review["course"]
    record = {
        **review["cleaned"],
        "course_id": course["id"],
        "course_name": course["name"],
        "eligibility_outcome": eligibility["outcome"],
        "eligibility_details": eligibility["checks"],
        "eligibility_acknowledged": eligibility_acknowledged,
        "course_data_is_sample": DATA_IS_SAMPLE,
    }
    return registration_db.create_registration(record, submission_token)


def check_registration_status(reference: str, email: str) -> dict:
    """Return the status of one registration. Raises LookupRefused unless reference and email both match."""
    return registration_db.lookup_status(reference, email)
