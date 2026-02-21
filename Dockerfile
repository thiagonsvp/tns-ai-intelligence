# Use a imagem base mais leve do Playwright (já tem tudo pronto)
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

# Define o diretório de trabalho
WORKDIR /app

# Instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# O Playwright já vem instalado na imagem base, 
# só precisamos garantir que o sistema está pronto.
# Não reinstalamos para ganhar tempo e espaço.

# Copia o código fonte
COPY . .

# Variável de ambiente para a porta
ENV PORT 5000

# Executa com Gunicorn, aumentando o tempo de resposta (timeout)
# Nota: A Render Free ainda cortará conexões em 30s, o timeout aqui é do worker.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app:app --workers 1 --threads 8 --timeout 0"]
