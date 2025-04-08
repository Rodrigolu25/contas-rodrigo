# Usa uma imagem base do Python
FROM python:3.8-slim 

# Instala dependências do sistema (incluindo o wkhtmltopdf para gerar PDFs)
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Cria e define o diretório de trabalho
WORKDIR /app

# Copia os arquivos necessários
COPY . .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando para rodar o aplicativo
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]