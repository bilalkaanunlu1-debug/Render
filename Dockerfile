FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MEGA_DB_PATH=/data/mega.db MEGA_COOKIE_SECURE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt brotli
COPY bundle/ /app/bundle/
COPY unpack_bundle.py generate_icons.py patch_owner_login.py patch_x_integration.py x_list_sync.py x_free_import.py patch_x_free_import.py ./
RUN python unpack_bundle.py && python patch_owner_login.py && python patch_x_integration.py && python patch_x_free_import.py && python generate_icons.py && rm -rf /app/bundle
RUN mkdir -p /data
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
