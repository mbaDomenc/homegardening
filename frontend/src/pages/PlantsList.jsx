import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Search, Leaf } from 'lucide-react';
import { api } from '../api/axiosInstance';
import PlantCard from '../components/PlantCard';
import PlantFormModal from '../components/PlantFormModal';
import { uploadPlantImage } from '../api/uploads';

//  Normalizzazione:  gestisce id string, _id string, _id.$oid, e normalizza date
const normalize = (arr = []) =>
  arr
    .filter(Boolean)
    .map((p) => ({
      ...p,
      id: p.id || p._id || (p?._id?.$oid ?? null),
      createdAt: p.createdAt ? new Date(p.createdAt).toISOString() : null,
      updatedAt: p.updatedAt ? new Date(p.updatedAt).toISOString() : null,
    }));

const PlantsList = ({ onOpenDetail = () => {} }) => {
  const [plants, setPlants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPlant, setEditingPlant] = useState(null);

  // Carica lista piante
  const loadPlants = useCallback(async () => {
    try {
      setLoading(true);
      const { data } = await api.get('/api/piante');
      console.log('[PlantsList] GET /api/piante →', data);

      const normalized = normalize(data);
      console.log('[PlantsList] normalized →', normalized);

      setPlants(normalized);
      setError('');
    } catch (err) {
      console.error('Errore nel caricamento piante:', err);
      setError('Errore nel caricamento delle piante');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPlants();
  }, [loadPlants]);

  // Filtra piante per ricerca
  const filteredPlants = plants.filter((plant) => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return true;
    return (
      (plant?.name || '').toLowerCase().includes(term) ||
      (plant?.species || '').toLowerCase().includes(term)
    );
  });

  // Aggiungi nuova pianta (apri modal vuoto)
  const handleAddPlant = () => {
    setEditingPlant(null);
    setModalOpen(true);
  };

  // Modifica pianta (apri modal precompilata)
  const handleEditPlant = (plant) => {
    setEditingPlant(plant);
    setModalOpen(true);
  };

  // Submit form (create/update) —> ricarico sempre la lista dal server
  
  const handleFormSubmit = async (formData, imageFile) => { 
    try {
      let plantId = null;

      if (editingPlant) {
        // Modifica
        plantId = editingPlant.id;
        await api.patch(`/api/piante/${plantId}`, formData);
      } else {
        // Creazione
        const { data } = await api.post('/api/piante', formData);
        plantId = data.id || data._id; // Assicurati di prendere l'ID corretto dalla risposta
      }

      // Se c'è un file immagine, caricalo ora usando l'ID della pianta
      if (imageFile && plantId) {
        console.log("Caricamento immagine per pianta:", plantId);
        try {
            await uploadPlantImage(plantId, imageFile);
        } catch (imgErr) {
            console.error("Errore caricamento immagine:", imgErr);
            alert("Pianta salvata, ma errore nel caricamento dell'immagine.");
        }
      }

      await loadPlants(); // Ricarica la lista
      setModalOpen(false);
      setEditingPlant(null);
    } catch (error) {
      console.error('Errore nel salvataggio:', error);
      throw error;
    }
  };

  // Inline edit
  const handleInlineSave = async (plantId, patch) => {
    try {
      await api.patch(`/api/piante/${plantId}`, patch);
      await loadPlants();            
    } catch (error) {
      console.error("Errore nell'aggiornamento:", error);
      throw error;
    }
  };

  // Elimina
  const handleDeletePlant = async (plantId) => {
    try {
      await api.delete(`/api/piante/${plantId}`);
      await loadPlants();            
    } catch (error) {
      console.error("Errore nell'eliminazione:", error);
      alert("Errore nell'eliminazione della pianta");
    }
  };

  // Click card → apri dettaglio (il parent deve gestire la route)
  const handleOpenDetail = (plant) => {
  if (!plant?.id) {
    console.warn('[PlantsList] onOpenDetail chiamato senza id valido:', plant);
    return;
  }
  onOpenDetail(plant); // viene passato dal wrapper in App.js
};

  if (loading) {
    return (
      <div className="min-h-screen bg-green-50 pt-16">
        <div className="w-full max-w-screen-2xl xl:px-32 lg:px-12 md:px-8 sm:px-6 px-4 py-8 mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-green-50 pt-16">
        <div className="w-full max-w-screen-2xl xl:px-32 lg:px-12 md:px-8 sm:px-6 px-4 py-8 mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-600">{error}</p>
            <button
              onClick={loadPlants}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Riprova
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-green-50 pt-16">
      <div className="w-full max-w-screen-2xl xl:px-32 lg:px-12 md:px-8 sm:px-6 px-4 py-8 mx-auto">

        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Le mie piante</h1>
            <p className="text-gray-600">Gestisci e monitora tutte le tue piante</p>
          </div>
          <button
            onClick={handleAddPlant}
            className="mt-4 sm:mt-0 bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center space-x-2 shadow-lg"
          >
            <Plus className="h-5 w-5" />
            <span>Aggiungi pianta</span>
          </button>
        </div>

        {/* Barra ricerca */}
        <div className="mb-8">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Cerca per nome o specie..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent transition-colors"
            />
          </div>
        </div>

        {/* Lista piante */}
        {filteredPlants.length === 0 ? (
          <div className="text-center py-16">
            <div className="bg-white rounded-xl shadow-lg p-12 max-w-md mx-auto">
              <div className="bg-green-100 p-4 rounded-full w-20 h-20 mx-auto mb-6 flex items-center justify-center">
                <Leaf className="h-10 w-10 text-green-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-4">
                {searchTerm ? 'Nessuna pianta trovata' : 'Nessuna pianta ancora'}
              </h3>
              <p className="text-gray-600 mb-6">
                {searchTerm
                  ? 'Prova a modificare i termini di ricerca'
                  : 'Inizia aggiungendo la tua prima pianta per monitorarla e prendertene cura'}
              </p>
              {!searchTerm && (
                <button
                  onClick={handleAddPlant}
                  className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center space-x-2 mx-auto"
                >
                  <Plus className="h-5 w-5" />
                  <span>Aggiungi la prima pianta</span>
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">{filteredPlants
  .filter(p => p && (p.id || p._id))
  .map((plant) => (
    <PlantCard
      key={plant.id || plant._id}
      plant={plant}
      onOpenDetail={handleOpenDetail}
      onInlineSave={handleInlineSave}
      onDelete={handleDeletePlant}
    />
))}
          </div>
        )}

        {/* Modal Form */}
        <PlantFormModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          initialData={editingPlant}
          onSubmit={handleFormSubmit}
        />
      </div>
    </div>
  );
};

export default PlantsList;