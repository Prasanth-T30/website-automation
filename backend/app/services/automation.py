"""Scheduled document sending.

Offer letters go out once a student has actually paid; certificates go out
once their programme has ended. Both are sent by the same code the console
uses, so an automatic letter is identical to a hand-sent one.

This removes the human check the console deliberately puts in front of every
send, so the safety has to come from the design instead:

* **Off unless switched on.** `AUTOMATION_ENABLED` defaults to false, so
  deploying this changes nothing until someone decides otherwise.
* **Dry run.** Every entry point can report exactly what it would send
  without sending it.
* **Idempotent.** A document already filed for a student is never sent again;
  the filed report *is* the record, the same one the console reads to show
  "Sent".
* **Capped.** A run will not send more than `AUTOMATION_MAX_PER_RUN`. A bad
  query or a bulk import cannot turn into hundreds of emails before anyone
  notices.
* **Audited.** Every send is recorded against the student exactly as a manual
  one is, attributed to the automation rather than to a person.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.core.config import settings
from app.models.student import Student
from app.services import documents

# Who the audit trail credits. Not a real account, and deliberately not an
# admin's id: "who sent this?" should never point at a person who did not.
AUTOMATION_ACTOR = "system:automation"


@dataclass
class Planned:
    kind: str
    student_id: str
    name: str
    email: str
    reason: str


@dataclass
class RunReport:
    dry_run: bool
    enabled: bool
    planned: list[Planned] = field(default_factory=list)
    sent: list[dict] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)
    skipped_over_cap: int = 0

    def as_dict(self) -> dict:
        return {
            "dry_run": self.dry_run,
            "enabled": self.enabled,
            "planned": [p.__dict__ for p in self.planned],
            "sent": self.sent,
            "failed": self.failed,
            "skipped_over_cap": self.skipped_over_cap,
        }


def _days_remaining(end_date: str | None) -> int | None:
    if not end_date:
        return None
    try:
        return (date.fromisoformat(str(end_date)[:10]) - date.today()).days
    except ValueError:
        return None


def plan(*, students, payments, reports, batches, applications) -> list[Planned]:
    """Work out what is due, touching nothing.

    Deliberately the whole decision: `run` does no eligibility thinking of its
    own, so a dry run and a real run can never disagree about who qualifies.
    """
    paid_for = {p.student_id for p in payments.list_all() if p.amount > 0}
    filed = {"offer_letter": set(), "certificate": set()}
    for category in filed:
        filed[category] = {
            r.student_id for r in reports.list_all(category=category) if r.student_id
        }

    due: list[Planned] = []
    for s in students.list_all():
        if s.status == "dropped" or not s.email:
            continue

        if s.id in paid_for and s.id not in filed["offer_letter"]:
            due.append(
                Planned(
                    kind="offer_letter", student_id=s.id, name=s.name, email=s.email,
                    reason="has paid and has no offer letter on file",
                )
            )

        if s.id in filed["certificate"]:
            continue
        # Certificates wait for the programme to be genuinely over, not merely
        # near its end. The console offers them five days early so an HR can
        # prepare one; sending early unprompted would be wrong.
        end = _programme_end(s, batches, applications)
        remaining = _days_remaining(end)
        finished = s.status == "completed" or (remaining is not None and remaining < 0)
        if finished:
            due.append(
                Planned(
                    kind="certificate", student_id=s.id, name=s.name, email=s.email,
                    reason=("marked completed" if s.status == "completed"
                            else f"programme ended {abs(remaining)} day(s) ago"),
                )
            )
    return due


def _programme_end(student: Student, batches, applications) -> str | None:
    if student.batch_id:
        batch = batches.get(student.batch_id)
        if batch and batch.end_date:
            return str(batch.end_date)
    if student.application_id:
        source = applications.get(student.application_id)
        if source and source.end_date:
            return str(source.end_date)
    return None


def run(
    *,
    students,
    payments,
    reports,
    batches,
    applications,
    storage,
    activity_repo,
    offer_letter_fields,
    dry_run: bool = True,
) -> RunReport:
    """Send everything that is due.

    `offer_letter_fields` is passed in rather than imported so this module
    stays independent of the API layer that assembles a letter's contents.
    """
    report = RunReport(dry_run=dry_run, enabled=settings.automation_enabled)
    report.planned = plan(
        students=students, payments=payments, reports=reports,
        batches=batches, applications=applications,
    )

    # A dry run reports and stops. So does a live run while the feature is
    # switched off — the plan is still useful to look at.
    if dry_run or not settings.automation_enabled:
        return report

    cap = settings.automation_max_per_run
    for item in report.planned[:cap]:
        student = students.get(item.student_id)
        if student is None:
            continue
        try:
            if item.kind == "offer_letter":
                result = documents.issue_offer_letter(
                    student=student,
                    fields=offer_letter_fields(student, applications),
                    subject=None, body=None,
                    storage=storage, reports=reports, activity_repo=activity_repo,
                    actor_id=AUTOMATION_ACTOR,
                )
            else:
                batch = batches.get(student.batch_id) if student.batch_id else None
                result = documents.issue_certificate(
                    student=student, awardee=student, batch=batch,
                    subject=None, body=None,
                    storage=storage, reports=reports, activity_repo=activity_repo,
                    actor_id=AUTOMATION_ACTOR,
                )
            report.sent.append(
                {"kind": item.kind, "student_id": item.student_id, "name": item.name,
                 "emailed_to": result.emailed_to, "email_sent": result.email_sent,
                 "report_id": result.report_id}
            )
        except Exception as exc:  # noqa: BLE001 - one bad record must not stop the run
            report.failed.append(
                {"kind": item.kind, "student_id": item.student_id,
                 "name": item.name, "error": str(exc)[:200]}
            )

    report.skipped_over_cap = max(0, len(report.planned) - cap)
    return report
