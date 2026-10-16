FROM node:22-bookworm-slim AS ui
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY demo/ ./demo/
COPY scripts/start_react.sh ./scripts/start_react.sh
COPY --from=ui /build/dist ./frontend/dist/
RUN useradd --create-home nexus && mkdir -p /app/storage && chown -R nexus:nexus /app
USER nexus
ENV PROJECT07_DB_PATH=/app/storage/project07.sqlite3 PROJECT07_VAULT_DIR=/app/storage/private_vault PROJECT07_REQUIRE_GATES=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["bash", "scripts/start_react.sh"]
