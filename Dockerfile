# Stage 1: Build dell'ambiente virtuale Python
FROM python:3.12-slim AS builder

# Creiamo il venv senza bisogno di installare TeX qui!
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY pyproject.toml README.md ./
COPY notion2tex ./notion2tex

# Installazione del pacchetto
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .


# Stage 2: Immagine finale di runtime
FROM python:3.12-slim
ARG TARGETARCH
ARG PANDOC_VERSION=3.10.1

# Installazione dipendenze di sistema minime.
# Rimossi: texlive-fonts-extra (troppo pesante) e duplicati inutili.
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-latex-extra \
    texlive-plain-generic \
    cm-super \
    lmodern \
    curl \
    ca-certificates \
    && curl -fsSL -o /tmp/pandoc.deb \
       "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-1-${TARGETARCH}.deb" \
    && dpkg -i /tmp/pandoc.deb \
    && rm -f /tmp/pandoc.deb \
    && apt-get purge -y curl ca-certificates \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copia l'ambiente virtuale e il codice sorgente
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --from=builder /build/notion2tex ./notion2tex
COPY pyproject.toml README.md LICENSE ./

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Verifica l'installazione
RUN notion2tex --check

ENTRYPOINT ["notion2tex"]
CMD ["--help"]