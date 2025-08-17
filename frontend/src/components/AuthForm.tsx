"use client";

import { useState } from 'react';
import Link from 'next/link';
import { signInWithEmailAndPassword, createUserWithEmailAndPassword } from 'firebase/auth';
import { auth } from '@/lib/firebase';
import { useRouter } from 'next/navigation';

interface AuthFormProps {
  mode: 'login' | 'register';
}

export default function AuthForm({ mode }: AuthFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const isLogin = mode === 'login';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        // Login
        await signInWithEmailAndPassword(auth, email, password);
        router.push('/chat');
      } else {
        // Register
        if (password !== confirmPassword) {
          throw new Error('Le password non coincidono');
        }
        if (password.length < 6) {
          throw new Error('La password deve essere di almeno 6 caratteri');
        }
        await createUserWithEmailAndPassword(auth, email, password);
        router.push('/chat');
      }
    } catch (error: any) {
      console.error('Auth error:', error);
      setError(error.message || 'Si è verificato un errore');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="text-center">
            <div className="text-4xl mb-4">🤖</div>
            <h2 className="text-3xl font-bold text-gray-900">
              {isLogin ? 'Accedi al tuo account' : 'Crea un nuovo account'}
            </h2>
            <p className="mt-2 text-gray-600">
              {isLogin 
                ? 'Bentornato! Accedi per continuare le tue conversazioni AI personalizzate.'
                : 'Unisciti a ChatMap e inizia a creare le tue mappe concettuali.'
              }
            </p>
          </div>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Inserisci la tua email"
              />
            </div>
            
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete={isLogin ? "current-password" : "new-password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Inserisci la tua password"
              />
            </div>

            {!isLogin && (
              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                  Conferma Password
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Conferma la tua password"
                />
              </div>
            )}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="flex">
                <div className="flex-shrink-0">
                  <span className="text-red-400">⚠️</span>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {isLogin ? 'Accesso in corso...' : 'Registrazione in corso...'}
                </div>
              ) : (
                <>
                  {isLogin ? 'Accedi' : 'Registrati'}
                  <span className="ml-2">{isLogin ? '🔓' : '🚀'}</span>
                </>
              )}
            </button>
          </div>

          <div className="text-center">
            <p className="text-gray-600">
              {isLogin ? 'Non hai ancora un account?' : 'Hai già un account?'}
              {' '}
              <Link 
                href={isLogin ? '/auth/register' : '/auth/login'}
                className="font-medium text-blue-600 hover:text-blue-500 transition-colors"
              >
                {isLogin ? 'Registrati ora' : 'Accedi qui'}
              </Link>
            </p>
          </div>

          <div className="text-center">
            <Link 
              href="/"
              className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              ← Torna alla homepage
            </Link>
          </div>
        </form>

        {/* Features reminder */}
        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
          <h3 className="text-sm font-semibold text-blue-800 mb-2">
            Cosa ottieni con ChatMap:
          </h3>
          <ul className="text-xs text-blue-700 space-y-1">
            <li>🧠 Memoria intelligente delle conversazioni</li>
            <li>🗺️ Mappe concettuali interattive</li>
            <li>⚡ AI personalizzata sul tuo stile di pensiero</li>
            <li>🎯 Risposte +35% più rilevanti</li>
          </ul>
        </div>
      </div>
    </div>
  );
}