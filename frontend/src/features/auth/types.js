/**
 * Auth shapes. JSDoc typedefs only — this file exports no runtime code.
 *
 * @typedef {"admin" | "hr"} UserRole
 *
 * @typedef {object} User
 * @property {string} id  Firestore document ID — an opaque string, not a
 *   numeric primary key.
 * @property {string} email
 * @property {string} full_name
 * @property {UserRole} role
 * @property {boolean} is_active
 * @property {string | null} phone
 * @property {boolean} must_change_password
 * @property {string | null} last_login_at
 * @property {string} created_at
 *
 * @typedef {object} SessionResponse
 * @property {User} user
 */

export {};
