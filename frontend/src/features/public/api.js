import { api } from "@/lib/api";
export const publicApi = {
  choices: () => api.get("/public/choices"),
  submit: (values, screenshot) => {
    const form = new FormData();
    for (const [key, value] of Object.entries(values)) {
      if (value !== "" && value !== undefined && value !== null) {
        form.append(key, String(value));
      }
    }
    form.append("payment_screenshot", screenshot);
    return api.upload("/public/applications", form);
  },
};
