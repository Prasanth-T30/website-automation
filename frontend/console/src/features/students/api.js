import { api } from "@/lib/api";
export const studentsApi = {
  list: (params) => api.get("/students", params),
  create: (data) => api.post("/students", data),
  get: (id) => api.get(`/students/${id}`),
  update: (id, data) => api.patch(`/students/${id}`, data),
  /** Admin only: delete a student and everything filed against them. */
  remove: (id) => api.del(`/students/${id}`),
  /** Admin only: move a student to a different HR. */
  reassign: (id, owner_id) => api.post(`/students/${id}/reassign`, { owner_id }),

  /** Students whose certificate is due, or falls due within `within_days`. */
  certificateCandidates: (params) => api.get("/students/certificate/candidates", params),
  /** The certificate's current field values plus the covering email. */
  certificateDraft: (id) => api.get(`/students/${id}/certificate/draft`),
  /** The certificate as a PDF blob, with the HR's edits applied. Nothing is sent. */
  certificatePreview: (id, fields) =>
    api.postBlob(`/students/${id}/certificate/preview`, { fields }),
  /** Generates the certificate, emails it, and files it under Documents. */
  issueCertificate: (id, data = {}) => api.post(`/students/${id}/certificate`, data),
  /** Preview only — downloads the PDF without emailing or filing it. */
  certificateUrl: (id) => api.url(`/students/${id}/certificate`),

  /** Students who may be sent an offer letter: anyone who has paid. */
  offerCandidates: () => api.get("/students/offer-letter/candidates"),
  /** The letter's current field values plus the covering email, for editing. */
  offerLetterDraft: (id) => api.get(`/students/${id}/offer-letter/draft`),
  /** The letter as a PDF blob, with the HR's edits applied. Nothing is sent. */
  offerLetterPreview: (id, fields) =>
    api.postBlob(`/students/${id}/offer-letter/preview`, { fields }),
  /** Generates the offer letter, emails it, and files it under Documents. */
  issueOfferLetter: (id, data = {}) => api.post(`/students/${id}/offer-letter`, data),
  /** Preview only — renders the letter without emailing or filing it. */
  offerLetterUrl: (id) => api.url(`/students/${id}/offer-letter`),
};
