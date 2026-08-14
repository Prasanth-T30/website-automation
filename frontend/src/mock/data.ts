/**
 * Static preview data for screens whose real backend hasn't landed yet
 * (Phases 2–6). Nothing here is persisted or wired to Firestore — it exists
 * purely so the overall design language can be reviewed across every module
 * before each is built for real.
 *
 * The three HR names continue the desktop app's own placeholder cast
 * (Rajan Kumar, Preethi S, Kavita) rather than inventing a new one.
 */

import { addDays, format, subDays } from "date-fns";

const today = new Date();
const iso = (d: Date) => d.toISOString();
const daysFromNow = (n: number) => iso(n >= 0 ? addDays(today, n) : subDays(today, -n));

// ── People ───────────────────────────────────────────────────────────────

export interface MockHr {
  id: string;
  name: string;
  email: string;
}

export const MOCK_HRS: MockHr[] = [
  { id: "hr-1", name: "Rajan Kumar", email: "hr1@dvein.in" },
  { id: "hr-2", name: "Preethi S", email: "hr2@dvein.in" },
  { id: "hr-3", name: "Kavita Iyer", email: "hr3@dvein.in" },
];

export const DOMAINS = [
  "Full Stack Java",
  "Full Stack Python",
  "MERN Stack",
  "Data Science and AI",
  "Cyber Security",
  "Cloud Computing",
  "UI/UX Design and Prototyping",
  "Digital Marketing",
  "Embedded Systems",
  "Software Testing",
] as const;

export const COLLEGES = [
  "PSG College of Technology",
  "Coimbatore Institute of Technology",
  "Kumaraguru College of Technology",
  "Sri Krishna College of Engineering",
  "Karpagam College of Engineering",
  "Bannari Amman Institute of Technology",
];

// ── Batches ──────────────────────────────────────────────────────────────

export type BatchStatus = "upcoming" | "active" | "completed";

export interface MockBatch {
  id: string;
  code: string;
  domain: string;
  start_date: string;
  end_date: string;
  capacity: number;
  status: BatchStatus;
  student_count: number;
  days_left: number | null;
}

export const MOCK_BATCHES: MockBatch[] = [
  {
    id: "batch-1", code: "JAVA-04", domain: "Full Stack Java",
    start_date: daysFromNow(-70), end_date: daysFromNow(2),
    capacity: 25, status: "active", student_count: 22, days_left: 2,
  },
  {
    id: "batch-2", code: "MERN-03", domain: "MERN Stack",
    start_date: daysFromNow(-40), end_date: daysFromNow(20),
    capacity: 20, status: "active", student_count: 18, days_left: 20,
  },
  {
    id: "batch-3", code: "DS-05", domain: "Data Science and AI",
    start_date: daysFromNow(-20), end_date: daysFromNow(70),
    capacity: 20, status: "active", student_count: 14, days_left: 70,
  },
  {
    id: "batch-4", code: "CYB-02", domain: "Cyber Security",
    start_date: daysFromNow(10), end_date: daysFromNow(100),
    capacity: 18, status: "upcoming", student_count: 6, days_left: null,
  },
  {
    id: "batch-5", code: "UIUX-02", domain: "UI/UX Design and Prototyping",
    start_date: daysFromNow(-130), end_date: daysFromNow(-10),
    capacity: 15, status: "completed", student_count: 15, days_left: null,
  },
  {
    id: "batch-6", code: "PY-06", domain: "Full Stack Python",
    start_date: daysFromNow(-15), end_date: daysFromNow(45),
    capacity: 20, status: "active", student_count: 11, days_left: 45,
  },
];

const batchCode = (id: string) => MOCK_BATCHES.find((b) => b.id === id)?.code ?? "—";

// ── Students ─────────────────────────────────────────────────────────────

export type PaymentStatus = "paid" | "pending" | "overdue";
export type StudentStatus = "active" | "completed" | "dropped";
export type PipelineStage =
  | "contacted" | "interested" | "enrolled" | "in_training" | "completed" | "dropped";

export const PIPELINE_STAGES: { key: PipelineStage; label: string }[] = [
  { key: "contacted", label: "Contacted" },
  { key: "interested", label: "Interested" },
  { key: "enrolled", label: "Enrolled" },
  { key: "in_training", label: "In Training" },
  { key: "completed", label: "Completed" },
];

export interface MockStudent {
  id: string;
  student_id: string;
  name: string;
  college_name: string;
  email: string;
  phone: string;
  domain: string;
  batch_id: string | null;
  owner_id: string;
  total_fees: number;
  fees_paid: number;
  payment_status: PaymentStatus;
  status: StudentStatus;
  pipeline_stage: PipelineStage;
  city: string;
  created_at: string;
}

const FIRST = ["Arjun", "Divya", "Karthik", "Meena", "Sanjay", "Priya", "Vignesh", "Anitha",
  "Harish", "Deepika", "Naveen", "Swathi", "Gokul", "Ramya", "Suresh", "Lavanya",
  "Bala", "Nithya", "Arun", "Keerthi", "Manoj", "Shalini", "Vikram", "Pooja"];
const LAST = ["Kumar", "Raj", "Krishnan", "Sundaram", "Pillai", "Nair", "Iyer", "Murugan",
  "Venkatesh", "Rangan", "Balan", "Selvam", "Anand", "Ganesh", "Prasad", "Mohan"];

function makeStudents(): MockStudent[] {
  const rows: MockStudent[] = [];
  let n = 1001;
  const plan: Array<[string | null, PaymentStatus, StudentStatus, number]> = [
    ["batch-1", "paid", "active", -60], ["batch-1", "paid", "active", -58],
    ["batch-1", "pending", "active", -55], ["batch-1", "overdue", "active", -50],
    ["batch-2", "paid", "active", -35], ["batch-2", "pending", "active", -30],
    ["batch-2", "overdue", "active", -28], ["batch-2", "paid", "active", -25],
    ["batch-3", "paid", "active", -18], ["batch-3", "pending", "active", -15],
    ["batch-3", "paid", "active", -12], ["batch-4", "pending", "active", -3],
    ["batch-4", "paid", "active", -2], ["batch-5", "paid", "completed", -125],
    ["batch-5", "paid", "completed", -120], ["batch-5", "paid", "completed", -118],
    ["batch-6", "paid", "active", -14], ["batch-6", "overdue", "active", -10],
    ["batch-6", "pending", "active", -8], [null, "pending", "active", -2],
    [null, "pending", "active", -1], ["batch-3", "paid", "dropped", -16],
  ];
  for (const [batchId, payStatus, status, createdOffset] of plan) {
    const first = FIRST[n % FIRST.length]!;
    const last = LAST[(n * 7) % LAST.length]!;
    const domain = batchId
      ? MOCK_BATCHES.find((b) => b.id === batchId)!.domain
      : DOMAINS[n % DOMAINS.length]!;
    const totalFees = 45000 + (n % 5) * 5000;
    const feesPaid =
      payStatus === "paid" ? totalFees : payStatus === "pending" ? totalFees * 0.5 : totalFees * 0.2;
    const stage: PipelineStage =
      status === "dropped"
        ? "dropped"
        : status === "completed"
          ? "completed"
          : PIPELINE_STAGES[n % 4]!.key; // contacted..in_training for active students
    rows.push({
      id: `student-${n}`,
      student_id: `STU-${n}`,
      name: `${first} ${last}`,
      college_name: COLLEGES[n % COLLEGES.length]!,
      email: `${first.toLowerCase()}.${last.toLowerCase()}${n}@example.com`,
      phone: `9${String(400000000 + n * 137).slice(0, 9)}`,
      domain,
      batch_id: batchId,
      owner_id: MOCK_HRS[n % MOCK_HRS.length]!.id,
      total_fees: totalFees,
      fees_paid: Math.round(feesPaid),
      payment_status: payStatus,
      status,
      pipeline_stage: stage,
      city: "Coimbatore",
      created_at: daysFromNow(createdOffset),
    });
    n += 1;
  }
  return rows;
}

export const MOCK_STUDENTS = makeStudents();

export const studentName = (id: string | null) =>
  MOCK_STUDENTS.find((s) => s.id === id)?.name ?? "Unknown";

export const hrName = (id: string) => MOCK_HRS.find((h) => h.id === id)?.name ?? "Unassigned";

// ── Applications (the shared claim pool) ────────────────────────────────

export type ApplicationStatus = "new" | "claimed" | "converted" | "rejected";

export interface MockApplication {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  college_name: string;
  domain_interest: string;
  city: string;
  status: ApplicationStatus;
  claimed_by: string | null;
  created_at: string;
  message: string;
}

export const MOCK_APPLICATIONS: MockApplication[] = [
  { id: "app-1", full_name: "Yogesh Ramamoorthy", email: "yogesh.r@example.com", phone: "9876500011", college_name: "PSG College of Technology", domain_interest: "Full Stack Java", city: "Coimbatore", status: "new", claimed_by: null, created_at: daysFromNow(0), message: "Saw the ad on Instagram, interested in the next Java batch." },
  { id: "app-2", full_name: "Abinaya Chandrasekar", email: "abinaya.c@example.com", phone: "9876500012", college_name: "Kumaraguru College of Technology", domain_interest: "Data Science and AI", city: "Coimbatore", status: "new", claimed_by: null, created_at: daysFromNow(0), message: "Final year student, want to start after exams." },
  { id: "app-3", full_name: "Praveen Raghavan", email: "praveen.r@example.com", phone: "9876500013", college_name: "Sri Krishna College of Engineering", domain_interest: "Cyber Security", city: "Tiruppur", status: "new", claimed_by: null, created_at: daysFromNow(-1), message: "" },
  { id: "app-4", full_name: "Dhivya Sankar", email: "dhivya.s@example.com", phone: "9876500014", college_name: "Karpagam College of Engineering", domain_interest: "MERN Stack", city: "Coimbatore", status: "claimed", claimed_by: "hr-1", created_at: daysFromNow(-2), message: "Called once, following up tomorrow." },
  { id: "app-5", full_name: "Mukesh Balaji", email: "mukesh.b@example.com", phone: "9876500015", college_name: "Bannari Amman Institute of Technology", domain_interest: "Full Stack Python", city: "Erode", status: "claimed", claimed_by: "hr-2", created_at: daysFromNow(-3), message: "Asked about EMI options." },
  { id: "app-6", full_name: "Sowmya Prakash", email: "sowmya.p@example.com", phone: "9876500016", college_name: "PSG College of Technology", domain_interest: "UI/UX Design and Prototyping", city: "Coimbatore", status: "claimed", claimed_by: "hr-3", created_at: daysFromNow(-4), message: "" },
  { id: "app-7", full_name: "Ashwin Natarajan", email: "ashwin.n@example.com", phone: "9876500017", college_name: "Coimbatore Institute of Technology", domain_interest: "Full Stack Java", city: "Coimbatore", status: "converted", claimed_by: "hr-1", created_at: daysFromNow(-9), message: "Enrolled into JAVA-04." },
  { id: "app-8", full_name: "Revathi Sundar", email: "revathi.s@example.com", phone: "9876500018", college_name: "Kumaraguru College of Technology", domain_interest: "Data Science and AI", city: "Coimbatore", status: "converted", claimed_by: "hr-2", created_at: daysFromNow(-19), message: "" },
  { id: "app-9", full_name: "Gowtham Velusamy", email: "gowtham.v@example.com", phone: "9876500019", college_name: "Sri Krishna College of Engineering", domain_interest: "Cloud Computing", city: "Pollachi", status: "rejected", claimed_by: "hr-3", created_at: daysFromNow(-6), message: "Went with a different institute." },
  { id: "app-10", full_name: "Nandhini Rajkumar", email: "nandhini.r@example.com", phone: "9876500020", college_name: "Karpagam College of Engineering", domain_interest: "Digital Marketing", city: "Coimbatore", status: "new", claimed_by: null, created_at: daysFromNow(0), message: "Wants weekend batch only." },
];

// ── Attendance ───────────────────────────────────────────────────────────

export type AttendanceStatus = "present" | "absent" | "late";

export interface MockAttendance {
  student_id: string;
  batch_id: string;
  date: string;
  status: AttendanceStatus;
}

function makeAttendance(): MockAttendance[] {
  const rows: MockAttendance[] = [];
  const roster = MOCK_STUDENTS.filter((s) => s.batch_id && s.status === "active");
  for (let dayOffset = 6; dayOffset >= 0; dayOffset -= 1) {
    for (const s of roster) {
      const roll = (s.id.charCodeAt(8) + dayOffset) % 10;
      const status: AttendanceStatus = roll < 8 ? "present" : roll === 8 ? "late" : "absent";
      rows.push({ student_id: s.id, batch_id: s.batch_id!, date: daysFromNow(-dayOffset), status });
    }
  }
  return rows;
}

export const MOCK_ATTENDANCE = makeAttendance();

// ── Payments ─────────────────────────────────────────────────────────────

export type PaymentMode = "cash" | "upi" | "bank" | "cheque";

export interface MockTransaction {
  id: string;
  receipt_number: string;
  student_id: string;
  amount: number;
  mode: PaymentMode;
  balance_after: number;
  paid_at: string;
  notes: string;
}

function makeTransactions(): MockTransaction[] {
  const modes: PaymentMode[] = ["cash", "upi", "bank", "cheque"];
  const rows: MockTransaction[] = [];
  let receiptN = 1;
  MOCK_STUDENTS.forEach((s, i) => {
    if (s.fees_paid <= 0) return;
    const installments = s.payment_status === "paid" ? 2 : 1;
    let paid = 0;
    for (let k = 0; k < installments; k += 1) {
      const amount = Math.round(s.fees_paid / installments / 500) * 500;
      paid += amount;
      rows.push({
        id: `tx-${s.id}-${k}`,
        receipt_number: `RCP-2026-${String(receiptN).padStart(4, "0")}`,
        student_id: s.id,
        amount,
        mode: modes[(i + k) % modes.length]!,
        balance_after: Math.max(s.total_fees - paid, 0),
        paid_at: daysFromNow(-Math.max(5, 60 - i * 3) + k * 10),
        notes: k === 0 ? "Registration fee" : "Installment 2",
      });
      receiptN += 1;
    }
  });
  return rows.sort((a, b) => (a.paid_at < b.paid_at ? 1 : -1));
}

export const MOCK_TRANSACTIONS = makeTransactions();

export const paymentsSummary = () => {
  const totalRevenue = MOCK_STUDENTS.reduce((s, x) => s + x.fees_paid, 0);
  const pending = MOCK_STUDENTS.filter((s) => s.payment_status === "pending");
  const overdue = MOCK_STUDENTS.filter((s) => s.payment_status === "overdue");
  return {
    total_revenue: totalRevenue,
    pending_amount: pending.reduce((s, x) => s + (x.total_fees - x.fees_paid), 0),
    overdue_amount: overdue.reduce((s, x) => s + (x.total_fees - x.fees_paid), 0),
    paid_count: MOCK_STUDENTS.filter((s) => s.payment_status === "paid").length,
    pending_count: pending.length,
    overdue_count: overdue.length,
  };
};

// ── Reports & certificates ──────────────────────────────────────────────

export type ReportCategory = "call_letter" | "certificate" | "invoice" | "other";

export interface MockReport {
  id: string;
  title: string;
  category: ReportCategory;
  student_id: string | null;
  original_filename: string;
  file_size_bytes: number;
  uploaded_at: string;
}

export const MOCK_REPORTS: MockReport[] = [
  { id: "rep-1", title: "Full Stack Java Certificate [A+]", category: "certificate", student_id: "student-1017", original_filename: "certificate_java.pdf", file_size_bytes: 245_000, uploaded_at: daysFromNow(-15) },
  { id: "rep-2", title: "UI/UX Design Certificate [A]", category: "certificate", student_id: "student-1015", original_filename: "certificate_uiux.pdf", file_size_bytes: 198_000, uploaded_at: daysFromNow(-11) },
  { id: "rep-3", title: "UI/UX Design Certificate [B+]", category: "certificate", student_id: "student-1016", original_filename: "certificate_uiux2.pdf", file_size_bytes: 201_000, uploaded_at: daysFromNow(-11) },
  { id: "rep-4", title: "Call Letter — JAVA-04 Batch", category: "call_letter", student_id: "student-1001", original_filename: "call_letter_java04.pdf", file_size_bytes: 82_000, uploaded_at: daysFromNow(-58) },
  { id: "rep-5", title: "Fee Invoice — March", category: "invoice", student_id: "student-1005", original_filename: "invoice_march.pdf", file_size_bytes: 64_000, uploaded_at: daysFromNow(-30) },
  { id: "rep-6", title: "Batch Attendance Summary — DS-05", category: "other", student_id: null, original_filename: "attendance_ds05.xlsx", file_size_bytes: 38_000, uploaded_at: daysFromNow(-5) },
];

// ── Notifications (mirrors the tiering rules from the desktop app) ──────

export interface MockNotification {
  id: string;
  type: "danger" | "warning" | "primary";
  title: string;
  desc: string;
  urgency: number;
  created_at: string;
}

export const MOCK_NOTIFICATIONS: MockNotification[] = [
  { id: "n-1", type: "danger", title: "⚡ EXPIRES IN 2 DAYS — JAVA-04", desc: "22 students · Full Stack Java · Ends " + format(addDays(today, 2), "MMM d, yyyy"), urgency: 0, created_at: daysFromNow(0) },
  { id: "n-2", type: "danger", title: "Payment overdue: Sanjay Krishnan", desc: "Balance: ₹27,000 · JAVA-04", urgency: 1, created_at: daysFromNow(0) },
  { id: "n-3", type: "danger", title: "3 students have overdue payments", desc: "Total overdue: ₹68,500", urgency: 1, created_at: daysFromNow(-1) },
  { id: "n-4", type: "warning", title: "⏰ 15-Day Reminder — MERN-03", desc: "Expires in 20 days · 18 students", urgency: 2, created_at: daysFromNow(-1) },
  { id: "n-5", type: "warning", title: "5 students with pending payments", desc: "Total pending: ₹1,32,000", urgency: 3, created_at: daysFromNow(-2) },
  { id: "n-6", type: "primary", title: "New student registered: Nithya Balan", desc: "Enrolled in Data Science and AI", urgency: 4, created_at: daysFromNow(-1) },
  { id: "n-7", type: "primary", title: "New student registered: Manoj Ganesh", desc: "Enrolled in Full Stack Python", urgency: 4, created_at: daysFromNow(-3) },
];

// ── Dashboard aggregates ─────────────────────────────────────────────────

export const dashboardStats = () => ({
  total_students: MOCK_STUDENTS.length,
  active_students: MOCK_STUDENTS.filter((s) => s.status === "active").length,
  completed_students: MOCK_STUDENTS.filter((s) => s.status === "completed").length,
  active_batches: MOCK_BATCHES.filter((b) => b.status === "active").length,
  upcoming_batches: MOCK_BATCHES.filter((b) => b.status === "upcoming").length,
  total_reports: MOCK_REPORTS.length,
  ...paymentsSummary(),
});

export const monthlyRegistrations = [
  { month: "Feb", count: 6 }, { month: "Mar", count: 9 }, { month: "Apr", count: 7 },
  { month: "May", count: 11 }, { month: "Jun", count: 8 }, { month: "Jul", count: 14 },
  { month: "Aug", count: 22 },
];

export const monthlyRevenue = [
  { month: "Feb", amount: 185 }, { month: "Mar", amount: 240 }, { month: "Apr", amount: 198 },
  { month: "May", amount: 312 }, { month: "Jun", amount: 275 }, { month: "Jul", amount: 356 },
  { month: "Aug", amount: 410 },
];

export const domainDistribution = DOMAINS.map((domain) => ({
  domain,
  count: MOCK_STUDENTS.filter((s) => s.domain === domain).length,
})).filter((d) => d.count > 0);

export const batchAttendanceRate = MOCK_BATCHES.filter((b) => b.status === "active").map((b) => {
  const rows = MOCK_ATTENDANCE.filter((a) => a.batch_id === b.id);
  const present = rows.filter((a) => a.status === "present").length;
  return { code: b.code, pct: rows.length ? Math.round((present / rows.length) * 100) : 0 };
});

export const hrPerformance = MOCK_HRS.map((hr) => {
  const claimed = MOCK_APPLICATIONS.filter((a) => a.claimed_by === hr.id);
  const converted = claimed.filter((a) => a.status === "converted");
  const owned = MOCK_STUDENTS.filter((s) => s.owner_id === hr.id);
  return {
    hr,
    claimed: claimed.length,
    converted: converted.length,
    conversionRate: claimed.length ? Math.round((converted.length / claimed.length) * 100) : 0,
    revenue: owned.reduce((s, x) => s + x.fees_paid, 0),
    activeStudents: owned.filter((s) => s.status === "active").length,
  };
});

export { batchCode };
