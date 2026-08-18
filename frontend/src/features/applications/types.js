/**
 * Registration/application shapes. JSDoc typedefs only — no runtime code.
 *
 * @typedef {"pending" | "claimed" | "approved" | "rejected"} ApplicationStatus
 *
 * @typedef {object} Application
 * @property {string} id
 * @property {string} registration_id
 * @property {string | null} title
 * @property {string} name
 * @property {string} email
 * @property {string} phone
 * @property {string} college
 * @property {string} place
 * @property {string | null} department
 * @property {string | null} year
 * @property {"student" | "professional"} applicant_type
 * @property {"Internship" | "Course" | "Project"} category
 * @property {string} domain
 * @property {string} duration
 * @property {string} start_date
 * @property {string} end_date
 * @property {number} amount
 * @property {string} transaction_id
 * @property {string | null} payment_screenshot
 * @property {ApplicationStatus} status
 * @property {string | null} owner_id  Null until an HR claims it.
 * @property {string | null} claimed_at
 * @property {string | null} approved_at
 * @property {string | null} converted_student_id
 * @property {string | null} rejection_reason
 * @property {string | null} created_at
 *
 * @typedef {object} Programme
 * @property {string} name
 * @property {string} summary
 * @property {string[]} stack
 *
 * @typedef {object} Choices
 * @property {string[]} titles
 * @property {string[]} categories
 * @property {string[]} domains
 * @property {string[]} durations
 * @property {string[]} years
 * @property {Programme[]} [programmes]  Domains with their blurb and stack.
 */

export {};
