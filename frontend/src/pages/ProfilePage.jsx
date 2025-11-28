import React, { useRef, useState } from "react";
import {
  User,Mail, Calendar, Camera, Edit3, Save, X, Loader2, Trash2,
} from "lucide-react";
import { api } from "../api/axiosInstance";
import { useAuth } from "../context/AuthContext";

const MAX_UPLOAD_MB = 8;

export default function ProfilePage() {
  const { user, setUser } = useAuth();

  // Normalizzo lo stato iniziale con i campi disponibili
  const initial = {
    id: user?.id || "",
    username: user?.username || "",
    email: user?.email || "",
    nome: user?.nome || "",
    cognome: user?.cognome || "",
    dataNascita: user?.dataNascita || "",
    sesso: user?.sesso || "",
    avatarUrl: user?.avatarUrl || null,
    avatarThumbUrl: user?.avatarThumbUrl || null,
    dataRegistrazione: user?.dataRegistrazione || "", // ISO opzionale
  };

  const [userData, setUserData] = useState(initial);
  const [editData, setEditData] = useState(initial);
  const [isEditing, setIsEditing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);

  const fileRef = useRef(null);

  const initials =
    (userData?.username || userData?.email || "U")
      .split(" ")
      .map((p) => p[0]?.toUpperCase())
      .join("")
      .slice(0, 2) || "U";

  const formatDate = (iso) => {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleDateString("it-IT", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    } catch {
      return "";
    }
  };

  const handleEditToggle = () => {
    if (isEditing) setEditData({ ...userData });
    setIsEditing((v) => !v);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setUserData({ ...editData });
      setIsEditing(false);
    } catch (e) {
      console.error(e);
      alert("Errore nel salvataggio dei dati");
    } finally {
      setSaving(false);
    }
  };

  // Apertura file
  const handleImageSelectClick = () => fileRef.current?.click();

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      alert("Seleziona un file immagine (jpg, png, webp).");
      return;
    }
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > MAX_UPLOAD_MB) {
      alert(`File troppo grande. Massimo ${MAX_UPLOAD_MB}MB`);
      return;
    }

    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);

      const { data } = await api.post("/api/utenti/avatar", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const newAvatar = data?.url;
      const newThumb = data?.thumbUrl;

      // Aggiorno AuthContext (Navbar si aggiorna)
      setUser((prev) => ({
        ...prev,
        avatarUrl: newAvatar,
        avatarThumbUrl: newThumb,
      }));

      // Aggiorno pagina profilo
      setUserData((prev) => ({
        ...prev,
        avatarUrl: newAvatar,
        avatarThumbUrl: newThumb,
      }));
      setEditData((prev) => ({
        ...prev,
        avatarUrl: newAvatar,
        avatarThumbUrl: newThumb,
      }));
    } catch (err) {
      console.error("Errore upload avatar:", err);
      alert("Errore nel caricamento dell'immagine");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleDeleteImage = async () => {
    if (!window.confirm("Rimuovere l'immagine del profilo?")) return;

    try {
      setUser((prev) => ({ ...prev, avatarUrl: null, avatarThumbUrl: null }));
      setUserData((prev) => ({ ...prev, avatarUrl: null, avatarThumbUrl: null }));
      setEditData((prev) => ({ ...prev, avatarUrl: null, avatarThumbUrl: null }));
    } catch (err) {
      console.error(err);
      alert("Errore nella rimozione dell'immagine");
    }
  };

  return (
    <div className="pt-16 bg-green-50 min-h-screen">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* CARD */}
        <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
          {/* HEADER */}
          <div className="relative bg-gradient-to-r from-emerald-600 to-emerald-700 px-6 sm:px-8 py-10">
            <div className="flex items-center gap-6">
<div className="flex flex-col items-center">
  {/* Cerchio avatar */}
  <div className="h-28 w-28 rounded-full ring-4 ring-white/30 bg-white overflow-hidden flex items-center justify-center">
    {userData.avatarThumbUrl || userData.avatarUrl ? (
      <img
        src={userData.avatarThumbUrl || userData.avatarUrl}
        alt="Avatar"
        className="h-full w-full object-cover"
      />
    ) : (
      <div className="h-full w-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-3xl font-bold">
        {initials}
      </div>
    )}
  </div>

  {/* Pulsanti sotto l'avatar */}
  <div className="mt-3 flex items-center gap-2">
    {/* Cambia foto */}
    <button
      type="button"
      onClick={handleImageSelectClick}
      disabled={uploading}
      title="Cambia foto"
      className="inline-flex items-center justify-center h-9 w-9 rounded-full bg-white/95 text-emerald-700 shadow hover:bg-white disabled:opacity-60"
    >
      {uploading ? (
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/>
        </svg>
      ) : (
        <Camera className="h-4 w-4" />
      )}
    </button>

    {/* Rimuovi (mostra solo se c'è un avatar) */}
    {(userData.avatarUrl || userData.avatarThumbUrl) && (
      <button
        type="button"
        onClick={handleDeleteImage}
        title="Rimuovi foto"
        className="inline-flex items-center justify-center h-9 w-9 rounded-full border border-white/70 text-white hover:bg-white/10"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    )}
  </div>

  {/* input file nascosto */}
  <input
    ref={fileRef}
    type="file"
    accept="image/*"
    className="hidden"
    onChange={handleImageUpload}
  />
</div>

              {/* NOME & DATA */}
              <div className="text-white">
                <h1 className="text-3xl font-bold leading-tight">
                  {userData.username || "Utente"}
                </h1>
                {formatDate(userData.dataRegistrazione) && (
                  <p className="text-emerald-100 mt-1">
                    Registrato il {formatDate(userData.dataRegistrazione)}
                  </p>
                )}
              </div>

              {/* TOGGLE EDIT */}
              <div className="ml-auto">
                {!isEditing ? (
                  <button
                    onClick={handleEditToggle}
                    className="inline-flex items-center gap-2 rounded-lg bg-white text-emerald-700 px-4 py-2 shadow hover:bg-emerald-50"
                  >
                    <Edit3 className="h-4 w-4" />
                    <span>Modifica</span>
                  </button>
                ) : (
                  <div className="flex gap-2">
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="inline-flex items-center gap-2 rounded-lg bg-white text-emerald-700 px-4 py-2 shadow hover:bg-emerald-50 disabled:opacity-60"
                    >
                      {saving ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Save className="h-4 w-4" />
                      )}
                      <span>{saving ? "Salvo..." : "Salva"}</span>
                    </button>
                    <button
                      onClick={handleEditToggle}
                      className="inline-flex items-center gap-2 rounded-lg bg-white/10 text-white px-4 py-2 ring-1 ring-white/30 hover:bg-white/20"
                    >
                      <X className="h-4 w-4" />
                      <span>Annulla</span>
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* file input nascosto */}
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleImageUpload}
            />
          </div>

          {/* BODY */}
          <div className="px-6 sm:px-8 py-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">
              Informazioni Personali
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {/* Username (readonly) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Username
                </label>
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    value={userData.username}
                    readOnly
                    className="w-full bg-gray-100 px-3 py-2 rounded-md border border-gray-200 text-gray-700"
                  />
                </div>
              </div>

              {/* Email (readonly) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email
                </label>
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-gray-400" />
                  <input
                    type="email"
                    value={userData.email}
                    readOnly
                    className="w-full bg-gray-100 px-3 py-2 rounded-md border border-gray-200 text-gray-700"
                  />
                </div>
              </div>

              {/* Nome */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nome
                </label>
                <input
                  type="text"
                  value={isEditing ? editData.nome : userData.nome}
                  onChange={(e) =>
                    setEditData((prev) => ({ ...prev, nome: e.target.value }))
                  }
                  readOnly={!isEditing}
                  className={`w-full px-3 py-2 rounded-md border ${
                    isEditing
                      ? "border-gray-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      : "bg-gray-100 border-gray-200 text-gray-700"
                  }`}
                  placeholder="Il tuo nome"
                />
              </div>

              {/* Cognome */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Cognome
                </label>
                <input
                  type="text"
                  value={isEditing ? editData.cognome : userData.cognome}
                  onChange={(e) =>
                    setEditData((prev) => ({ ...prev, cognome: e.target.value }))
                  }
                  readOnly={!isEditing}
                  className={`w-full px-3 py-2 rounded-md border ${
                    isEditing
                      ? "border-gray-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      : "bg-gray-100 border-gray-200 text-gray-700"
                  }`}
                  placeholder="Il tuo cognome"
                />
              </div>

              {/* Data di nascita */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Data di nascita
                </label>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-gray-400" />
                  <input
                    type="date"
                    value={
                      isEditing
                        ? (editData.dataNascita || "")
                        : (userData.dataNascita || "")
                    }
                    onChange={(e) =>
                      setEditData((prev) => ({
                        ...prev,
                        dataNascita: e.target.value,
                      }))
                    }
                    readOnly={!isEditing}
                    className={`w-full px-3 py-2 rounded-md border ${
                      isEditing
                        ? "border-gray-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        : "bg-gray-100 border-gray-200 text-gray-700"
                    }`}
                  />
                </div>
              </div>

              {/* Sesso */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Sesso
                </label>
                <select
                  value={isEditing ? (editData.sesso || "") : (userData.sesso || "")}
                  onChange={(e) =>
                    setEditData((prev) => ({ ...prev, sesso: e.target.value }))
                  }
                  disabled={!isEditing}
                  className={`w-full px-3 py-2 rounded-md border ${
                    isEditing
                      ? "border-gray-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      : "bg-gray-100 border-gray-200 text-gray-700"
                  }`}
                >
                  <option value="">-</option>
                  <option value="M">M</option>
                  <option value="F">F</option>
                  <option value="Altro">Altro</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Spaziatura finale */}
        <div className="h-6" />
      </div>
    </div>
  );
}