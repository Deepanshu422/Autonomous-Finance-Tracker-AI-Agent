FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system utilities, Python runtime, Node.js, and headless Chromium
RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    chromium-browser \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face enforces non-root execution under UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy application code with non-root ownership
COPY --chown=user . $HOME/app/

# Install dependencies
RUN pip3 install --no-cache-dir -r requirements.txt
RUN cd whatsapp-bridge && npm install

EXPOSE 7860

CMD ["bash", "start.sh"]
