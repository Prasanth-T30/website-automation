/**
 * Student shapes, as the API returns them.
 *
 * These are JSDoc typedefs rather than runtime code — the file exports nothing.
 * Editors still read them for autocomplete and hover docs, so the domain model
 * stays documented in one place now that the project is plain JavaScript.
 *
 * @typedef {"paid" | "pending" | "overdue"} PaymentStatus
 * @typedef {"active" | "completed" | "dropped"} StudentStatus
 *
 * @typedef {object} Student
 * @property {string} id
 * @property {string} application_id
 * @property {string} owner_id  HR who claimed the application this came from.
 * @property {string} name
 * @property {string} email
 * @property {string} phone
 * @property {string} college
 * @property {string} place
 * @property {string} category
 * @property {string} domain
 * @property {string} duration
 * @property {string | null} batch_id  Null until an HR assigns a cohort.
 * @property {number} total_fees
 * @property {number} fees_paid
 * @property {PaymentStatus} payment_status
 * @property {StudentStatus} status
 * @property {string | null} created_at
 *
 * @typedef {object} StudentUpdateInput
 * @property {string | null} [batch_id]
 * @property {StudentStatus} [status]
 * @property {PaymentStatus} [payment_status]
 * @property {number} [fees_paid]
 * @property {number} [total_fees]
 */

export {};
