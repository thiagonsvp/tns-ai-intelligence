# Usar a imagem oficial sincronizada com a versão mais recente do Playwright
FROM mcr.microsoft.com/playwright/python:v1.50.0-jammy

# Define o diretório de trabalho
WORKDIR /app

# Instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código fonte
COPY . .

# Variável de ambiente para a porta
ENV PORT 5000

# Executa com Gunicorn, aumentando o tempo de resposta (timeout)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app:app --workers 1 --threads 8 --timeout 0"]
