# Google Places Scraper Pro

Um sistema robusto para buscar, filtrar e exportar leads do Google Maps/Google Meu Negócio, focado em estabelecimentos comerciais com telefones válidos.

## 🚀 Tecnologias

- **Backend:** Python + Flask
- **Frontend:** HTML5, Vanilla JavaScript, Tailwind CSS
- **API:** Google Places API (New)
- **Estilização:** Design Moderno, Dark Mode, Responsivo

## 🛠️ Como Instalar e Rodar

### 1. Obtenha sua chave da API do Google
1. Vá ao [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um novo projeto.
3. No menu lateral, vá em **APIs e Serviços** > **Biblioteca**.
4. Procure por **"Places API"** e ative-a (certifique-se de que é a versão "New").
5. Vá em **Credenciais** e crie uma **Chave de API (API Key)**.
6. Habilite o faturamento (Billing) no seu projeto (necessário para APIs do Google Maps, embora haja uma cota gratuita mensal).

### 2. Configure o projeto localmente
1. Clone ou baixe este diretório.
2. Crie um arquivo chamado `.env` na raiz do projeto baseado no `.env.example`:
   ```env
   GOOGLE_PLACES_API_KEY=SuaChaveAqui
   ```
3. Crie um ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
4. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Rode a aplicação
```bash
python app.py
# Ou usando o Flask CLI:
# flask run
```
Acesse `http://127.0.0.1:5000` no seu navegador.

## ✨ Funcionalidades

- **Busca Avançada:** Pesquisa por nome/especialidade e localização.
- **Validação Automática:** Filtra apenas estabelecimentos com telefone e valida o formato brasileiro (DDD + número).
- **Badge de Qualidade:** Identificação visual de contatos verificados.
- **Exportação CSV:** Baixe todos os leads filtrados para usar em CRM ou planilhas.
- **Interface Mobile-First:** Funciona perfeitamente em celulares (botão "Ligar" integrado).
- **Filtro em Tempo Real:** Refine os resultados carregados instantaneamente.
- **Dark Mode:** Conforto visual automático ou manual.

## 📝 Notas de Implementação

- Os resultados são armazenados temporariamente em memória para a função de exportação.
- A aplicação utiliza o endpoint `places:searchText` da nova Google Places API.
- Ordenação automática por melhor avaliação (Rating).

---
Desenvolvido com ❤️ usando Antigravity.
