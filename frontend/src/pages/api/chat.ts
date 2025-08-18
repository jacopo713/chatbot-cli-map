import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://chatbot-cli-map-production.up.railway.app';
  
  try {
    console.log('🔄 Proxying request to:', `${backendUrl}/api/chat`);
    console.log('🔄 Request body:', JSON.stringify(req.body, null, 2));

    const response = await fetch(`${backendUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/plain, */*',
      },
      body: JSON.stringify(req.body),
      signal: AbortSignal.timeout(60000), // 60 second timeout
    });

    console.log('✅ Backend response status:', response.status);
    console.log('✅ Backend response headers:', Object.fromEntries(response.headers.entries()));

    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Backend error:', response.status, errorText);
      return res.status(response.status).json({ 
        error: `Backend error: ${response.status}`,
        details: errorText 
      });
    }

    // Set headers for streaming response
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('X-Accel-Buffering', 'no');

    // Stream the response from Railway to client
    if (response.body) {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        res.write(chunk);
      }
    }

    res.end();
  } catch (error) {
    console.error('❌ Proxy error:', error);
    res.status(500).json({ 
      error: 'Proxy error', 
      details: error instanceof Error ? error.message : 'Unknown error' 
    });
  }
}

// Configure body parser for larger requests
export const config = {
  api: {
    bodyParser: {
      sizeLimit: '10mb',
    },
  },
};