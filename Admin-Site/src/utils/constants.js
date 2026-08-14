export const CATEGORY_CHOICES = ["Internship", "Course", "Project"];

// Mirrors the backend's EMAIL_ENABLED_CATEGORIES — Project registrations get
// approved/rejected like any other, but no approval email/PDF is sent for them.
export const EMAIL_ENABLED_CATEGORIES = ["Internship", "Course"];

export const CATEGORY_COLORS = {
  Internship: "bg-primary-100 text-primary-700 border-primary-200",
  Course: "bg-purple-100 text-purple-700 border-purple-200",
  Project: "bg-orange-100 text-orange-700 border-orange-200",
};

export const DOMAIN_CHOICES = [
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
];

export const DURATION_CHOICES = ["15 Days", "30 Days", "45 Days", "60 Days", "90 Days"];

export const STATUS_COLORS = {
  Pending: "bg-amber-100 text-amber-700 border-amber-200",
  Approved: "bg-emerald-100 text-emerald-700 border-emerald-200",
  Rejected: "bg-red-100 text-red-700 border-red-200",
};

export const YEAR_CHOICES = ["1st Year", "2nd Year", "3rd Year", "4th Year", "Final Year"];

export const TITLE_CHOICES = ["Mr.", "Ms.", "Mrs.", "Dr."];
