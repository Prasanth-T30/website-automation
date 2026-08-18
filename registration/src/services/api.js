import axios from "axios";

import { API_BASE_URL } from "../config/config";

/**
 * Public, unauthenticated client.
 *
 * The admin-token interceptor and the 401 redirect that used to live here
 * belonged to the old combined app, which served the admin panel from this
 * same bundle. Staff now sign in to the HRM console instead, so this site
 * never holds a credential — anything that arrives here came from a stranger
 * on the internet, and the backend treats it that way (rate limited, written
 * to `applications`, never trusted until an HR claims it).
 */
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

export default api;
