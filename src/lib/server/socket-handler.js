import { Server } from 'socket.io';

export function createSocketServer(server) {
  // Store the io instance in the global scope to ensure it's a singleton
  // especially in a Vite dev environment with HMR.
  const io = new Server(server);
  globalThis.io = io;

  io.on('connection', (socket) => {
    console.log('A client connected');
    socket.emit('message', 'Welcome to the load balancer visualization!');

    socket.on('disconnect', () => {
      console.log('A client disconnected');
    });
  });

  return io;
}
