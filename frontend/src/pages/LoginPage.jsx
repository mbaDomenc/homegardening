import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Lock, Leaf, Eye, EyeOff } from 'lucide-react';
import { api } from '../api/axiosInstance';
import { useAuth } from '../context/AuthContext';

const LoginPage = () => {
  const navigate = useNavigate();
  const { setAccessToken, setUser } = useAuth(); // dal tuo AuthContext

  const [formData, setFormData] = useState({
    identifier: '', // email o username
    password: ''
  });

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);

    try {
      // Decidi dinamicamente se inviare email o username
      const payload = {
        password: formData.password
      };
      if (formData.identifier.includes('@')) {
        payload.email = formData.identifier.trim();
      } else {
        payload.username = formData.identifier.trim();
      }

      const res = await api.post('/api/utenti/login', payload);
      const token = res.data?.accessToken;

      if (!token) throw new Error('Token mancante nella risposta');

      // Salva nel context (così axiosInstance lo userà automaticamente)
      setAccessToken(token);
      setUser(res.data?.utente || null);

      // Vai alla home (o dashboard)
      navigate('/', { replace: true });
    } catch (err) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        'Errore di login';
      setErrorMsg(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-green-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">

        {/* Header */}
        <div className="text-center">
          <div className="flex justify-center mb-6">
            <div className="bg-green-600 p-4 rounded-full">
              <Leaf className="h-12 w-12 text-white" />
            </div>
          </div>
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            Accedi al tuo account
          </h2>
          <p className="text-gray-600">
            Bentornato! Accedi per continuare a coltivare il tuo giardino.
          </p>
        </div>

        {/* Login Form */}
        <div className="bg-white p-8 rounded-xl shadow-lg">
          {errorMsg && (
            <div className="mb-4 rounded-md bg-red-50 px-4 py-3 text-red-700 text-sm">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Email o Username */}
            <div>
              <label htmlFor="identifier" className="flex items-center space-x-2 text-sm font-medium text-gray-700 mb-2">
                <User className="h-4 w-4" />
                <span>Email o Username</span>
              </label>
              <input
                type="text"
                id="identifier"
                name="identifier"
                value={formData.identifier}
                onChange={handleChange}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent transition-colors"
                placeholder="Inserisci email o username"
              />
            </div>

            {/* Password con toggle visibilità */}
            <div>
              <label htmlFor="password" className="flex items-center space-x-2 text-sm font-medium text-gray-700 mb-2">
                <Lock className="h-4 w-4" />
                <span>Password</span>
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  maxLength={72}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent transition-colors pr-10"
                  placeholder="La tua password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(prev => !prev)}
                  className="absolute inset-y-0 right-3 flex items-center text-gray-500 hover:text-gray-700"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            {/* Ricordami e link */}
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
                  Ricordami
                </label>
              </div>
              <Link to="/forgot-password" className="text-sm text-green-600 hover:text-green-500">
                Password dimenticata?
              </Link>
            </div>

            {/* Pulsante Login */}
            <button
              type="submit"
              disabled={loading}
              className={`w-full ${loading ? 'bg-green-400' : 'bg-green-600 hover:bg-green-700'} text-white py-3 px-6 rounded-lg transition-colors font-medium`}
            >
              {loading ? 'Accesso in corso...' : 'Accedi'}
            </button>
          </form>

          {/* Link Registrazione */}
          <div className="mt-6 text-center">
            <p className="text-gray-600">
              Non hai un account?{' '}
              <Link to="/register" className="text-green-600 hover:text-green-500 font-medium">
                Registrati qui
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;