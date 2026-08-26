/**
 * Alert shapes. Derived by the backend on every read — nothing is stored.
 * JSDoc typedefs only, no runtime code.
 *
 * @typedef {"danger" | "warning" | "primary"} NotificationType
 *
 * @typedef {object} Notification
 * @property {string} id
 * @property {NotificationType} type
 * @property {string} title
 * @property {string} description
 * @property {number} urgency  Higher sorts first.
 * @property {string | null} created_at
 * @property {string | null} link  Console path this alert refers to.
 */

export {};
