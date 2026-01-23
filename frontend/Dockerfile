# AURA-NOTES-MANAGER Frontend Dockerfile
# Container image for the React + Vite frontend.

# Installs frontend dependencies, builds the app, and serves the preview
# server on port 3001 for the Notes Manager UI.
# Built from the frontend folder context.

# @see: AURA-NOTES-MANAGER/docker-compose.yml - Service build configuration
# @note: Uses Node 20 to align with Vite toolchain

FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . ./
RUN npm run build

EXPOSE 3001

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3001"]
