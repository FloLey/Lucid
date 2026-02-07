# Lucid Frontend - Node 22 LTS
FROM node:22-alpine

WORKDIR /app

# Install dependencies first (better caching)
COPY package*.json ./
RUN npm install

# Copy application code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run dev server with host flag for container networking
CMD ["npm", "run", "dev", "--", "--host"]
