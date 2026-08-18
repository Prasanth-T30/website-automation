/**
 * Institute settings shapes. JSDoc typedefs only — no runtime code.
 *
 * @typedef {object} InstituteSettings
 * @property {string} name
 * @property {string} email
 * @property {string} phone
 * @property {string} address
 * @property {string} website
 * @property {string} gst
 * @property {string | null} updated_at
 *
 * An update sends only the fields that changed; `updated_at` is server-set.
 * @typedef {Partial<Omit<InstituteSettings, "updated_at">>} InstituteSettingsUpdate
 */

export {};
