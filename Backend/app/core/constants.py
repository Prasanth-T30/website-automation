"""Static enumerations and choice lists shared across the app."""

CATEGORY_CHOICES = ["Internship", "Course", "Project"]

# Approval emails (with the PDF offer/completion letter) are only sent for these
# categories. "Project" registrations are approved/rejected in the admin panel
# like any other, but no email or PDF is generated for them.
EMAIL_ENABLED_CATEGORIES = {"Internship", "Course"}

DOMAIN_CHOICES = [
    "Web Development",
    "Python",
    "Java",
    "Data Science",
    "AI",
    "Machine Learning",
    "Cyber Security",
    "React",
    "MERN Stack",
    "Flutter",
    "UI/UX",
    "Testing",
]

DURATION_CHOICES = ["15 Days", "30 Days", "45 Days", "60 Days", "90 Days"]

STATUS_PENDING = "Pending"
STATUS_APPROVED = "Approved"
STATUS_REJECTED = "Rejected"
STATUS_CHOICES = [STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED]

REGISTRATION_ID_PREFIX = "REG"
