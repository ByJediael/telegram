FROM python:3.12-slim

# Garantir saída de logs em tempo real sem buffer no Docker/Easypanel
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

# Copiar e instalar dependências em cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código-fonte
COPY . .

# Expor a porta 8000 para o Easypanel
EXPOSE 8000

# Comando para rodar o bot e o painel web
CMD ["python", "-u", "main.py"]
