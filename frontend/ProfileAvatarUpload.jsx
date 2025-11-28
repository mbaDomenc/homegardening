import React, { useState } from "react";
import { uploadAvatar } from "../api/uploads";

export default function ProfileAvatarUpload() {
  const [preview, setPreview] = useState(null);

  const handleChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setPreview(URL.createObjectURL(file));

    try {
      const res = await uploadAvatar(file);
      console.log("Avatar caricato:", res);
    } catch (err) {
      console.error("Errore upload avatar:", err);
    }
  };

  return (
    <div>
      {preview && <img src={preview} alt="Preview" className="w-24 h-24 rounded-full" />}
      <input type="file" accept="image/*" onChange={handleChange} />
    </div>
  );
}