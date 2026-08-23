import { BrowserRouter } from "react-router-dom";

import Toast from "./components/common/Toast";
import AppRoutes from "./routes/AppRoutes";

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
      <Toast />
    </BrowserRouter>
  );
}

export default App;
