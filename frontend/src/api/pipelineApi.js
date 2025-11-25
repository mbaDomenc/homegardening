import { api } from "./axiosInstance";


export async function processPipeline(arg1, arg2 = "generic") {
  let payload;

  // Controllo se il primo argomento è già il payload completo (contiene la chiave sensor_data)
  if (arg1.sensor_data) {
      // Modalità Nuova (quella che usa PipelineTestPage)
      payload = arg1;
  } else {
      // Modalità Vecchia (compatibilità)
      payload = {
        sensor_data: arg1,
        plant_type: arg2,
      };
  }

  // Debug: controlla nella console del browser cosa stiamo inviando
  console.log("[API] Invio Pipeline:", payload);

  const { data } = await api.post("/api/pipeline/process", payload);
  return data;
}

/**
 * Endpoint semplificato per il suggerimento rapido.
 */
export async function getQuickSuggestion(sensorData, plantType = "generic") {
    // Usiamo process per coerenza e estraiamo i dati
    const fullResult = await processPipeline({
        sensor_data: sensorData,
        plant_type: plantType
    });
    
    return {
        status: fullResult.status,
        suggestion: fullResult.suggestion,
        metadata: fullResult.metadata
    };
}
