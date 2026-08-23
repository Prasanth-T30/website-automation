import Footer from "../../components/layout/Footer";
import Navbar from "../../components/layout/Navbar";
import RegistrationForm from "../../components/registration/RegistrationForm";

const Registration = () => (
  <div className="dv-shell flex min-h-screen flex-col">
    <Navbar />
    <main className="mx-auto w-full max-w-[560px] flex-1 px-4 pb-16 pt-7">
      <div className="flex flex-col items-center gap-2 pb-6 text-center">
        <img src="/brand/logo.png" alt="DVein Innovations" className="h-[70px] w-auto" />
        <p className="max-w-md text-[13px] font-medium leading-6 text-[#5A6B82]">
          Internship, course and project registration for students and working professionals
        </p>
      </div>

      <div className="glass-card overflow-hidden p-5 sm:p-6">
        <RegistrationForm />
      </div>
    </main>
    <Footer />
  </div>
);

export default Registration;
