FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
RUN pip install --no-cache-dir -e .

ENV ARCP_PROFILE=local-demo
ENV ARCP_MODE=mock
ENV ARCP_STATE_DIR=/app/state
ENV ARCP_REPORTS_DIR=/app/reports

CMD ["python", "-m", "ai_release_control_plane.cli", "demo-run", "--scenario", "success", "--profile", "local-demo"]
