# Kung Fu Chess -- server container.
#
# Only the server needs to run in a container: it has no display, so
# no pygame/SDL dependency at all (verified: importing server.app pulls
# in kfchess.input for GameEngine's ClickController, but never
# kfchess.gui or pygame itself). requirements-server.txt reflects that
# -- just `websockets`; everything else the server uses (sqlite3,
# asyncio, hashlib, hmac, logging, json) is the standard library.
#
# The graphical client (client_main.py) is not containerized here --
# it opens a real window, which needs a display on whatever machine
# runs it. Run it locally with `python client_main.py ws://<host>:8765`
# pointed at this container.
FROM python:3.12-slim

WORKDIR /app

COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

COPY kfchess/ ./kfchess/
COPY protocol/ ./protocol/
COPY server/ ./server/
COPY server_main.py .

# SQLite file lives on a volume (see docker-compose.yml and
# k8s/kfchess.yaml) so user accounts/ratings survive a container
# restart. The server runs as an unprivileged user that owns /data.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin kfchess \
    && mkdir -p /data \
    && chown kfchess:kfchess /data
USER 10001

EXPOSE 8765

CMD ["python", "server_main.py", "--host", "0.0.0.0", "--port", "8765", "--db", "/data/kfchess_server.db"]
