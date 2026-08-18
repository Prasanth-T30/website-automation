/**
 * A balance is "overdue" once its batch has been marked completed with
 * money still owed — there's no due-date field to check against, so the
 * programme actually finishing is the derivation, matching the backend's
 * notification engine (app/services/notifications.py). `payment_status`
 * only ever stores "paid" or "pending" (see StudentRepository.update), so
 * this must be computed live rather than trusted from the stored field.
 */
export function isOverdue(student, batchesById) {
  const balance = student.total_fees - student.fees_paid;
  if (balance <= 0 || !student.batch_id) return false;
  return batchesById.get(student.batch_id)?.status === "completed";
}
