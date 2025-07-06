/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
  // Handle CORS preflight requests
  if (event.request.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Methods': 'POST, GET, OPTIONS, DELETE',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  }

  const response = await resolve(event);

  // Apply CORS headers to actual responses
  response.headers.set('Access-Control-Allow-Origin', '*');

  return response;
}
