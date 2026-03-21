FROM ghcr.io/astral-sh/uv:trixie-slim AS builder

WORKDIR /app
COPY uv.lock /app
RUN uv init -p 3.13.11 --name src && uv sync --no-dev

FROM docker.io/python:3.13-slim AS runner
RUN mkdir /website

WORKDIR /app
COPY . /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/.venv/lib/python3.13/site-packages
RUN pip install gunicorn
EXPOSE 8080
ENV PYTHONUNBUFFERED=TRUE
CMD ["gunicorn", "--enable-stdio-inheritance", "-w", "2", "-b", "unix:/website/hackspace_storage.sock", "hackspace_storage:create_app()"]
