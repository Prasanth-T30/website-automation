"""Realistic sample data for walking through the console.

Written through the repositories rather than the HTTP API on purpose: the
reject, offer-letter and certificate endpoints all send real mail, and a demo
dataset must never put anything on the wire. Nothing here is imported by the
running app — `python -m app.cli demo <project-id>` is the only caller.

The shape is chosen so every screen has something to show:

* Applications  - unclaimed, claimed, approved and rejected, so all four tabs fill
* Students      - spread across the HRs, in and out of batches
* Batches       - one finishing this week, one mid-flight, one not yet open
* Payments      - settled, part-paid and overdue, so Finance has a real spread
* Attendance    - a fortnight of marks for the batch that is running
* Certificates  - the finishing batch puts real names on the Certificates tab
* Offer letters - everyone who has paid becomes a candidate
"""

from __future__ import annotations

import random
from datetime import UTC, date, datetime, timedelta

from app.repositories.activity import ActivityRepository
from app.repositories.announcements import AnnouncementRepository
from app.repositories.applications import ApplicationRepository
from app.repositories.attendance import AttendanceRepository
from app.repositories.batches import BatchRepository
from app.repositories.events import EventRepository
from app.repositories.payments import PaymentRepository
from app.repositories.students import StudentRepository
from app.repositories.users import UserRepository

# Fixed so two runs of the demo produce the same story, which makes it usable
# for screenshots and for talking someone through the screens.
_RNG = random.Random(20260823)


def _iso(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


# name, college, place, native, passing year, phone tail
_PEOPLE = [
    ("Mr.", "Arun Kumar S", "Anna University", "Chennai", "Salem", "2027"),
    ("Ms.", "Divya Lakshmi R", "PSG College of Technology", "Coimbatore", "Erode", "2026"),
    ("Mr.", "Karthik Raja M", "Thiagarajar College of Engineering", "Madurai", "Theni", "2027"),
    ("Ms.", "Priya Dharshini K", "Rajalakshmi Engineering College", "Chennai", "Vellore", "2026"),
    ("Mr.", "Mohammed Irfan A", "Sri Krishna College of Engineering", "Coimbatore",
     "Tirunelveli", "2028"),
    ("Ms.", "Sneha Priya V", "SSN College of Engineering", "Chennai", "Kanchipuram", "2027"),
    ("Mr.", "Vignesh Prabhu T", "Kongu Engineering College", "Erode", "Namakkal", "2026"),
    ("Ms.", "Aishwarya Nandhini P", "Coimbatore Institute of Technology", "Coimbatore",
     "Tiruppur", "2027"),
    ("Mr.", "Hari Prasath G", "Velammal Engineering College", "Chennai", "Cuddalore", "2028"),
    ("Ms.", "Meenakshi Sundari J", "Mepco Schlenk Engineering College", "Sivakasi",
     "Virudhunagar", "2026"),
    ("Mr.", "Naveen Balaji C", "Bannari Amman Institute of Technology", "Sathyamangalam",
     "Gobi", "2027"),
    ("Ms.", "Keerthana Shri L", "Sona College of Technology", "Salem", "Dharmapuri", "2026"),
    ("Mr.", "Surya Prakash N", "Government College of Technology", "Coimbatore",
     "Pollachi", "2028"),
    ("Ms.", "Janani Devi B", "Easwari Engineering College", "Chennai", "Thiruvallur", "2027"),
    ("Mr.", "Rahul Krishnan D", "Amrita Vishwa Vidyapeetham", "Coimbatore", "Palakkad", "2026"),
]


def _email_for(name: str) -> str:
    first = name.split()[0].lower()
    return f"{first}.{_RNG.randint(100, 999)}@example.com"


def _phone() -> str:
    return f"9{_RNG.randint(100000000, 999999999)}"


def build(db) -> dict:
    """Create the dataset. Returns a summary of what was made."""
    users = UserRepository(db)
    apps = ApplicationRepository(db)
    students = StudentRepository(db)
    batches = BatchRepository(db)
    events = EventRepository(db)
    payments = PaymentRepository(db)
    attendance = AttendanceRepository(db)
    announcements = AnnouncementRepository(db)
    activity = ActivityRepository(db)

    staff = users.list_all()
    admin = next((u for u in staff if u.role.value == "admin"), None)
    hrs = [u for u in staff if u.role.value == "hr"]
    if admin is None or not hrs:
        raise RuntimeError("Run `python -m app.cli seed` first — no accounts to own the data.")

    made = dict(batches=0, applications=0, students=0, payments=0,
                attendance=0, announcements=0, events=0)

    # ── Batches ──────────────────────────────────────────────────────────
    # The first one ends in three days, which is what puts names on the
    # Certificates tab without anyone having to touch a status field.
    plan = [
        ("FSJ-2026-A", "Full Stack Java", -27, 3, 20, "active", "Finishing this week."),
        ("DSA-2026-B", "Data Science and AI", -12, 33, 18, "active", "Mid-way through."),
        ("UIX-2026-C", "UI/UX Design and Prototyping", 10, 55, 15, "upcoming", "Opens next month."),
    ]
    made_batches = []
    for code, domain, starts, ends, cap, status, note in plan:
        b = batches.create(
            code=code, domain=domain, start_date=_iso(starts), end_date=_iso(ends),
            capacity=cap, notes=note, created_by_id=admin.id,
        )
        if status != "upcoming":
            b = batches.update_fields(b.id, {"status": status})
        made_batches.append(b)
        made["batches"] += 1

    finishing, running, upcoming = made_batches

    # ── Students, via real applications so they trace back to a registration
    # ── (that is what the offer-letter and certificate screens read) ──────
    def registration(person, *, domain, duration, starts, ends, amount,
                     category="Internship", method="upi", hr_name=None):
        """One public registration.

        `method="cash"` builds the shape a cash submission actually arrives
        in — no amount, no reference, no screenshot — rather than a UPI row
        with the method relabelled, so the console screens are exercised
        against the real thing.
        """
        title, name, college, place, native, year = person
        cash = method == "cash"
        return apps.create(
            title=title, name=name, email=_email_for(name), phone=_phone(),
            college=college, place=place, department="CSE", year="Final",
            applicant_type="student", category=category, domain=domain,
            duration=duration, start_date=starts, end_date=ends,
            payment_method=method,
            amount=None if cash else amount,
            transaction_id=None if cash else f"TXN{_RNG.randint(10**7, 10**8 - 1)}",
            payment_screenshot=None, mode="Offline", project_topic=None,
            # Required on the public form, so every sample row carries one —
            # otherwise the console's "HR:" line would be blank everywhere
            # and the field would look broken rather than mandatory.
            hr_name=hr_name or _RNG.choice([h.full_name for h in hrs]),
            other=None, native_place=native,
            passed_out_year=year, declaration=True,
        )

    enrolled = []

    # Six in the batch that finishes this week -> Certificates tab.
    for person in _PEOPLE[:6]:
        owner = hrs[len(enrolled) % len(hrs)]
        a = registration(person, domain=finishing.domain, duration="30 Days",
                         starts=finishing.start_date, ends=finishing.end_date, amount=5000)
        apps.claim(a.id, owner.id)
        total = _RNG.choice([18000, 20000, 25000])
        s = students.create_from_application(apps.get(a.id), total_fees=total)
        apps.mark_approved(a.id, student_id=s.id, subject="", body="", email_sent=False)
        students.update(s.id, {"batch_id": finishing.id})
        payments.record(student_id=s.id, owner_id=owner.id, amount=a.amount, method=None,
                        notes=f"Registration payment (transaction {a.transaction_id})",
                        recorded_by_id=owner.id)
        enrolled.append((s, owner, total, a.amount, finishing.id))
        made["applications"] += 1
        made["students"] += 1
        made["payments"] += 1

    # Five in the batch still running.
    for person in _PEOPLE[6:11]:
        owner = hrs[len(enrolled) % len(hrs)]
        a = registration(person, domain=running.domain, duration="60 Days",
                         starts=running.start_date, ends=running.end_date, amount=6000)
        apps.claim(a.id, owner.id)
        total = _RNG.choice([22000, 28000, 30000])
        s = students.create_from_application(apps.get(a.id), total_fees=total)
        apps.mark_approved(a.id, student_id=s.id, subject="", body="", email_sent=False)
        students.update(s.id, {"batch_id": running.id})
        payments.record(student_id=s.id, owner_id=owner.id, amount=a.amount, method=None,
                        notes=f"Registration payment (transaction {a.transaction_id})",
                        recorded_by_id=owner.id)
        enrolled.append((s, owner, total, a.amount, running.id))
        made["applications"] += 1
        made["students"] += 1
        made["payments"] += 1

    # ── Follow-up installments, so Finance shows a real spread ────────────
    # Roughly: a third settled, a third part-paid, a third still owing only
    # their deposit (which is what tips them into "overdue" on the dashboard).
    methods = ["UPI", "Bank Transfer", "Cash", "Card"]
    for idx, (s, owner, total, paid_so_far, _batch) in enumerate(enrolled):
        if idx % 3 == 0:
            instalments = [total - paid_so_far]                 # settles in full
        elif idx % 3 == 1:
            instalments = [round((total - paid_so_far) * 0.5)]  # half the balance
        else:
            instalments = []                                    # deposit only
        running_total = paid_so_far
        for amount in instalments:
            if amount <= 0:
                continue
            payments.record(student_id=s.id, owner_id=owner.id, amount=float(amount),
                            method=_RNG.choice(methods), notes="Installment",
                            recorded_by_id=owner.id)
            running_total += amount
            made["payments"] += 1
        students.update(s.id, {"fees_paid": float(running_total)})

    # ── Two walk-ins with no application behind them ─────────────────────
    for person in _PEOPLE[11:13]:
        title, name, college, place, _, _ = person
        owner = _RNG.choice(hrs)
        s = students.create_manual(
            owner_id=owner.id, name=name, email=_email_for(name), phone=_phone(),
            college=college, place=place, category="Course",
            domain="Software Testing", duration="45 Days", batch_id=None,
            total_fees=15000, fees_paid=5000,
        )
        payments.record(student_id=s.id, owner_id=owner.id, amount=5000, method="Cash",
                        notes="Opening balance recorded when the student was added by hand",
                        recorded_by_id=owner.id)
        made["students"] += 1
        made["payments"] += 1

    # ── Applications left mid-flow, so the queue is not empty ────────────
    for person in _PEOPLE[13:]:                       # unclaimed, awaiting a decision
        registration(person, domain="Cloud Computing", duration="30 Days",
                     starts=_iso(14), ends=_iso(44), amount=4000)
        made["applications"] += 1

    for person in _PEOPLE[:2]:                        # claimed but not yet decided
        a = registration(person, domain="Data Analytics", duration="45 Days",
                         starts=_iso(7), ends=_iso(52), amount=4500, category="Course")
        apps.claim(a.id, hrs[0].id)
        made["applications"] += 1

    # Paying at the desk rather than online: these arrive with no amount and
    # no reference at all, and read as "Cash · at desk" in the queue until an
    # HR records what was actually collected.
    for person, referred_by in zip(_PEOPLE[3:5], [h.full_name for h in hrs], strict=False):
        registration(person, domain="Web Development", duration="30 Days",
                     starts=_iso(10), ends=_iso(40), amount=0,
                     method="cash", hr_name=referred_by)
        made["applications"] += 1

    # Rejected straight through the repository: the HTTP endpoint emails the
    # applicant, and sample data has no business sending real mail.
    rejected = registration(_PEOPLE[2], domain="Business Analytics", duration="15 Days",
                            starts=_iso(5), ends=_iso(20), amount=2000, category="Project")
    apps.claim(rejected.id, hrs[1].id)
    apps.mark_rejected(rejected.id, "Payment screenshot did not match the transaction reference.")
    made["applications"] += 1

    # ── A fortnight of attendance for the batch that is running ──────────
    in_running = [s for s, _o, _t, _a, batch_id in enrolled if batch_id == running.id]
    for offset in range(14, 0, -1):
        day = date.today() - timedelta(days=offset)
        if day.weekday() >= 5:            # the institute does not run weekends
            continue
        for s in in_running:
            attendance.mark(
                student_id=s.id, batch_id=running.id, date_iso=day.isoformat(),
                status="present" if _RNG.random() > 0.12 else "absent", notes=None,
            )
            made["attendance"] += 1

    # ── Off-campus events, spread across the HRs ─────────────────────────
    # Private to whoever owns them, so signing in as two different HRs shows
    # two different Events pages — which is the whole point of the feature.
    # Every kind is represented, and some still have money outstanding so the
    # "to receive" column is not uniformly zero.
    event_plan = [
        ("workshop", "Anna University", 60, 30000, 20000, -40, -38, 2),
        ("bootcamp", "PSG College of Technology", 45, 75000, 0, -30, -24, 6),
        ("training_program", "Kongu Engineering College", 120, 180000, 45000, -60, -20, 15),
        ("addon_course", "Thiagarajar College", 35, 42000, 8000, -21, -7, 10),
        ("industrial_visit", "SSN College of Engineering", 90, 27000, 0, -14, -14, 1),
        ("workshop", "Sri Krishna College", 55, 25000, 12500, -9, -8, 2),
    ]
    for i, (kind, college, heads, got, owed, starts, ends, days) in enumerate(event_plan):
        owner = hrs[i % len(hrs)]
        events.create(
            owner_id=owner.id, recorded_by_id=owner.id,
            event_type=kind, college=college, student_count=heads,
            amount_collected=got, amount_receivable=owed,
            start_date=_iso(starts), end_date=_iso(ends), days_conducted=days,
            notes=None,
        )
        made["events"] += 1

    # ── Announcements ────────────────────────────────────────────────────
    for title, body, level in [
        ("Certificates due this week",
         f"{finishing.code} finishes on {finishing.end_date}. Issue certificates from Documents.",
         "warning"),
        ("New batch opens next month",
         f"{upcoming.code} starts {upcoming.start_date}. Begin assigning students.", "info"),
    ]:
        announcements.create(
            title=title, body=body, level=level, created_by_id=admin.id,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        made["announcements"] += 1

    activity.record(action="demo.seeded", entity_type="system", entity_id="demo",
                    summary=f"Loaded demo data: {made}")
    return made
