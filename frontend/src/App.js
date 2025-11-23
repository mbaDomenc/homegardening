import React from "react";
import { Routes, Route, Navigate, useParams, useNavigate } from "react-router-dom";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import Dashboard from "./pages/Dashboard";
import ProfilePage from "./pages/ProfilePage";
import AIIrrigationPage from './pages/AIIrrigationPage';

//NUOVA IMPORTAZIONE PER PipelineTestPage, AL FINE DI UTILIZZARLO ALL'INTERNO DI APP
import PipelineTestPage from "./pages/PipelineTestPage";

import PlantsList from "./pages/PlantsList";
import PlantDetail from "./pages/PlantDetail";

import RequireAuth from './components/RequireAuth';
import RequireGuest from './components/RequireGuest';



// Wrapper per la lista: passa navigate a PlantsList
function PlantsListWrapper() {
    const navigate = useNavigate();
    return (
        <RequireAuth>
            <PlantsList
                onOpenDetail={(plant) => {
                    if (plant?.id) navigate(`/piante/${plant.id}`);
                }}
            />
        </RequireAuth>
    );
}

// Wrapper per il dettaglio: legge :id dall'URL e gestisce back/delete
function PlantDetailWrapper() {
    const { id } = useParams();
    const navigate = useNavigate();
    return (
        <RequireAuth>
            <PlantDetail
                plantId={id}
                onBack={() => navigate('/piante')}
                onDeleted={() => navigate('/piante')}
            />
        </RequireAuth>
    );
}

export default function App() {
    return (
        <div className="min-h-screen flex flex-col bg-white">
            <Navbar />
            <main className="flex-1">
                <Routes>
                    <Route path="/" element={<HomePage />} />

                    {/* Guest only */}
                    <Route path="/login" element={
                        <RequireGuest>
                            <LoginPage/>
                        </RequireGuest>
                    }/>
                    <Route path="/register" element={
                        <RequireGuest>
                            <RegisterPage/>
                        </RequireGuest>
                    }/>

                    {/* Private */}
                    <Route path="/dashboard" element={
                        <RequireAuth>
                            <Dashboard />
                        </RequireAuth>
                    }/>
                    <Route
                        path="/profilo"
                        element={
                            <RequireAuth>
                                <ProfilePage />
                            </RequireAuth>
                        }
                    />

                    <Route
                        path="/ai/irrigazione"
                        element={
                            <RequireAuth>
                                <AIIrrigationPage />
                            </RequireAuth>
                        }
                    />

                    <Route
                        path="/ai/pipeline-test"
                        element={<RequireAuth><PipelineTestPage />
                        </RequireAuth>} 
                    />


                    {/* Piante */}
                    <Route path="/piante" element={<PlantsListWrapper />} />
                    <Route path="/piante/:id" element={<PlantDetailWrapper />} />



                    {/* Fallback */}
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </main>
            <Footer />
        </div>
    );
}