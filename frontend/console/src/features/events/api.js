import { api } from "@/lib/api";

/**
 * Off-campus revenue events — workshops, bootcamps, training programmes,
 * add-on courses and industrial visits.
 *
 * Every one of these is scoped to the signed-in HR by the server. There is
 * deliberately no "all events" call to reach for: an event is private to the
 * person who recorded it, and the team-wide picture exists only as totals on
 * the admin performance report.
 */
export const eventsApi = {
  list: (params) => api.get("/events", params),
  summary: () => api.get("/events/summary"),
  types: () => api.get("/events/types"),
  create: (data) => api.post("/events", data),
  update: (id, data) => api.patch(`/events/${id}`, data),
  remove: (id) => api.del(`/events/${id}`),
};
