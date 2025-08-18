import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://chatbot-cli-map-production.up.railway.app';
  
  try {
    const url = `${backendUrl}/api/firebase/concept-maps`;
    console.log('🔄 Proxying concept maps request to:', url);

    const response = await fetch(url, {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': req.headers.authorization || '',
      },
      body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined,
      signal: AbortSignal.timeout(30000),
    });

    console.log('✅ Concept maps response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Concept maps error:', response.status, errorText);
      return res.status(response.status).json({ 
        error: `Backend error: ${response.status}`,
        details: errorText 
      });
    }

    const data = await response.json();
    res.status(200).json(data);
  } catch (error) {
    console.error('❌ Concept maps proxy error:', error);
    res.status(500).json({ 
      error: 'Proxy error', 
      details: error instanceof Error ? error.message : 'Unknown error' 
    });
  }
}