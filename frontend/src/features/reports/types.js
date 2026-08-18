/**
 * Uploaded document shapes. JSDoc typedefs only — no runtime code.
 *
 * @typedef {"certificate" | "call_letter" | "invoice" | "other"} ReportCategory
 *
 * @typedef {object} Report
 * @property {string} id
 * @property {string} title
 * @property {ReportCategory} category
 * @property {string | null} student_id  Null for institute-wide files.
 * @property {string} original_filename
 * @property {string} content_type
 * @property {number} file_size_bytes
 * @property {string} uploaded_by_id
 * @property {string | null} created_at
 */

export {};
