FROM python:3.12-slim

ENV APP_NAME=com_gemini_ai_example.controller.api_controller
ENV PORT=8080

WORKDIR /app

COPY dist/*.whl /app/dist/
COPY src/com_gemini_ai_example /app/src/com_gemini_ai_example

# Install uvicorn and application dependencies
RUN pip install uvicorn /app/dist/*.whl

EXPOSE 8080

# Start the application
CMD ["sh", "-c", "uvicorn ${APP_NAME}:app --host 0.0.0.0 --port ${PORT}"]
