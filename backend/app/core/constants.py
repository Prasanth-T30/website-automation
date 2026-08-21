"""Choice lists shared by the registration form and its validation.

Verbatim from Dvein's live programme catalogue — these are the institute's
actual programme categories and domains, not an invented list.
"""

from __future__ import annotations

from dataclasses import dataclass

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

YEAR_CHOICES = ["1st Year", "2nd Year", "3rd Year", "4th Year", "Final Year"]

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

SIGNATORY_NAME = "Sahana Ramamoorthi"
SIGNATORY_TITLE = "Executive Head & AI Engineer"
# The offer letter's own signature block uses the shorter form.
SIGNATORY_TITLE_SHORT = "Executive Head"
