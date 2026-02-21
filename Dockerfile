# Use a imagem oficial do Playwright para Python (já vem com navegadores e dependências)
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos de requisitos e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala apenas o Chromium (para economizar espaço)
RUN playwright install chromium

# Copia o resto do código
COPY . .

# Define a porta padrão (o Render sobrescreve isso com a variável PORT)
ENV PORT 5000

# Inicia a aplicação usando gunicorn
# Usamos a variável $PORT do sistema
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app:app --timeout 600"]
