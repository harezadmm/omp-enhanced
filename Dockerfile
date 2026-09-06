FROM node:18-slim

# Install Git
RUN apt-get update && \
    apt-get install -y git curl && \
    rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy package files
COPY . .

# Install OMP and dependencies
RUN bash -c "set -e; \
    git clone https://github.com/secretflow/omp.git; \
    cd omp; \
    npm install --production; \
    cd ..; \
    mkdir -p /root/.omp/skills /root/.omp/prompts; \
    cp -r skills/* /root/.omp/skills/ || true; \
    cp AGENTS.md /root/.omp/prompts/system.md || true"

WORKDIR /app/omp

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# Start server
CMD ["npm", "start"]
