// O script só é executado depois que todo o HTML da página é carregado.
document.addEventListener('DOMContentLoaded', function() {

    // Seleciona os principais elementos do HTML para interação
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const messagesContainer = document.getElementById('messages');
    const welcomeContainer = document.getElementById('chat-welcome');

    // Evento de Envio do Formulário
    // Adiciona um "ouvinte" ao formulário para capturar o envio de mensagens.
    chatForm.addEventListener('submit', function(e) {
        // Previne o comportamento padrão do formulário, que é recarregar a página.
        e.preventDefault();

        // Pega o texto digitado pelo usuário e remove espaços extras no início e fim.
        const message = userInput.value.trim();

        // Só processa a mensagem se ela não estiver vazia.
        if (message) {
            // Se a tela de boas-vindas estiver visível, ela é escondida.
            if (welcomeContainer && !welcomeContainer.classList.contains('hidden')) {
                welcomeContainer.classList.add('hidden');
            }

            // Exibe a mensagem do usuário na tela.
            addMessage(message, 'user');
            // Limpa o campo de entrada para uma nova mensagem.
            userInput.value = '';

            // Animação de Carregamento
            // Cria e adiciona o elemento de "carregando" na tela.
            const loaderElement = createLoaderElement();
            messagesContainer.appendChild(loaderElement);
            // Rola a tela para baixo para mostrar a animação.
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // Requisição para o Servidor
            // Envia a mensagem do usuário para o backend.
            fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `message=${encodeURIComponent(message)}`
            })
            // Converte a resposta do servidor para JSON.
            .then(response => response.json())
            // Pega a resposta do bot e a exibe na tela.
            .then(data => {
                addMessage(data.answer, 'bot');
            })
            // Captura e trata possíveis erros de comunicação.
            .catch(error => {
                console.error('Error:', error);
                addMessage('Desculpe, ocorreu um erro.', 'bot');
            })
            // Remove o elemento de "carregando", independentemente do resultado.
            .finally(() => {
                loaderElement.remove();
            });
        }
    });

    // Funções Auxiliares

    // Cria e retorna o elemento de animação de "carregando".
    function createLoaderElement() {
        // Cria o contêiner principal
        const loaderContainer = document.createElement('div');
        loaderContainer.classList.add('loader-container');

        // Cria o elemento de vídeo
        const video = document.createElement('video');
        video.src = '/static/videos/loading.mp4';
        video.classList.add('loading-video');
        video.autoplay = true;
        video.loop = true;
        video.muted = true;
        video.playsInline = true;

        // Cria o elemento de texto
        const text = document.createElement('p');
        text.classList.add('loader-text');
        text.textContent = 'Health.AI está pensando...';

        // Adiciona o vídeo e o texto ao contêiner
        loaderContainer.appendChild(video);
        loaderContainer.appendChild(text);

        return loaderContainer;
    }

    // Adiciona uma nova mensagem na interface do chat.
    function addMessage(text, sender) {
        // Cria um novo elemento div para a mensagem.
        const messageElement = document.createElement('div');
        // Adiciona classes CSS para estilizar a mensagem de acordo com o remetente (user/bot).
        messageElement.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');
        // Define o texto da mensagem.
        messageElement.textContent = text;
        // Adiciona a mensagem ao contêiner de mensagens.
        messagesContainer.appendChild(messageElement);
        // Rola a tela para baixo para a mensagem ficar visível.
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
});
