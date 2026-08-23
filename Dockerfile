FROM python:3.12-slim

# Diretório de trabalho no contêiner
WORKDIR /app

# Copiar e instalar dependências em cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código-fonte
COPY . .

# Expor a porta 8000 para o Easypanel
EXPOSE 8000

# Comando para rodar o bot e o painel web
CMD ["python", "main.py"]
