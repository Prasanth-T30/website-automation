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

  // The roster for a workshop or bootcamp. Separate from students on
  // purpose — an attendee is not an enrolment, and the server keeps them in
  // their own collection so they never reach the Students page.
  attendees: (id) => api.get(`/events/${id}/attendees`),
  importAttendees: (id, file) => {
    const form = new FormData();
    form.append("file", file);
    return api.upload(`/events/${id}/attendees/import`, form);
  },
  removeAttendee: (id, attendeeId) => api.del(`/events/${id}/attendees/${attendeeId}`),
  clearRoster: (id) => api.del(`/events/${id}/attendees`),
  // A blank register in the shape the importer reads. Served by the API
  // rather than built here, so it cannot drift from the parser.
  templateUrl: () => api.url("/events/attendees/template.xlsx"),
};
