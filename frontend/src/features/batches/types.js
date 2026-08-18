/**
 * Batch/cohort shapes. JSDoc typedefs only — this file exports no runtime code.
 *
 * @typedef {"upcoming" | "active" | "completed"} BatchStatus
 *
 * @typedef {object} Batch
 * @property {string} id
 * @property {string} code
 * @property {string} domain
 * @property {string} start_date
 * @property {string} end_date
 * @property {number} capacity
 * @property {BatchStatus} status
 * @property {string | null} notes
 * @property {string | null} created_by_id
 * @property {string | null} created_at
 * @property {number} student_count  Computed per read, never stored.
 * @property {number | null} days_left  Only set while the batch is active.
 * @property {string | null} created_by_name  The HR who set the batch up —
 *   shown on every card, since batches are shared across the whole team.
 * @property {boolean} can_edit  Creator or admin. The API enforces this too;
 *   it drives the UI so other HRs see a read-only card rather than controls
 *   that fail on click.
 *
 * @typedef {object} BatchCreateInput
 * @property {string} code
 * @property {string} domain
 * @property {string} start_date
 * @property {string} end_date
 * @property {number} capacity
 * @property {string | null} [notes]
 *
 * @typedef {object} BatchUpdateInput
 * @property {string} [domain]
 * @property {string} [start_date]
 * @property {string} [end_date]
 * @property {number} [capacity]
 * @property {BatchStatus} [status]
 * @property {string | null} [notes]
 */

export {};
