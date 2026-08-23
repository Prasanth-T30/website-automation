import { describe, expect, it } from "vitest";

import { balanceOf, filterSummary, financeTotals, summariseByStudent } from "./summarise";

const student = (over = {}) => ({
  id: "s1",
  name: "Rohan Sundaram",
  college: "PSG College of Technology",
  total_fees: 45000,
  fees_paid: 16000,
  batch_id: null,
  ...over,
});

const payment = (over = {}) => ({
  id: "p1",
  student_id: "s1",
  receipt_number: "RCPT00001",
  amount: 1000,
  method: "cash",
  created_at: "2026-08-01T10:00:00Z",
  ...over,
});

describe("balanceOf", () => {
  it("reports what is still owed", () => {
    expect(balanceOf(student())).toBe(29000);
  });

  it("treats over-payment as settled rather than credit", () => {
    // A negative balance would subtract from the institute's pending total
    // and make it read lower than it really is.
    expect(balanceOf(student({ total_fees: 1000, fees_paid: 5000 }))).toBe(0);
  });

  it("survives a missing student", () => {
    expect(balanceOf(undefined)).toBe(0);
  });
});

describe("summariseByStudent", () => {
  it("returns one row per student, not one per transaction", () => {
    // The bug this replaced: three installments rendered as three rows, each
    // repeating the same student-level total, so one debt looked like three.
    const rows = summariseByStudent(
      [student()],
      [
        payment({ id: "a", amount: 10000 }),
        payment({ id: "b", amount: 1000 }),
        payment({ id: "c", amount: 5000 }),
      ],
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].payments).toHaveLength(3);
    expect(rows[0].collected).toBe(16000);
  });

  it("includes a student who has never paid", () => {
    // These are the people who owe everything — dropping them would hide the
    // largest debts on the page.
    const rows = summariseByStudent([student({ fees_paid: 0 })], []);
    expect(rows).toHaveLength(1);
    expect(rows[0].collected).toBe(0);
    expect(rows[0].balance).toBe(45000);
  });

  it("puts the largest debt first", () => {
    const rows = summariseByStudent(
      [
        student({ id: "a", name: "Settled", total_fees: 100, fees_paid: 100 }),
        student({ id: "b", name: "Owes A Lot", total_fees: 90000, fees_paid: 0 }),
      ],
      [],
    );
    expect(rows.map((r) => r.student.id)).toEqual(["b", "a"]);
  });

  it("breaks ties by name so the order is stable between renders", () => {
    const rows = summariseByStudent(
      [
        student({ id: "z", name: "Zara", total_fees: 100, fees_paid: 100 }),
        student({ id: "a", name: "Aarav", total_fees: 100, fees_paid: 100 }),
      ],
      [],
    );
    expect(rows.map((r) => r.student.name)).toEqual(["Aarav", "Zara"]);
  });

  it("reports the most recent payment date", () => {
    const rows = summariseByStudent(
      [student()],
      [
        payment({ id: "old", created_at: "2026-01-01T00:00:00Z" }),
        payment({ id: "new", created_at: "2026-09-01T00:00:00Z" }),
      ],
    );
    expect(rows[0].lastPaidAt).toBe("2026-09-01T00:00:00Z");
  });

  it("ignores transactions belonging to somebody else", () => {
    const rows = summariseByStudent([student()], [payment({ student_id: "someone-else" })]);
    expect(rows[0].collected).toBe(0);
  });
});

describe("filterSummary", () => {
  const rows = summariseByStudent(
    [
      student({ id: "owing", name: "Still Owes", total_fees: 5000, fees_paid: 1000 }),
      student({
        id: "settled",
        name: "All Paid",
        college: "Kongu Engineering College",
        total_fees: 2000,
        fees_paid: 2000,
      }),
    ],
    [
      payment({ id: "x", student_id: "owing", amount: 1000, method: "cash" }),
      payment({
        id: "y",
        student_id: "settled",
        amount: 2000,
        method: "upi",
        receipt_number: "RCPT00099",
      }),
    ],
  );

  it("narrows to students who still owe", () => {
    const out = filterSummary(rows, { feeStatus: "pending" });
    expect(out.map((r) => r.student.id)).toEqual(["owing"]);
  });

  it("narrows to students who are settled", () => {
    const out = filterSummary(rows, { feeStatus: "paid" });
    expect(out.map((r) => r.student.id)).toEqual(["settled"]);
  });

  it("reads a payment method as 'has ever paid this way'", () => {
    // A method belongs to a transaction, so at student level it cannot mean
    // anything else.
    expect(filterSummary(rows, { method: "upi" }).map((r) => r.student.id)).toEqual([
      "settled",
    ]);
  });

  it("filters by college", () => {
    const out = filterSummary(rows, { college: "Kongu Engineering College" });
    expect(out.map((r) => r.student.id)).toEqual(["settled"]);
  });

  it("searches names and receipt numbers alike", () => {
    expect(filterSummary(rows, { query: "still owes" })).toHaveLength(1);
    expect(filterSummary(rows, { query: "RCPT00099" })).toHaveLength(1);
  });

  it("is case-insensitive and ignores stray whitespace", () => {
    expect(filterSummary(rows, { query: "  STILL owes " })).toHaveLength(1);
  });

  it("returns everything when nothing is selected", () => {
    expect(filterSummary(rows, {})).toHaveLength(2);
    expect(filterSummary(rows)).toHaveLength(2);
  });
});

describe("financeTotals", () => {
  it("sums revenue from the ledger, not from fees_paid", () => {
    // The ledger is what receipts were issued against; if the two ever
    // disagree the receipts are the truth.
    const rows = summariseByStudent(
      [student({ fees_paid: 16000 })],
      [payment({ amount: 10000 }), payment({ id: "b", amount: 6000 })],
    );
    expect(financeTotals(rows).totalRevenue).toBe(16000);
  });

  it("separates pending from overdue by whether the batch has finished", () => {
    const batches = new Map([
      ["done", { id: "done", status: "completed" }],
      ["running", { id: "running", status: "active" }],
    ]);
    const rows = summariseByStudent(
      [
        student({ id: "late", total_fees: 5000, fees_paid: 0, batch_id: "done" }),
        student({ id: "current", total_fees: 3000, fees_paid: 0, batch_id: "running" }),
      ],
      [],
    );
    const totals = financeTotals(rows, batches);
    expect(totals.overdueAmount).toBe(5000);
    expect(totals.pendingAmount).toBe(3000);
  });

  it("counts the fully paid", () => {
    const rows = summariseByStudent(
      [
        student({ id: "a", total_fees: 100, fees_paid: 100 }),
        student({ id: "b", total_fees: 100, fees_paid: 50 }),
      ],
      [],
    );
    expect(financeTotals(rows).paidCount).toBe(1);
  });

  it("is all zeroes on an empty institute rather than NaN", () => {
    expect(financeTotals([])).toEqual({
      totalRevenue: 0,
      pendingAmount: 0,
      overdueAmount: 0,
      paidCount: 0,
    });
  });
});
