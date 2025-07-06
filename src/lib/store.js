import { writable } from 'svelte/store';
import io from 'socket.io-client';

export const events = writable([]);
export const vms = writable(new Map());

const socket = io();

socket.on('connect', () => {
  console.log('Connected to WebSocket server');
});

socket.on('request', (event) => {
  console.log('Received request event:', event); // Debugging log
  events.update(currentEvents => [...currentEvents, event]);

  // Update VM stats
  vms.update(currentVms => {
    const existingVm = currentVms.get(event.vmId);
    const requests = (existingVm?.requests || 0) + 1;

    // Create a new, complete VM object to ensure reactivity
    const newVm = {
      id: event.vmId,
      ip: event.vmId, // The VM ID is the IP address
      requests: requests,
      ips: new Set(existingVm?.ips).add(event.ip),
      status: 'active',
      // Calculate load based on requests. For demo, let's cap at 20 for 100%.
      load: Math.min(100, (requests / 20) * 100),
    };

    currentVms.set(event.vmId, newVm);
    return new Map(currentVms); // Return a new map to trigger Svelte's reactivity
  });
});

socket.on('disconnect', () => {
  console.log('Disconnected from WebSocket server');
});
