import api from "./api";

/**
 * Submit a registration to the HRM.
 *
 * Posts to the HRM's public endpoint, which validates the payload, stores the
 * payment screenshot, and creates an `application` in the claim queue for an
 * HR to pick up. The response is the created application itself — the old
 * backend wrapped every payload in `{ data: ... }`; the HRM returns it directly.
 */
export const submitRegistration = async (formData) => {
  const { data } = await api.post("/public/applications", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

/**
 * Titles, categories, domains, durations and years, straight from the HRM's
 * own constants. Fetched rather than hardcoded so the programme catalogue can
 * never drift between this form and the console that receives its output.
 */
export const getChoices = async () => {
  const { data } = await api.get("/public/choices");
  return data;
};
