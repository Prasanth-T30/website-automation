export const CATEGORY_CHOICES = ["Internship", "Course", "Project"];

// Section title + "Domain" field label adapt to whichever category is picked.
export const CATEGORY_LABELS = {
  Internship: { section: "Internship Information", domainField: "Domain" },
  Course: { section: "Course Information", domainField: "Course Name" },
  Project: { section: "Project Information", domainField: "Project Name" },
};

/**
 * The programme catalogue.
 *
 * The HRM's `/public/choices` endpoint is the authority — it is generated from
 * the same list the console validates submissions against, so a domain added
 * there appears here without a redeploy. This copy is the offline fallback and
 * the source of the summary/stack copy shown on each programme card.
 */
export const DOMAIN_CATALOG = [
  {
    name: "Full Stack Java",
    summary:
      "Build enterprise-grade applications with Java, Spring Boot, REST APIs, and scalable backend systems.",
    stack: ["Java", "Spring Boot", "REST API", "MySQL"],
  },
  {
    name: "Full Stack Python",
    summary: "End-to-end Python development using Django, FastAPI, and modern frontend integration.",
    stack: ["Python", "Django", "FastAPI", "PostgreSQL"],
  },
  {
    name: "Data Science and AI",
    summary:
      "Explore data pipelines, statistical modelling, and AI-driven applications using Python and real datasets.",
    stack: ["Python", "Pandas", "Statistics", "Visualization"],
  },
  {
    name: "AI & Machine Learning",
    summary: "Supervised, unsupervised, and deep learning models built for real production deployments.",
    stack: ["TensorFlow", "PyTorch", "Scikit-learn", "LLMs"],
  },
  {
    name: "Data Analytics",
    summary: "Transform raw data into actionable insights using SQL, Excel, Power BI, and Tableau.",
    stack: ["SQL", "Excel", "Power BI", "Tableau"],
  },
  {
    name: "Business Analytics",
    summary: "Drive strategic decisions through data-driven business modelling, KPIs, and BI dashboards.",
    stack: ["Strategy", "BI Tools", "KPIs", "Reporting"],
  },
  {
    name: "Software Testing",
    summary:
      "Manual and automated testing, test case design, and QA methodologies for production-grade software.",
    stack: ["Manual Testing", "Selenium", "Postman", "Test Plans"],
  },
  {
    name: "Cloud Computing",
    summary: "Deploy, scale, and manage applications on AWS, Azure, and GCP with cloud-native best practices.",
    stack: ["AWS", "Azure", "GCP", "Terraform"],
  },
  {
    name: "MERN Stack",
    summary: "Full-stack web apps with MongoDB, Express, React, and Node.js in a cohesive modern workflow.",
    stack: ["MongoDB", "Express", "React", "Node.js"],
  },
  {
    name: "UI/UX Design and Prototyping",
    summary:
      "Design intuitive user interfaces and interactive prototypes using Figma and design system principles.",
    stack: ["Figma", "Prototyping", "Wireframes", "User Research"],
  },
  {
    name: "Web Development",
    summary: "Core and advanced web development covering HTML, CSS, JavaScript, and modern frameworks.",
    stack: ["HTML/CSS", "JavaScript", "React", "Responsive"],
  },
  {
    name: "IOT",
    summary:
      "Connect physical devices to the internet with sensor integration, protocols, and cloud IoT platforms.",
    stack: ["Arduino", "MQTT", "Sensors", "Cloud IoT"],
  },
  {
    name: "Embedded Systems",
    summary:
      "Program microcontrollers, real-time systems, and low-level hardware interfaces for embedded applications.",
    stack: ["C/C++", "Microcontrollers", "RTOS", "PCB"],
  },
  {
    name: "Cybersecurity",
    summary:
      "Ethical hacking, threat analysis, and secure system design following OWASP and industry standards.",
    stack: ["Ethical Hacking", "OWASP", "Pen Testing", "SIEM"],
  },
  {
    name: "Big Data Analytics",
    summary: "Process and analyse massive datasets using Hadoop, Spark, and distributed computing frameworks.",
    stack: ["Hadoop", "Spark", "Hive", "Kafka"],
  },
  {
    name: "HR - Operations",
    summary: "Streamline HR workflows, talent acquisition, and workforce management with modern HR tools.",
    stack: ["Talent Acquisition", "HRMS", "Onboarding", "Compliance"],
  },
  {
    name: "HR - Marketing",
    summary: "Employer branding, talent marketing strategies, and HR communication for modern organisations.",
    stack: ["Employer Branding", "Recruitment Mktg", "LinkedIn", "Analytics"],
  },
  {
    name: "HR - Finance & Accounting",
    summary: "Payroll management, financial reporting, and accounting fundamentals for HR professionals.",
    stack: ["Payroll", "Tally", "Budgeting", "Compliance"],
  },
  {
    name: "Digital Marketing",
    summary: "SEO, paid advertising, social media strategy, and analytics for impactful digital campaigns.",
    stack: ["SEO", "Google Ads", "Social Media", "Analytics"],
  },
  {
    name: "DevOps",
    summary: "CI/CD pipelines, containerisation, and infrastructure automation for modern software delivery.",
    stack: ["Docker", "CI/CD", "Kubernetes", "Jenkins"],
  },
];

export const DOMAIN_CHOICES = DOMAIN_CATALOG.map((d) => d.name);

export const DURATION_CHOICES = ["15 Days", "30 Days", "45 Days", "60 Days", "90 Days"];

export const MODE_CHOICES = ["Online", "Offline"];

export const STATUS_COLORS = {
  Pending: "bg-amber-100 text-amber-700 border-amber-200",
  Approved: "bg-emerald-100 text-emerald-700 border-emerald-200",
  Rejected: "bg-red-100 text-red-700 border-red-200",
};

export const YEAR_CHOICES = ["1st Year", "2nd Year", "3rd Year", "4th Year", "Final Year"];

/**
 * Years offered for "Year of Passing Out".
 *
 * Built from the clock rather than typed out, so the list cannot quietly go
 * stale — a hardcoded range stops offering next year's graduates the moment
 * the calendar turns, and the first person to notice is an applicant who
 * cannot finish the form.
 *
 * Runs forward far enough for a first-year student who has not graduated
 * yet, and back far enough for the working professionals who register for
 * the upskilling programmes.
 */
export const passedOutYearChoices = () => {
  const now = new Date().getFullYear();
  const years = [];
  for (let y = now + 5; y >= now - 25; y -= 1) years.push(String(y));
  return years;
};

export const TITLE_CHOICES = ["Mr.", "Ms.", "Mrs.", "Dr."];
