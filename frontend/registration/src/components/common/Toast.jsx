import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

const Toast = () => (
  <ToastContainer
    position="top-right"
    autoClose={3500}
    hideProgressBar={false}
    newestOnTop
    closeOnClick
    pauseOnHover
    theme="light"
  />
);

export default Toast;
