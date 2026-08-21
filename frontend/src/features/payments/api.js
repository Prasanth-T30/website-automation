import { api } from "@/lib/api";
export const paymentsApi = {
  list: (params) => api.get("/payments", params),
  record: (data) => api.post("/payments/record", data),
  receiptUrl: (id) => api.url(`/payments/${id}/receipt`),

  /**
   * Download URL for the ledger, carrying the screen's current filters so the
   * file matches what is on display. Empty values are omitted rather than sent
   * as `method=all`, which the API would read as a real method name.
   *
   * @param {"xlsx" | "pdf"} format
   * @param {{ mine?: boolean, method?: string, college?: string, q?: string,
   *           fee_status?: "all" | "paid" | "pending" }} [filters]
   */
  exportUrl: (format, filters = {}) => {
    const params = {};
    if (filters.mine) params.mine = "true";
    if (filters.method && filters.method !== "all") params.method = filters.method;
    if (filters.college && filters.college !== "all") params.college = filters.college;
    if (filters.q?.trim()) params.q = filters.q.trim();
    if (filters.fee_status && filters.fee_status !== "all") {
      params.fee_status = filters.fee_status;
    }
    const qs = new URLSearchParams(params).toString();
    return api.url(`/payments/export.${format}${qs ? `?${qs}` : ""}`);
  },
};
