import { networkInterfaces } from 'os';

// Helper to get the primary local IP address of the server
function getLocalIp() {
  const nets = networkInterfaces();
  for (const name of Object.keys(nets)) {
    for (const net of nets[name]) {
      // Skip over non-IPv4 and internal (i.e. 127.0.0.1) addresses
      if (net.family === 'IPv4' && !net.internal) {
        return net.address;
      }
    }
  }
  return '127.0.0.1'; // Fallback for environments where it's not found
}

const vmId = getLocalIp();

/** @type {import('./$types').RequestHandler} */
export function GET(event) {
  const eventData = {
    type: 'request_received',
    vmId: vmId, // Use the server's IP as the VM ID
    ip: event.getClientAddress(),
    timestamp: Date.now(),
  };

  // Access the global io instance and emit the event
  if (globalThis.io) {
    globalThis.io.emit('request', eventData);
    return new Response(JSON.stringify({ success: true, vmId: vmId }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } else {
    // Failsafe if the socket server isn't running
    return new Response(JSON.stringify({ error: 'Socket server not available' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
