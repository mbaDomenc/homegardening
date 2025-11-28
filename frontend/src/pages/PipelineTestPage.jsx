import React, { useState } from 'react';
import { 
    Brain, MapPin, Sprout, Thermometer, 
    Droplets, Sun, CloudRain, AlertTriangle, Search, ArrowRight
} from 'lucide-react';
import { processPipeline } from '../api/pipelineApi';
import { api } from '../api/axiosInstance'; 
import PlaceAutocomplete from '../components/PlaceAutocomplete';
import PipelineResultCard from '../components/PipelineResultCard';
import RequireAuth from '../components/RequireAuth';

const SUPPORTED_PLANTS = [
    { id: 'tomato', label: 'Pomodoro (Tomato)' },
    { id: 'potato', label: 'Patata (Potato)' },
    { id: 'pepper', label: 'Peperone (Pepper)' },
    { id: 'peach', label: 'Pesca (Peach)' },   
    { id: 'grape', label: 'Uva (Grape)' },     
    { id: 'generic', label: 'Altra Specie (Generica)' }
];

const SUPPORTED_SOILS = [
    { id: 'franco', label: 'Lavorabile (Medio impasto)' },
    { id: 'universale', label: 'Universale (Standard)' },
    { id: 'argilloso', label: 'Argilloso (Pesante)' },
    { id: 'sabbioso', label: 'Sabbioso (Drenante)' },
    { id: 'acido', label: 'Acido (es. Mirtilli)' },
    { id: 'torboso', label: 'Torboso' }
];

export default function PipelineTestPage() {
    const [plantType, setPlantType] = useState('tomato');
    const [location, setLocation] = useState('');
    const [geoData, setGeoData] = useState(null); 
    const [soilType, setSoilType] = useState('franco');

    const [result, setResult] = useState(null);
    const [weatherData, setWeatherData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handlePlaceSelect = (place) => {
        setLocation(place.formattedAddress);
        setGeoData(place);
    };

    const handleAnalyze = async () => {
        if (!geoData) {
            setError("Per favore seleziona una località valida.");
            return;
        }

        setLoading(true);
        setError(null);
        setResult(null);
        setWeatherData(null);

        try {
            //USA LE COORDINATE PER IL METEO
            let url = '/api/weather';
            if (geoData.lat && geoData.lng) {
                url += `?lat=${geoData.lat}&lon=${geoData.lng}`;
            } else {
                const city = geoData.addrParts?.locality || geoData.formattedAddress;
                url += `?city=${encodeURIComponent(city)}`;
            }

            const weatherRes = await api.get(url);
            const weather = weatherRes.data;
            setWeatherData(weather);

            const sensorData = {
                temperature: weather.temp,
                humidity: weather.humidity,
                rainfall: weather.rainNext24h || 0.0,
                light: weather.light || 0.0,
                soil_moisture: weather.soil_moisture || 0.0
            };

            const payload = {
                sensor_data: sensorData,
                plant_type: plantType,
                soil_type: soilType 
            };

            const pipelineRes = await processPipeline(payload); 
            if (pipelineRes.status === 'error') throw new Error(pipelineRes.metadata.errors.join(', '));

            setResult(pipelineRes);

        } catch (err) {
            console.error('Errore analisi:', err);
            setError(err.response?.data?.detail || err.message || 'Errore analisi');
        } finally {
            setLoading(false);
        }
    };

    const handleReset = () => {
        setLocation('');
        setGeoData(null);
        setResult(null);
        setWeatherData(null);
        setError(null);
        setSoilType('franco');
    };

    const getSuitabilityBadge = (res) => {
        const comfort = res?.details?.features?.climate_comfort_index || 0;
        if (comfort >= 75) return { label: "LUOGO IDEALE", color: "text-emerald-700", bg: "bg-emerald-100", border: "border-emerald-200" };
        if (comfort >= 50) return { label: "BUONO", color: "text-blue-700", bg: "bg-blue-100", border: "border-blue-200" };
        if (comfort >= 30) return { label: "ACCETTABILE", color: "text-yellow-700", bg: "bg-yellow-100", border: "border-yellow-200" };
        return { label: "SCONSIGLIATO", color: "text-red-700", bg: "bg-red-100", border: "border-red-200" };
    };

    return (
        <RequireAuth>
            <div className="min-h-screen bg-[#f0fdf4] pt-36 pb-12 px-6 relative overflow-hidden">
                <div className="max-w-7xl mx-auto">
                    {/* Header */}
                    <div className="mb-12 text-center md:text-left">
                        <h1 className="text-4xl font-extrabold text-gray-900 mb-2">Analisi Idoneità Ambientale</h1>
                        <p className="text-gray-600">Simula le condizioni di coltivazione prima di piantare.</p>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        {/* Configurazione */}
                        <div className="lg:col-span-1">
                            <div className="glass bg-white/80 p-8 rounded-[2rem] shadow-xl border border-white/50 sticky top-28">
                                <h2 className="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2">
                                    <div className="p-2 bg-blue-100 rounded-xl text-blue-600"><MapPin className="h-5 w-5" /></div>Configura
                                </h2>
                                <div className="space-y-6">
                                    <div className="space-y-2">
                                        <label className="text-sm font-bold text-gray-600 ml-1">Pianta</label>
                                        <div className="relative">
                                            <select value={plantType} onChange={(e) => setPlantType(e.target.value)} className="w-full pl-4 pr-10 py-3.5 bg-white border-none rounded-2xl shadow-sm focus:ring-4 focus:ring-emerald-100 outline-none appearance-none font-medium text-gray-700 transition-all">
                                                {SUPPORTED_PLANTS.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
                                            </select>
                                            <ArrowRight className="absolute right-4 top-4 h-5 w-5 text-gray-400 rotate-90 pointer-events-none" />
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-bold text-gray-600 ml-1">Tipo di Terreno</label>
                                        <div className="relative">
                                            <select value={soilType} onChange={(e) => setSoilType(e.target.value)} className="w-full pl-4 pr-10 py-3.5 bg-white border-none rounded-2xl shadow-sm focus:ring-4 focus:ring-emerald-100 outline-none appearance-none font-medium text-gray-700 transition-all">
                                                {SUPPORTED_SOILS.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
                                            </select>
                                            <ArrowRight className="absolute right-4 top-4 h-5 w-5 text-gray-400 rotate-90 pointer-events-none" />
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-sm font-bold text-gray-600 ml-1">Località</label>
                                        <PlaceAutocomplete value={location} onChangeText={setLocation} onSelectPlace={handlePlaceSelect} placeholder="Cerca città..." className="w-full pl-4 pr-4 py-3.5 bg-white border-none rounded-2xl shadow-sm focus:ring-4 focus:ring-emerald-100 outline-none font-medium placeholder-gray-400 transition-all" />
                                    </div>
                                    <div className="pt-4 flex gap-3">
                                        <button onClick={handleAnalyze} disabled={loading || !geoData} className="btn-bouncy flex-1 bg-emerald-600 text-white py-3.5 rounded-2xl hover:bg-emerald-500 font-bold shadow-lg shadow-emerald-200 disabled:opacity-50 flex items-center justify-center gap-2">
                                            {loading ? "Calcolo..." : <><Search className="h-5 w-5" /> Analizza</>}
                                        </button>
                                        {result && <button onClick={handleReset} className="btn-bouncy px-5 py-3.5 bg-white text-gray-600 font-bold rounded-2xl shadow-md hover:bg-gray-50 border border-gray-100">Reset</button>}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Risultati */}
                        <div className="lg:col-span-2 space-y-6">
                            {error && <div className="bg-red-50 p-6 rounded-3xl border border-red-100 flex items-start gap-4"><AlertTriangle className="h-6 w-6 text-red-600" /><div><h3 className="font-bold text-red-800 text-lg">Errore Analisi</h3><p className="text-red-600">{error}</p></div></div>}
                            
                            {!result && !loading && !error && (
                                <div className="glass bg-white/60 h-full min-h-[400px] rounded-[2.5rem] border border-white/50 flex flex-col items-center justify-center text-center p-10 border-dashed border-gray-300/50">
                                    <div className="bg-emerald-100 p-6 rounded-full mb-6 shadow-inner"><Brain className="h-12 w-12 text-emerald-600" /></div>
                                    <h3 className="text-2xl font-bold text-gray-800 mb-2">In attesa di input</h3>
                                    <p className="text-gray-500 max-w-md">Seleziona i parametri a sinistra.</p>
                                </div>
                            )}

                            {result && (
                                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
                                    <div className="bg-white rounded-[2.5rem] shadow-xl border border-white/60 overflow-hidden">
                                        <div className="bg-gray-50/50 p-8 border-b border-gray-100 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                                            <div><h2 className="text-2xl font-extrabold text-gray-900">Report per <span className="text-emerald-600 uppercase">{plantType}</span></h2><div className="flex items-center gap-2 text-gray-500 mt-1 font-medium"><MapPin className="h-4 w-4" /> {geoData?.formattedAddress}</div></div>
                                            {(() => { const badge = getSuitabilityBadge(result); return (<div className={`px-6 py-3 rounded-2xl border-2 ${badge.border} ${badge.bg} ${badge.color} text-center shadow-sm`}><p className="text-[10px] font-bold tracking-widest uppercase opacity-80 mb-1">Rating</p><p className="text-xl font-black leading-none">{badge.label}</p></div>); })()}
                                        </div>
                                        <div className="p-8 grid grid-cols-2 md:grid-cols-4 gap-4">
                                            <div className="p-4 bg-orange-50 rounded-2xl text-center"><Thermometer className="h-6 w-6 text-orange-500 mx-auto mb-2" /><span className="text-xs font-bold uppercase">Temp</span><div className="text-2xl font-black mt-1 text-orange-500">{Math.round(weatherData.temp)}°</div></div>
                                            <div className="p-4 bg-blue-50 rounded-2xl text-center"><Droplets className="h-6 w-6 text-blue-500 mx-auto mb-2" /><span className="text-xs font-bold uppercase">Umidità</span><div className="text-2xl font-black mt-1 text-blue-500">{weatherData.humidity}%</div></div>
                                            <div className="p-4 bg-indigo-50 rounded-2xl text-center"><CloudRain className="h-6 w-6 text-indigo-500 mx-auto mb-2" /><span className="text-xs font-bold uppercase">Pioggia</span><div className="text-2xl font-black mt-1 text-indigo-500">{weatherData.rainNext24h}mm</div></div>
                                            <div className="p-4 bg-yellow-50 rounded-2xl text-center"><Sun className="h-6 w-6 text-yellow-600 mx-auto mb-2" /><span className="text-xs font-bold uppercase">Luce</span><div className="text-2xl font-black mt-1 text-yellow-600">{(weatherData.light/1000).toFixed(1)}k</div></div>
                                        </div>
                                    </div>
                                    <div className="opacity-100"><PipelineResultCard result={result} plantType={plantType} /></div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </RequireAuth>
    );
}