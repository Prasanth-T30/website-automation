/**
 * Attendance shapes. JSDoc typedefs only — no runtime code.
 *
 * @typedef {"present" | "absent" | "late"} AttendanceStatus
 *
 * @typedef {object} AttendanceRecord
 * @property {string} id
 * @property {string} student_id
 * @property {string | null} batch_id
 * @property {string} date  ISO date (YYYY-MM-DD), not a timestamp.
 * @property {AttendanceStatus} status
 * @property {string | null} notes
 * @property {string | null} created_at
 *
 * @typedef {object} AttendanceMarkInput
 * @property {string} student_id
 * @property {string | null} [batch_id]
 * @property {string} date
 * @property {AttendanceStatus} status
 * @property {string | null} [notes]
 */

export {};
