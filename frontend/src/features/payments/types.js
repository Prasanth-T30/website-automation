/**
 * Payment shapes. JSDoc typedefs only — no runtime code.
 *
 * @typedef {"cash" | "upi" | "bank_transfer" | "card" | "other"} PaymentMethod
 *
 * @typedef {object} PaymentTransaction
 * @property {string} id
 * @property {string} student_id
 * @property {string} owner_id
 * @property {string} receipt_number  Sequential, assigned by the backend.
 * @property {number} amount
 * @property {PaymentMethod | null} method
 * @property {string | null} notes
 * @property {string} recorded_by_id
 * @property {string | null} created_at
 *
 * @typedef {object} PaymentRecordInput
 * @property {string} student_id
 * @property {number} amount
 * @property {PaymentMethod} [method]
 * @property {string} [notes]
 */

export {};
