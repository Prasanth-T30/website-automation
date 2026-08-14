import { Route, Routes } from "react-router-dom";

import NotFound from "../pages/error/NotFound";
import Registration from "../pages/home/Registration";
import Success from "../pages/home/Success";

// This app only ever serves the public registration flow — no landing page,
// visitors land straight on the registration form. The Admin experience
// lives in a completely separate app/URL (see Admin-Site).
const AppRoutes = () => (
  <Routes>
    <Route path="/" element={<Registration />} />
    <Route path="/register" element={<Registration />} />
    <Route path="/success" element={<Success />} />
    <Route path="*" element={<NotFound />} />
  </Routes>
);

export default AppRoutes;
