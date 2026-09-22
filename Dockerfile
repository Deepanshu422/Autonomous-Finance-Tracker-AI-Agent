FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install curl and Node.js
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Security: Run as non-root user
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# 1. Copy ONLY dependency files first to leverage Docker layer caching
COPY --chown=user requirements.txt .
COPY --chown=user whatsapp-bridge/package.json whatsapp-bridge/

# 2. Install dependencies before copying code
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt
RUN cd whatsapp-bridge && npm install

# 3. Copy the rest of the application code
COPY --chown=user . $HOME/app/

EXPOSE 7860

CMD ["bash", "start.sh"]