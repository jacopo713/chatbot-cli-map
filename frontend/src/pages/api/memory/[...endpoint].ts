import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { endpoint } = req.query;
  const endpointPath = Array.isArray(endpoint) ? endpoint.join('/') : endpoint;
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://chatbot-cli-map-production.up.railway.app';
  
  try {
    const url = `${backendUrl}/api/memory/${endpointPath}`;
    console.log('🔄 Proxying memory request to:', url);

    const response = await fetch(url, {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: req.method !== 'GET' && req.method !== 'DELETE' ? JSON.stringify(req.body) : undefined,
      signal: AbortSignal.timeout(30000),
    });

    console.log('✅ Memory response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Memory error:', response.status, errorText);
      return res.status(response.status).json({ 
        error: `Backend error: ${response.status}`,
        details: errorText 
      });
    }

    const data = await response.json();
    res.status(200).json(data);
  } catch (error) {
    console.error('❌ Memory proxy error:', error);
    res.status(500).json({ 
      error: 'Proxy error', 
      details: error instanceof Error ? error.message : 'Unknown error' 
    });
  }
}