import { FiCheckCircle } from "react-icons/fi";
import { Link, useLocation } from "react-router-dom";

import Footer from "../../components/layout/Footer";
import Navbar from "../../components/layout/Navbar";

const Success = () => {
  const { state } = useLocation();
  const registration = state?.registration;

  return (
    <div className="dv-shell flex min-h-screen flex-col">
      <Navbar />
      <main className="mx-auto flex w-full max-w-lg flex-1 flex-col items-center justify-center px-4 py-16 text-center">
        <div className="glass-card w-full p-8">
          <FiCheckCircle className="mx-auto mb-4 text-6xl text-[#2E8B57]" />
          <h1 className="text-2xl font-extrabold text-[#0F1B2D]">Registration Successful</h1>
          <p className="mt-3 text-sm leading-6 text-[#5A6B82]">
            Your application has been submitted and is currently under admin verification. You will receive an email after approval.
          </p>

          {registration?.registration_id && (
            <div className="mx-auto mt-6 w-fit rounded-xl border border-[#DEE7F1] bg-[#F7FAFD] px-6 py-3">
              <p className="text-xs font-bold uppercase tracking-[.08em] text-[#8494A9]">Your Registration ID</p>
              <p className="font-mono text-lg font-semibold text-primary-600">{registration.registration_id}</p>
            </div>
          )}

          <Link to="/" className="btn-primary mt-8">
            Register Another
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default Success;
