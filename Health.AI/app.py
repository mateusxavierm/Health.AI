from flask import Flask, render_template, request, redirect, url_for, jsonify, session, make_response
import json
import os
from datetime import datetime
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
# Todas as importações implementadas no projeto

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Configuração da API Gemini
GOOGLE_API_KEY = 'AIzaSyDWTQyq9U1BbSjE6OJovKhis5LAM3UELg8'
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# --- Funções para interação com o modelo Gemini ---
def is_health_related(question, generative_model):
    """Verifica se a pergunta é sobre saúde humana, medicina, bem-estar, etc.
    Responde 'sim' ou 'não' de forma mais estrita."""
    classification_prompt = f"""
    A pergunta a seguir é **exclusivamente e diretamente** sobre saúde humana, medicina, doenças, bem-estar, tratamentos ou sintomas?
    Responda APENAS com 'sim' ou 'não' em letras minúsculas. Não adicione nenhuma outra palavra ou pontuação.

    Pergunta: "{question}"
    """
    try:
        response = generative_model.generate_content(classification_prompt)
        answer = response.text.strip().lower()
        return answer == 'sim'
    except Exception as e:
        print(f"[Erro na classificação do tópico]: {e}")
        return False

def get_health_info_in_topics(question, generative_model):
    """Obtém informações de saúde do modelo, focando apenas em saúde humana."""
    health_prompt = f"""
    Como um assistente focado **APENAS em saúde humana**, forneça informações claras e concisas sobre o seguinte tópico: "{question}".
    Organize a resposta em apenas um paragrafo conciso, tente usar entre no mínimo 70 palavras e no máximo 500, e responda resumidamente.
    **NÃO discuta tópicos fora da área de saúde humana.**, não gere textos com asteriscos "**texto exemplo**".
      Se a pergunta for muito genérica, adapte a resposta para um contexto de saúde ou indique a limitação.
    """
    try:
        response = generative_model.generate_content(health_prompt)
        return response.text
    except Exception as e:
        print(f"[Erro ao gerar conteúdo de saúde]: {e}")
        return "Desculpe, ocorreu um erro ao processar sua solicitação."

def get_non_health_response():
    """Retorna uma mensagem fixa quando a pergunta não é de saúde."""
    return "Desculpe, isso não está relacionado a saúde, não posso ajudar com isso."
# --- Fim das Funções para interação com o modelo Gemini ---

# Arquivos JSON
USERS_DB = 'database.json'
CHAT_HISTORY_DB = 'chat_history.json'

# Inicializar arquivos JSON se não existirem
if not os.path.exists(USERS_DB):
    with open(USERS_DB, 'w') as f:
        json.dump({'users': []}, f)

if not os.path.exists(CHAT_HISTORY_DB):
    with open(CHAT_HISTORY_DB, 'w') as f:
        json.dump({'chats': []}, f)

# Rotas
@app.route('/')
def home():
    # Se o usuário já estiver logado, redireciona diretamente para o chat
    if 'user_email' in session:
        return redirect(url_for('chat'))
    # Se não estiver logado, renderiza a tela inicial (start.html)
    return render_template('start.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with open(USERS_DB, 'r') as f:
            data = json.load(f)

        for user in data['users']:
            if user['email'] == email and user['password'] == password:
                session['user_email'] = email
                return redirect(url_for('chat'))

        return render_template('login.html', error='Credenciais inválidas')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with open(USERS_DB, 'r+') as f:
            data = json.load(f)

            # Verificar se o usuário já existe
            for user in data['users']:
                if user['email'] == email:
                    return render_template('register.html', error='Email já cadastrado')

            # Adicionar novo usuário
            data['users'].append({
                'email': email,
                'password': password
            })

            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_message = request.form['message']

        # Obter resposta do Gemini (AJUSTADO)
        if is_health_related(user_message, model):
            bot_response = get_health_info_in_topics(user_message, model)
        else:
            # Chama a nova função que retorna uma mensagem fixa
            bot_response = get_non_health_response()

        # Salvar no histórico
        chat_entry = {
            'user': session['user_email'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'question': user_message,
            'answer': bot_response
        }

        with open(CHAT_HISTORY_DB, 'r+') as f:
            data = json.load(f)
            data['chats'].append(chat_entry)
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

        return jsonify({
            'question': user_message,
            'answer': bot_response
        })

    # Carregar histórico do usuário
    with open(CHAT_HISTORY_DB, 'r') as f:
        data = json.load(f)

    user_chats = [chat for chat in data['chats'] if chat['user'] == session['user_email']]

    return render_template('chat.html', chats=user_chats)

@app.route('/download_chat/<int:chat_index>')
def download_chat(chat_index):
    if 'user_email' not in session:
        return redirect(url_for('login'))

    with open(CHAT_HISTORY_DB, 'r') as f:
        data = json.load(f)

    # Filtra apenas os chats do usuário atual
    user_chats = [chat for chat in data['chats'] if chat['user'] == session['user_email']]

    if chat_index < 0 or chat_index >= len(user_chats):
        return "Conversa não encontrada", 404

    chat = user_chats[chat_index]

    # Criar PDF em memória
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    # Configurações do PDF
    p.setFont("Helvetica", 12)
    y = 750  # Posição vertical inicial
    margin = 50  # Margem esquerda
    right_margin = 550  # Margem direita (largura útil)
    line_height = 15  # Espaçamento entre linhas

    # Função para quebrar texto em múltiplas linhas
    def draw_wrapped_text(text, x, y, max_width):
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            if p.stringWidth(test_line, "Helvetica", 12) <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    # Cabeçalho
    p.drawString(margin, y, f"Chat de Saúde - {chat['timestamp']}")
    y -= 30

    # Pergunta
    p.drawString(margin, y, "Pergunta:")
    y -= line_height

    # Quebra a pergunta em múltiplas linhas
    question_lines = draw_wrapped_text(chat['question'], margin, y, right_margin - margin)
    for line in question_lines:
        p.drawString(margin + 20, y, line)
        y -= line_height
    y -= 15  # Espaço extra após a pergunta

    # Resposta
    p.drawString(margin, y, "Resposta:")
    y -= line_height

    # Quebra a resposta em parágrafos e linhas
    answer_paragraphs = chat['answer'].split('\n')
    for paragraph in answer_paragraphs:
        if paragraph.strip():  # Ignora parágrafos vazios
            # Quebra cada parágrafo em linhas
            paragraph_lines = draw_wrapped_text(paragraph, margin, y, right_margin - margin)
            for line in paragraph_lines:
                if y < 50:  # Nova página se necessário
                    p.showPage()
                    p.setFont("Helvetica", 12)
                    y = 750
                p.drawString(margin + 20, y, line)
                y -= line_height
            y -= 5  # Espaço entre parágrafos

    p.save()

    # Preparar resposta
    buffer.seek(0)
    response = buffer.getvalue()

    # Configurar cabeçalhos para download
    response_pdf = make_response(response)
    response_pdf.headers['Content-Type'] = 'application/pdf'
    response_pdf.headers['Content-Disposition'] = f'attachment; filename=chat_{chat_index}.pdf'

    return response_pdf

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
