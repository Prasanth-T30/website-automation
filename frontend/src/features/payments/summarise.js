import { isOverdue } from "@/features/students/overdue";

/**
 * What a student still owes. Over-payment is settled, not credit — a negative
 * balance would otherwise subtract from the institute's pending total and
 * make it read lower than it really is.
 *
 * @param {{ total_fees: number, fees_paid: number }} student
 * @returns {number}
 */
export const balanceOf = (student) =>
  student ? Math.max(0, student.total_fees - student.fees_paid) : 0;

/**
 * Collapse the transaction ledger into one row per student.
 *
 * Finance answers "who owes what", which is a question about people. A raw
 * ledger repeats a name once per installment, and the fee columns beside each
 * of those rows repeat the same student-level total — so three payments read
 * as three separate debts. The individual transactions belong in that
 * person's own history, not on the summary.
 *
 * Extracted from the page so it can be tested without rendering: this is the
 * arithmetic the whole Finance screen and its exports rest on.
 *
 * @param {Array} students
 * @param {Array} transactions
 * @returns {Array} one entry per student, largest debt first
 */
export function summariseByStudent(students = [], transactions = []) {
  const byStudent = new Map();
  for (const t of transactions) {
    if (!byStudent.has(t.student_id)) byStudent.set(t.student_id, []);
    byStudent.get(t.student_id).push(t);
  }

  return students
    .map((student) => {
      const payments = byStudent.get(student.id) ?? [];
      const latest = payments.reduce(
        (newest, t) =>
          !newest || (t.created_at && t.created_at > newest.created_at) ? t : newest,
        null,
      );
      return {
        student,
        payments,
        collected: payments.reduce((sum, t) => sum + t.amount, 0),
        balance: balanceOf(student),
        lastPaidAt: latest?.created_at ?? null,
        methods: new Set(payments.map((t) => t.method ?? "other")),
      };
    })
    .sort((a, b) => b.balance - a.balance || a.student.name.localeCompare(b.student.name));
}

/**
 * Narrow the summary to what the filter bar is asking for.
 *
 * A payment method belongs to a transaction, so at student level it can only
 * mean "has ever paid this way" — which is what someone reconciling a cash
 * book is looking for.
 */
export function filterSummary(rows, { college, feeStatus, method, query } = {}) {
  const needle = (query ?? "").trim().toLowerCase();
  return rows.filter((r) => {
    if (college && college !== "all" && r.student.college !== college) return false;
    if (feeStatus === "paid" && r.balance > 0) return false;
    if (feeStatus === "pending" && r.balance <= 0) return false;
    if (method && method !== "all" && !r.methods.has(method)) return false;
    if (!needle) return true;
    return (
      r.student.name.toLowerCase().includes(needle) ||
      r.payments.some((t) => t.receipt_number.toLowerCase().includes(needle))
    );
  });
}

/**
 * The four tiles above the table.
 *
 * Revenue is summed from the ledger rather than from `fees_paid`, because the
 * ledger is what receipts were issued against; the two must not be able to
 * disagree on screen.
 */
export function financeTotals(rows, batchesById = new Map()) {
  const unpaid = rows.filter((r) => r.balance > 0);
  const overdue = unpaid.filter((r) => isOverdue(r.student, batchesById));
  const pending = unpaid.filter((r) => !isOverdue(r.student, batchesById));
  return {
    totalRevenue: rows.reduce((sum, r) => sum + r.collected, 0),
    pendingAmount: pending.reduce((sum, r) => sum + r.balance, 0),
    overdueAmount: overdue.reduce((sum, r) => sum + r.balance, 0),
    paidCount: rows.filter((r) => r.balance <= 0).length,
  };
}
