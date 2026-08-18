/**
 * Admin-only reporting shapes. JSDoc typedefs only — no runtime code.
 *
 * Only the administrator can read this: it exposes every HR's claim count and
 * attributed revenue, which no HR may see for another.
 *
 * @typedef {object} HrPerformance
 * @property {string} id
 * @property {string} full_name
 * @property {string} email
 * @property {number} claimed_count
 * @property {number} converted_count
 * @property {number} conversion_rate  0–1, not a percentage.
 * @property {number} active_students
 * @property {number} revenue_this_month
 * @property {number} revenue_all_time
 */

export {};
