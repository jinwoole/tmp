# Stage 1: Build the application
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package.json and package-lock.json first to leverage Docker cache
COPY package*.json ./

# Install all dependencies, including devDependencies needed for the build
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build the SvelteKit application for a Node.js environment
RUN npm run build

# Stage 2: Create the final production image
FROM node:18-alpine

WORKDIR /app

# Copy package.json to ensure 'type: module' is set
COPY --from=builder /app/package.json .

# Install only production dependencies
RUN npm install --omit=dev

# Copy the built SvelteKit server and the custom server wrapper
COPY --from=builder /app/build .
COPY --from=builder /app/src/lib/server/index.js ./custom-server.js

# Expose the port the app will run on
EXPOSE 3000

# Set environment variables for the SvelteKit server
ENV HOST=0.0.0.0
ENV PORT=3000

# Start the custom server which wraps the SvelteKit app and Socket.IO
CMD ["node", "custom-server.js"]
