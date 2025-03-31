# Base image with Node.js LTS (includes npm)
FROM node:lts-alpine

# Set working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json (important!)
# These define your dependencies
COPY package*.json ./

# Install dependencies using npm ci (clean install - generally preferred in Docker)
# If 'npm ci' causes issues, fall back to 'npm install'
RUN npm ci

# Copy the rest of the application code from your host machine's
# 'frontend' directory into the container's '/app' directory
COPY . .

# Expose the port Vite development server runs on
EXPOSE 5173

# Command to run the development server when the container starts
# The '-- --host' part ensures Vite listens on all network interfaces
# within the container, making it accessible from outside (via mapped ports)
CMD ["npm", "run", "dev", "--", "--host"]
