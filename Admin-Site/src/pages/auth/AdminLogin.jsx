import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { FiLock } from "react-icons/fi";
import { toast } from "react-toastify";

import Button from "../../components/common/Button";
import Input from "../../components/common/Input";
import { useAuth } from "../../hooks/useAuth";
import { useAutofillSync } from "../../hooks/useAutofillSync";

const AdminLogin = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const formRef = useRef(null);
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm({ mode: "onTouched", reValidateMode: "onChange" });

  useAutofillSync(formRef, setValue);

  const onSubmit = async ({ email, password }) => {
    setSubmitting(true);
    try {
      await login(email, password);
      toast.success("Welcome back!");
      navigate("/dashboard");
    } catch (err) {
      const message = err?.response?.data?.detail || "Invalid email or password";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="dv-admin-shell flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm overflow-hidden rounded-[20px] border border-[#DEE7F1] bg-white shadow-[0_24px_60px_-34px_rgba(15,27,45,.55)]">
        <div className="border-b border-[#EEF2F7] bg-[#0E1A2B] px-8 py-7 text-center">
          <img src="/brand/logo-icon.png" alt="DVein Innovations" className="mx-auto mb-3 h-12 w-auto" />
          <p className="text-[11px] font-extrabold uppercase tracking-[.14em] text-[#94A3B8]">Internship Portal</p>
          <h1 className="mt-1 text-xl font-extrabold text-white">Admin Login</h1>
        </div>
        <form ref={formRef} onSubmit={handleSubmit(onSubmit)} className="space-y-4 p-8">
          <Input label="Email" type="email" required placeholder="admin@dveininnovation.com" error={errors.email?.message} {...register("email", { required: "Email is required" })} />
          <Input label="Password" type="password" required placeholder="Password" error={errors.password?.message} {...register("password", { required: "Password is required" })} />
          <Button type="submit" loading={submitting} className="w-full">
            <FiLock /> Sign In
          </Button>
        </form>
      </div>
    </div>
  );
};

export default AdminLogin;
