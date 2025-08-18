import { useState } from 'react';

export default function TestAPI() {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const sendMessage = async () => {
    if (!message.trim()) return;
    
    setLoading(true);
    setError('');
    setResponse('');

    const endpoint = '/api/chat'; // Use Next.js API proxy
    
    const payload = {
      message: message,
      context_files: [],
      project_name: null,
      concept_map_context: null,
      active_concept_map_id: null,
      history: [],
      conversation_id: "test-" + Date.now(),
      user_id: "test-user"
    };

    console.log('🚀 TEST ENDPOINT:', endpoint);
    console.log('🚀 TEST PAYLOAD:', payload);

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/plain, */*',
          'Cache-Control': 'no-cache',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(30000), // 30 second timeout
      });

      console.log('🚀 RESPONSE STATUS:', res.status);
      console.log('🚀 RESPONSE HEADERS:', Object.fromEntries(res.headers.entries()));

      if (!res.ok) {
        const errorText = await res.text();
        console.log('🚀 ERROR BODY:', errorText);
        throw new Error(`HTTP ${res.status}: ${errorText}`);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let result = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          result += chunk;
          setResponse(result);
        }
      }
    } catch (err: any) {
      console.error('🚀 ERROR:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">API Test Page</h1>
        
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Test Chat API</h2>
          
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Message:</label>
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2"
              placeholder="Enter your message..."
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            />
          </div>

          <button
            onClick={sendMessage}
            disabled={loading || !message.trim()}
            className="bg-blue-500 text-white px-4 py-2 rounded disabled:bg-gray-400"
          >
            {loading ? 'Sending...' : 'Send Message'}
          </button>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            <strong>Error:</strong> {error}
          </div>
        )}

        {response && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-6">
            <strong>Response:</strong>
            <pre className="mt-2 whitespace-pre-wrap">{response}</pre>
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-2">Debug Info</h3>
          <p><strong>Backend URL:</strong> {process.env.NEXT_PUBLIC_BACKEND_URL || 'https://chatbot-cli-map-production.up.railway.app'}</p>
          <p><strong>Current Time:</strong> {new Date().toISOString()}</p>
          <p className="mt-4 text-sm text-gray-600">Check browser console for detailed logs</p>
        </div>

        <div className="mt-6">
          <a 
            href="/chat" 
            className="text-blue-500 hover:text-blue-700 underline"
          >
            ← Back to main chat
          </a>
        </div>
      </div>
    </div>
  );
}