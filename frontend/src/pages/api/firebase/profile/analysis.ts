import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';
  
  try {
    const url = `${backendUrl}/api/firebase/profile/analysis`;
    console.log('🔄 Proxying profile analysis request to:', url);

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': req.headers.authorization || '',
      },
      signal: AbortSignal.timeout(30000),
    });

    console.log('✅ Profile analysis response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Profile analysis error:', response.status, errorText);
      return res.status(response.status).json({ 
        error: `Backend error: ${response.status}`,
        details: errorText 
      });
    }

    const data = await response.json();
    res.status(200).json(data);
  } catch (error) {
    console.error('❌ Profile analysis proxy error:', error);
    res.status(500).json({ 
      error: 'Proxy error', 
      details: error instanceof Error ? error.message : 'Unknown error' 
    });
  }
}