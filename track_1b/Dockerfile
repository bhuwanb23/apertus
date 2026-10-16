FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY technical_report.md ./technical_report.md
COPY SwissRealityCheck_Report.pdf ./SwissRealityCheck_Report.pdf
COPY README.md ./README.md

ENV PYTHONUNBUFFERED=1
CMD ["python", "src/run.py"]
