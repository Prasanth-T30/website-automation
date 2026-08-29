"""Choice lists shared by the registration form and its validation.

Verbatim from DVein's live programme catalogue — these are the institute's
actual programme categories and domains, not an invented list.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

TITLE_CHOICES = ["Mr.", "Ms.", "Mrs.", "Dr."]

CATEGORY_CHOICES = ["Internship", "Course", "Project"]

# Approval emails (with the PDF offer/completion letter) are only sent for
# these categories. "Project" registrations are approved/rejected like any
# other, but no email or PDF is generated.
EMAIL_ENABLED_CATEGORIES = {"Internship", "Course"}

@dataclass(frozen=True)
class Domain:
    """One programme the institute runs.

    `summary` and `stack` are what the public registration site renders on each
    programme card; the HRM only needs `name`, but both live here so the two
    front-ends can never drift out of sync with each other.
    """

    name: str
    summary: str
    stack: tuple[str, ...]


DOMAIN_CATALOG: tuple[Domain, ...] = (
    Domain(
        "Full Stack Java",
        "Build enterprise-grade applications with Java, Spring Boot, REST APIs, and scalable "
        "backend systems.",
        ("Java", "Spring Boot", "REST API", "MySQL"),
    ),
    Domain(
        "Full Stack Python",
        "End-to-end Python development using Django, FastAPI, and modern frontend integration.",
        ("Python", "Django", "FastAPI", "PostgreSQL"),
    ),
    Domain(
        "Data Science and AI",
        "Explore data pipelines, statistical modelling, and AI-driven applications using Python "
        "and real datasets.",
        ("Python", "Pandas", "Statistics", "Visualization"),
    ),
    Domain(
        "AI & Machine Learning",
        "Supervised, unsupervised, and deep learning models built for real production deployments.",
        ("TensorFlow", "PyTorch", "Scikit-learn", "LLMs"),
    ),
    Domain(
        "Data Analytics",
        "Transform raw data into actionable insights using SQL, Excel, Power BI, and Tableau.",
        ("SQL", "Excel", "Power BI", "Tableau"),
    ),
    Domain(
        "Business Analytics",
        "Drive strategic decisions through data-driven business modelling, KPIs, and BI "
        "dashboards.",
        ("Strategy", "BI Tools", "KPIs", "Reporting"),
    ),
    Domain(
        "Software Testing",
        "Manual and automated testing, test case design, and QA methodologies for production-grade "
        "software.",
        ("Manual Testing", "Selenium", "Postman", "Test Plans"),
    ),
    Domain(
        "Cloud Computing",
        "Deploy, scale, and manage applications on AWS, Azure, and GCP with cloud-native best "
        "practices.",
        ("AWS", "Azure", "GCP", "Terraform"),
    ),
    Domain(
        "MERN Stack",
        "Full-stack web apps with MongoDB, Express, React, and Node.js in a cohesive modern "
        "workflow.",
        ("MongoDB", "Express", "React", "Node.js"),
    ),
    Domain(
        "UI/UX Design and Prototyping",
        "Design intuitive user interfaces and interactive prototypes using Figma and design system "
        "principles.",
        ("Figma", "Prototyping", "Wireframes", "User Research"),
    ),
    Domain(
        "Web Development",
        "Core and advanced web development covering HTML, CSS, JavaScript, and modern frameworks.",
        ("HTML/CSS", "JavaScript", "React", "Responsive"),
    ),
    Domain(
        "IOT",
        "Connect physical devices to the internet with sensor integration, protocols, and cloud "
        "IoT platforms.",
        ("Arduino", "MQTT", "Sensors", "Cloud IoT"),
    ),
    Domain(
        "Embedded Systems",
        "Program microcontrollers, real-time systems, and low-level hardware interfaces for "
        "embedded applications.",
        ("C/C++", "Microcontrollers", "RTOS", "PCB"),
    ),
    Domain(
        "Cybersecurity",
        "Ethical hacking, threat analysis, and secure system design following OWASP and industry "
        "standards.",
        ("Ethical Hacking", "OWASP", "Pen Testing", "SIEM"),
    ),
    Domain(
        "Big Data Analytics",
        "Process and analyse massive datasets using Hadoop, Spark, and distributed computing "
        "frameworks.",
        ("Hadoop", "Spark", "Hive", "Kafka"),
    ),
    Domain(
        "HR - Operations",
        "Streamline HR workflows, talent acquisition, and workforce management with modern HR "
        "tools.",
        ("Talent Acquisition", "HRMS", "Onboarding", "Compliance"),
    ),
    Domain(
        "HR - Marketing",
        "Employer branding, talent marketing strategies, and HR communication for modern "
        "organisations.",
        ("Employer Branding", "Recruitment Mktg", "LinkedIn", "Analytics"),
    ),
    Domain(
        "HR - Finance & Accounting",
        "Payroll management, financial reporting, and accounting fundamentals for HR "
        "professionals.",
        ("Payroll", "Tally", "Budgeting", "Compliance"),
    ),
    Domain(
        "Digital Marketing",
        "SEO, paid advertising, social media strategy, and analytics for impactful digital "
        "campaigns.",
        ("SEO", "Google Ads", "Social Media", "Analytics"),
    ),
    Domain(
        "DevOps",
        "CI/CD pipelines, containerisation, and infrastructure automation for modern software "
        "delivery.",
        ("Docker", "CI/CD", "Kubernetes", "Jenkins"),
    ),
)

DOMAIN_CHOICES = [d.name for d in DOMAIN_CATALOG]

# The catalogue was consolidated — the earlier, narrower list split some
# programmes apart and abbreviated others. Records written before the change
# still carry the old label, so anything that groups or filters by domain (the
# dashboard's domain mix, reports, batch rosters) resolves through this first;
# without it one programme would show up as two separate slices.
LEGACY_DOMAIN_ALIASES = {
    "Python": "Full Stack Python",
    "Java": "Full Stack Java",
    "React": "Web Development",
    "Flutter": "Web Development",
    "Data Science": "Data Science and AI",
    "AI": "AI & Machine Learning",
    "Machine Learning": "AI & Machine Learning",
    "Cyber Security": "Cybersecurity",
    "UI/UX": "UI/UX Design and Prototyping",
    "Testing": "Software Testing",
}


def canonical_domain(name: str | None) -> str | None:
    """Map a stored domain onto its current catalogue name."""
    if not name:
        return None
    return LEGACY_DOMAIN_ALIASES.get(name, name)

DURATION_CHOICES = ["15 Days", "30 Days", "45 Days", "60 Days", "90 Days"]

# How the programme is delivered. Asked on every category except Project,
# which the public form fills in as "Online" behind the scenes.
MODE_CHOICES = ["Online", "Offline"]

# How a registration was paid for. UPI is settled by the applicant before they
# submit, so it arrives with an amount and a reference; cash is settled at the
# desk, so the amount is entered by an HR afterwards and there is no reference.
# Job titles. Distinct from `UserRole`, which is the access level (admin or
# hr) that every permission check reads: these say what a person does, not
# what the software lets them do. A Managing Director may hold admin access
# and a Technical Lead ordinary access without the two ideas interfering.
#
# Stored as the key; the label is what the console shows.
DESIGNATION_LABELS: dict[str, str] = {
    "executive_hr": "Executive HR",
    "business_development_executive": "Business Development Executive",
    "hr": "HR",
    "technical_lead": "Technical Lead",
    "executive_head": "Executive Head",
    "managing_director": "Managing Director",
    "director": "Director",
}
DESIGNATIONS = list(DESIGNATION_LABELS)


PAYMENT_METHOD_UPI = "upi"
PAYMENT_METHOD_CASH = "cash"
PAYMENT_METHODS = [PAYMENT_METHOD_UPI, PAYMENT_METHOD_CASH]

# Revenue the institute earns off-campus, at a college rather than from an
# individual registration. These never pass through applications, students or
# the fee ledger, so each one is entered by hand by the HR who ran it and
# counts toward that HR's own total. Stored as the key; the label is what the
# console shows.
EVENT_TYPE_LABELS: dict[str, str] = {
    "workshop": "Workshop",
    "bootcamp": "Bootcamp",
    "training_program": "Training Program",
    "addon_course": "Add-on Course",
    "industrial_visit": "Industrial Visit",
}
EVENT_TYPES = list(EVENT_TYPE_LABELS)

YEAR_CHOICES = ["1st Year", "2nd Year", "3rd Year", "4th Year", "Final Year"]


def passed_out_year_choices() -> list[str]:
    """Graduation years offered on the public form.

    Computed from the current year rather than written down: a hardcoded list
    starts refusing next year's graduates the moment the calendar turns, and
    nobody notices until an applicant cannot complete the form.

    The range has to cover both people the form serves. Five years forward
    reaches a first-year student who has not graduated yet; twenty-five back
    reaches the working professionals who register for the upskilling
    programmes, and who would otherwise find their own year missing from the
    list with no way to proceed.
    """
    this_year = datetime.now(UTC).year
    return [str(y) for y in range(this_year + 5, this_year - 26, -1)]

APPLICATION_STATUS_PENDING = "pending"
APPLICATION_STATUS_CLAIMED = "claimed"
APPLICATION_STATUS_APPROVED = "approved"
APPLICATION_STATUS_REJECTED = "rejected"
APPLICATION_STATUS_CHOICES = [
    APPLICATION_STATUS_PENDING,
    APPLICATION_STATUS_CLAIMED,
    APPLICATION_STATUS_APPROVED,
    APPLICATION_STATUS_REJECTED,
]

REGISTRATION_ID_PREFIX = "REG"


# ── Institute identity ───────────────────────────────────────────────────
# Every outgoing document and email draws its letterhead, signature and
# reply-to from here. The two supplied templates disagreed with each other —
# one said `dveininnovations.com`, the other `dveininnovation.com`, and they
# signed off with different forms of the same name — so this is the single
# agreed set. A wrong address here means a student who replies to an offer
# letter reaches nobody, which is why it lives in one place rather than being
# retyped into each renderer.
COMPANY_NAME = "DVein Innovations Pvt. Ltd."
COMPANY_EMAIL = "info@dveininnovation.com"
COMPANY_PHONE = "+91 95001 81230"
COMPANY_ADDRESS_LINES = (
    "SSPDL Alpha City, Navalur, Chennai -",
    "600130",
)
COMPANY_FULL_ADDRESS = "3rd Floor, Gamma Block, SSPDL - Alpha City, Navalur, Chennai - 600 130"

# ── Mentors ──────────────────────────────────────────────────────────────
# Who signs a completion certificate, on the empty rule to the right of the
# institute's own signature.
#
# A domain can be taught by more than one mentor, so this is not a lookup —
# the console offers the mentors for the student's domain and an HR picks the
# one who actually taught them. `domains` therefore orders the dropdown; it
# never limits the choice, because which mentor taught a given cohort is not
# something this table can know.
#
# Nobody carries a job title here. Every certificate says "Mentor" under the
# name, so the word lives in MENTOR_TITLE rather than being repeated thirteen
# times and drifting.
#
# Signatures are fixed assets in app/assets/signatures/, not uploads: there
# are a handful of mentors, they change rarely, and keeping them in the image
# means no Storage round trip when a certificate renders. Each file is named
# after the mentor's id below. A missing file is not an error — the name and
# "Mentor" still print, which beats a broken image or a blocked certificate.


MENTOR_TITLE = "Mentor"


@dataclass(frozen=True)
class Mentor:
    id: str
    name: str
    # Filename within app/assets/signatures/.
    signature: str
    domains: tuple[str, ...]

    @property
    def title(self) -> str:
        return MENTOR_TITLE


MENTORS: tuple[Mentor, ...] = (
    Mentor("ahamed-yasik", "Ahamed Yasik Sarvaththudeen M", "ahamed-yasik.png",
           ("Full Stack Python", "DevOps", "Cloud Computing")),
    Mentor("aruna-devi", "Aruna Devi", "aruna-devi.png",
           ("HR - Operations", "HR - Marketing", "HR - Finance & Accounting")),
    Mentor("jayasri", "Jayasri", "jayasri.png",
           ("HR - Operations", "HR - Marketing", "HR - Finance & Accounting")),
    Mentor("koorinivash", "Koorinivash", "koorinivash.png",
           ("Full Stack Python", "IOT")),
    Mentor("mohamed-arsal", "Mohamed Arsal", "mohamed-arsal.png",
           ("Software Testing",)),
    Mentor("muniyappan", "Muniyappan", "muniyappan.png",
           ("Data Analytics", "Data Science and AI")),
    Mentor("navin", "Navin", "navin.png",
           ("Full Stack Java", "MERN Stack", "Web Development")),
    Mentor("prasanth", "Prasanth", "prasanth.png",
           ("Full Stack Python", "Web Development", "UI/UX Design and Prototyping")),
    Mentor("sahana", "Sahana", "sahana.png",
           ("Data Science and AI", "Cybersecurity", "Embedded Systems",
            "Big Data Analytics", "AI & Machine Learning")),
    Mentor("sasikumar", "Sasikumar", "sasikumar.png",
           ("Digital Marketing",)),
    Mentor("selvamani", "Selvamani", "selvamani.png",
           ("Full Stack Java", "MERN Stack")),
    Mentor("sidharraj", "Sidharraj", "sidharraj.png",
           ("Business Analytics", "Data Analytics")),
    Mentor("suriya", "Suriya", "suriya.png",
           ("Data Science and AI", "Cybersecurity", "Embedded Systems",
            "Big Data Analytics", "AI & Machine Learning")),
)


def mentors_for(domain: str | None) -> list[Mentor]:
    """The mentors who teach a domain.

    Only them: offering all thirteen for a Software Testing certificate made
    the one right answer something to hunt for, and the wrong ones just as
    easy to pick by accident.

    Falls back to everyone when the domain is unknown or has nobody assigned
    — an older record may carry a domain name the table has never heard of,
    and an empty dropdown would leave the certificate unsignable.
    """
    if not domain:
        return list(MENTORS)
    teaches = [m for m in MENTORS if domain in m.domains]
    return teaches or list(MENTORS)


def mentor_by_id(mentor_id: str | None) -> Mentor | None:
    if not mentor_id:
        return None
    return next((m for m in MENTORS if m.id == mentor_id), None)


SIGNATORY_NAME = "Sahana Ramamoorthi"
SIGNATORY_TITLE = "Executive Head & AI Engineer"
# The offer letter's own signature block uses the shorter form.
SIGNATORY_TITLE_SHORT = "Executive Head"
