import { useState } from "react";
import { FiUploadCloud, FiX } from "react-icons/fi";
import { toast } from "react-toastify";

import { isFileSizeValid, isValidImageFile } from "../../utils/validators";

const PaymentUpload = ({ file, onChange }) => {
  const [preview, setPreview] = useState(null);

  const handleFile = (selected) => {
    if (!selected) return;
    if (!isValidImageFile(selected)) {
      toast.error("Only JPG, JPEG, or PNG files are supported");
      return;
    }
    if (!isFileSizeValid(selected, 5)) {
      toast.error("File size must not exceed 5 MB");
      return;
    }
    onChange(selected);
    setPreview(URL.createObjectURL(selected));
  };

  const clear = () => {
    onChange(null);
    setPreview(null);
  };

  return (
    <div>
      <label className="dv-label">
        Payment Screenshot <span className="text-[#DC5B5B]">*</span>
      </label>

      {!file ? (
        <label className="flex cursor-pointer flex-col items-center justify-center rounded-[14px] border-2 border-dashed border-[#C9D4E3] bg-white px-4 py-8 text-center transition hover:border-primary-400 hover:bg-primary-50/40">
          <FiUploadCloud className="mb-2 text-2xl text-primary-500" />
          <p className="text-sm font-semibold text-[#41536B]">Click to upload payment screenshot</p>
          <p className="mt-1 text-xs font-medium text-[#8494A9]">JPG, JPEG, PNG - up to 5 MB</p>
          <input type="file" accept=".jpg,.jpeg,.png" className="hidden" onChange={(e) => handleFile(e.target.files?.[0])} />
        </label>
      ) : (
        <div className="relative w-fit">
          <img src={preview} alt="Payment proof preview" className="h-40 w-auto rounded-[14px] border border-[#DEE7F1] object-cover" />
          <button
            type="button"
            onClick={clear}
            className="absolute -right-2 -top-2 flex h-7 w-7 items-center justify-center rounded-full bg-[#C2453F] text-white shadow-md hover:brightness-105"
          >
            <FiX size={14} />
          </button>
        </div>
      )}
    </div>
  );
};

export default PaymentUpload;
