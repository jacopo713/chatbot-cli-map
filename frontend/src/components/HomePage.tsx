"use client";

import { useState } from 'react';
import Link from 'next/link';

interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
  benefits: string[];
}

function FeatureCard({ icon, title, description, benefits }: FeatureCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow duration-300 border border-gray-100">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-xl font-bold text-gray-800 mb-3">{title}</h3>
      <p className="text-gray-600 mb-4">{description}</p>
      <ul className="space-y-2">
        {benefits.map((benefit, index) => (
          <li key={index} className="flex items-center text-sm text-gray-700">
            <span className="text-green-500 mr-2">✓</span>
            {benefit}
          </li>
        ))}
      </ul>
    </div>
  );
}

interface BenefitItemProps {
  icon: string;
  title: string;
  description: string;
}

function BenefitItem({ icon, title, description }: BenefitItemProps) {
  return (
    <div className="flex items-start space-x-4 p-4 bg-blue-50 rounded-lg">
      <div className="text-2xl">{icon}</div>
      <div>
        <h4 className="font-semibold text-gray-800">{title}</h4>
        <p className="text-gray-600 text-sm">{description}</p>
      </div>
    </div>
  );
}

export default function HomePage() {
  const [activeFeature, setActiveFeature] = useState(0);

  const features = [
    {
      icon: "🧠",
      title: "Memoria Ibrida Intelligente",
      description: "Sistema di memoria avanzato che ricorda le tue conversazioni e impara dal tuo stile di pensiero.",
      benefits: [
        "Classifica automaticamente l'importanza dei messaggi",
        "Buffer scorrevole per contesto immediato",
        "Riassunti automatici delle conversazioni",
        "Storage multi-livello con TTL intelligente"
      ]
    },
    {
      icon: "🗺️",
      title: "Mappe Concettuali Interattive", 
      description: "Crea e gestisci mappe concettuali che l'AI utilizza per comprendere il tuo modo di ragionare.",
      benefits: [
        "13 tipi di relazioni semantiche",
        "Editor drag-and-drop intuitivo",
        "Salvataggio automatico su Firebase",
        "Analisi pattern di pensiero in tempo reale"
      ]
    },
    {
      icon: "🎯",
      title: "Personalizzazione AI Avanzata",
      description: "L'intelligenza artificiale si adatta al tuo stile di pensiero attraverso l'analisi delle mappe concettuali.",
      benefits: [
        "Rileva automaticamente domini di expertise",
        "Adatta risposte al tuo stile cognitivo",
        "Context enhancement basato sui tuoi pattern",
        "Miglioramento continuo delle prestazioni"
      ]
    },
    {
      icon: "⚡",
      title: "Ragionamento Potenziato",
      description: "Sistema di reasoning che combina memoria conversazionale e strutture cognitive per risposte superiori.",
      benefits: [
        "Catene causali dal tuo modo di pensare",
        "Cluster concettuali personalizzati",
        "Context enrichment automatico",
        "+35% di rilevanza nelle risposte"
      ]
    }
  ];

  const benefits = [
    {
      icon: "🚀",
      title: "Prestazioni Superiori",
      description: "Risposte +35% più rilevanti grazie all'analisi del tuo stile di pensiero"
    },
    {
      icon: "🔒",
      title: "Privacy e Sicurezza",
      description: "I tuoi dati sono protetti e le mappe concettuali rimangono private"
    },
    {
      icon: "📈",
      title: "Apprendimento Continuo",
      description: "Il sistema migliora automaticamente man mano che crei nuove mappe"
    },
    {
      icon: "🎨",
      title: "Interfaccia Intuitiva",
      description: "Design moderno e user-friendly per un'esperienza ottimale"
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <div className="text-2xl">🤖</div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                ChatMap
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <Link 
                href="/auth/login"
                className="text-gray-600 hover:text-gray-800 font-medium transition-colors"
              >
                Accedi
              </Link>
              <Link 
                href="/auth/register"
                className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors"
              >
                Registrati
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <div className="mb-8">
            <h2 className="text-5xl font-bold text-gray-900 mb-6">
              Il Chatbot che{' '}
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Impara
              </span>{' '}
              dal Tuo Modo di Pensare
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
              Combina memoria intelligente, mappe concettuali interattive e AI personalizzata 
              per offrire un'esperienza conversazionale completamente nuova.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            <Link 
              href="/auth/register"
              className="bg-blue-600 text-white px-8 py-4 rounded-xl font-semibold text-lg hover:bg-blue-700 transition-colors shadow-lg hover:shadow-xl"
            >
              Inizia Gratuitamente 🚀
            </Link>
            <Link 
              href="#features"
              className="border-2 border-gray-300 text-gray-700 px-8 py-4 rounded-xl font-semibold text-lg hover:border-gray-400 transition-colors"
            >
              Scopri le Funzionalità
            </Link>
          </div>

          {/* Demo Video/Screenshot Placeholder */}
          <div className="max-w-4xl mx-auto">
            <div className="bg-gradient-to-r from-blue-100 to-purple-100 rounded-2xl p-8 shadow-xl">
              <div className="bg-white rounded-xl p-6 shadow-lg">
                <div className="text-6xl mb-4">🧠🗺️💬</div>
                <h3 className="text-2xl font-bold text-gray-800 mb-4">
                  Sistema Integrato AI + Mappe Concettuali
                </h3>
                <p className="text-gray-600">
                  Visualizza come l'AI analizza le tue mappe concettuali per personalizzare ogni risposta
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Funzionalità Innovative
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Ogni componente è progettato per creare un'esperienza AI personalizzata e intelligente
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 mb-16">
            {features.map((feature, index) => (
              <FeatureCard
                key={index}
                icon={feature.icon}
                title={feature.title}
                description={feature.description}
                benefits={feature.benefits}
              />
            ))}
          </div>

          {/* Interactive Feature Demo */}
          <div className="bg-gray-50 rounded-2xl p-8">
            <h3 className="text-2xl font-bold text-center text-gray-800 mb-8">
              Come Funziona il Sistema Potenziato
            </h3>
            
            <div className="grid md:grid-cols-3 gap-6">
              <div className="text-center p-6">
                <div className="text-4xl mb-4">1️⃣</div>
                <h4 className="font-bold text-lg mb-2">Crei Mappe Concettuali</h4>
                <p className="text-gray-600">Disegni le tue idee e connessioni usando l'editor interattivo</p>
              </div>
              
              <div className="text-center p-6">
                <div className="text-4xl mb-4">2️⃣</div>
                <h4 className="font-bold text-lg mb-2">L'AI Analizza i Pattern</h4>
                <p className="text-gray-600">Il sistema estrae il tuo stile di pensiero e domini di expertise</p>
              </div>
              
              <div className="text-center p-6">
                <div className="text-4xl mb-4">3️⃣</div>
                <h4 className="font-bold text-lg mb-2">Risposte Personalizzate</h4>
                <p className="text-gray-600">Ogni conversazione è arricchita con il tuo modo di ragionare</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-20 bg-gradient-to-br from-blue-50 to-purple-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Vantaggi per l'Utente
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Scopri come il nostro sistema migliora concretamente la tua esperienza
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {benefits.map((benefit, index) => (
              <BenefitItem
                key={index}
                icon={benefit.icon}
                title={benefit.title}
                description={benefit.description}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl font-bold text-gray-900 mb-16">
            Risultati Misurabili
          </h2>
          
          <div className="grid md:grid-cols-4 gap-8">
            <div className="p-6">
              <div className="text-4xl font-bold text-blue-600 mb-2">+35%</div>
              <div className="text-gray-600">Rilevanza Risposte</div>
            </div>
            <div className="p-6">
              <div className="text-4xl font-bold text-green-600 mb-2">13</div>
              <div className="text-gray-600">Tipi di Relazioni</div>
            </div>
            <div className="p-6">
              <div className="text-4xl font-bold text-purple-600 mb-2">∞</div>
              <div className="text-gray-600">Mappe Concettuali</div>
            </div>
            <div className="p-6">
              <div className="text-4xl font-bold text-orange-600 mb-2">6h</div>
              <div className="text-gray-600">Cache Intelligente</div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-purple-600">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl font-bold text-white mb-6">
            Pronto a Trasformare le Tue Conversazioni AI?
          </h2>
          <p className="text-xl text-blue-100 mb-8">
            Unisciti alla nuova generazione di chatbot intelligenti che si adattano al tuo modo di pensare
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link 
              href="/auth/register"
              className="bg-white text-blue-600 px-8 py-4 rounded-xl font-semibold text-lg hover:bg-gray-100 transition-colors shadow-lg"
            >
              Registrati Ora - È Gratis! 🎉
            </Link>
            <Link 
              href="/auth/login"
              className="border-2 border-white text-white px-8 py-4 rounded-xl font-semibold text-lg hover:bg-white hover:text-blue-600 transition-colors"
            >
              Hai già un account? Accedi
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="flex items-center justify-center space-x-3 mb-4">
              <div className="text-2xl">🤖</div>
              <h3 className="text-xl font-bold">ChatMap</h3>
            </div>
            <p className="text-gray-400 mb-6">
              Il futuro delle conversazioni AI personalizzate
            </p>
            <div className="flex justify-center space-x-6 text-gray-400">
              <span>🧠 Memoria Intelligente</span>
              <span>•</span>
              <span>🗺️ Mappe Concettuali</span>
              <span>•</span>
              <span>⚡ AI Personalizzata</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}