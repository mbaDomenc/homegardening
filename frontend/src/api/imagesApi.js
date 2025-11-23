import { api } from "./axiosInstance";

/**
 * Carica un'immagine sul server.
 * Il backend estrarrà automaticamente i metadati tecnici.
 */
export async function uploadImage(file, metadata = {}) {
  const formData = new FormData();
  formData.append("file", file);

  // Aggiungi i campi opzionali se presenti
  if (metadata.planttype) formData.append("planttype", metadata.planttype);
  if (metadata.location) formData.append("location", metadata.location);
  if (metadata.sensorid) formData.append("sensorid", metadata.sensorid);
  if (metadata.notes) formData.append("notes", metadata.notes);

  // Header Content-Type multipart/form-data viene settato automaticamente da axios quando vede FormData
  const { data } = await api.post("/api/images/upload", formData);
  return data;
}

/**
 * Recupera la lista delle immagini (con filtri opzionali)
 */
export async function getImagesList(filters = {}) {
  const params = {};
  if (filters.limit) params.limit = filters.limit;
  if (filters.planttype) params.planttype = filters.planttype;
  if (filters.processed !== undefined) params.processed = filters.processed;

  const { data } = await api.get("/api/images/list", { params });
  return data;
}

/**
 * Elimina un'immagine
 */
export async function deleteImage(imageId) {
  const { data } = await api.delete(`/api/images/delete/${imageId}`);
  return data;
}