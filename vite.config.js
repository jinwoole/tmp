import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { createSocketServer } from './src/lib/server/socket-handler.js';

// Custom Vite plugin to integrate the WebSocket server
const webSocketPlugin = {
  name: 'webSocketServer',
  configureServer(server) {
    if (server.httpServer) {
        createSocketServer(server.httpServer);
    }
  }
};

export default defineConfig({
	plugins: [tailwindcss(), sveltekit(), webSocketPlugin]
});
