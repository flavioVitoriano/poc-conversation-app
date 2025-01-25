<template>
  <div class="chatbot-container">
    <div class="chat-window">
      <div class="messages">
        <div v-for="(msg, index) in messages" :key="index" :class="{'user-msg': msg.user, 'bot-msg': !msg.user}">
          <!-- Exibe o texto com suporte a Markdown renderizado -->
          <div v-if="!msg.user" v-html="renderMarkdown(msg.text)"></div>
          <div v-else>{{ msg.text }}</div>
        </div>
      </div>

      <!-- Indicador de Loading -->
      <div v-if="loading" class="loading">
        <span>Carregando...</span>
      </div>

      <div class="input-container">
        <input v-model="userInput" @keyup.enter="sendMessage" placeholder="Digite sua pergunta..." />
        <button @click="sendMessage">Enviar</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { marked } from "marked"; // Importa corretamente a biblioteca marked

export default {
  data() {
    return {
      userInput: "",
      messages: [],
      userId: "123",  // Defina um ID de usuário único
      conversationId: "abcd2",  // Defina um ID de conversa único
      correlatorId: "xyz",  // Defina um correlator de conversa único
      loading: false // Variável de loading
    };
  },
  methods: {
    async sendMessage() {
      if (this.userInput.trim() === "") return;

      // Adiciona a mensagem do usuário
      this.messages.push({ text: this.userInput, user: true });

      // Ativa o loading
      this.loading = true;

      // Envia a pergunta para a API de Perguntas
      try {
        const response = await axios.post("http://localhost:8001/ask-question", {
          question: this.userInput,
          user_id: this.userId,
          conversation_id: this.conversationId,
          correlator_id: this.correlatorId
        });

        // Adiciona a resposta do bot
        this.messages.push({ text: response.data, user: false });
      } catch (error) {
        console.error("Erro ao enviar pergunta: ", error);
        this.messages.push({ text: "Erro ao enviar pergunta, tente novamente.", user: false });
      } finally {
        // Desativa o loading quando a requisição for finalizada
        this.loading = false;
      }

      this.userInput = ""; // Limpa o campo de entrada
    },
    renderMarkdown(text) {
      // Converte texto Markdown para HTML
      return marked(text);
    },
    async loadHistory() {
      try {
        const response = await axios.get("http://localhost:8000/historicos", {
          params: {
            user_id: this.userId,
            conversation_id: this.conversationId,
          }
        });
        response.data = response.data.reverse();
        // Adiciona as mensagens do histórico
        response.data.forEach(historico => {
          this.messages.push({ text: `${historico.sender_name}: ${historico.content}`, user: false });
        });
      } catch (error) {
        console.error("Erro ao carregar histórico: ", error);
      }
    }
  },
  mounted() {
    this.loadHistory(); // Carrega o histórico de mensagens quando a aplicação iniciar
  }
};
</script>

<style scoped>
.chatbot-container {
  max-width: 800px;  /* Aumenta a largura */
  margin: 0 auto;
  font-family: Arial, sans-serif;
  background-color: #f7f7f7;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  height: 80vh; /* Define a altura para que o chat ocupe mais da tela */
}

.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow-y: auto;
  padding: 10px;
  background-color: white;
}

.messages {
  flex-grow: 1;
  overflow-y: auto;
  padding: 10px;
}

.messages .user-msg {
  text-align: right;
  background-color: #d4f0ff;
  padding: 5px;
  border-radius: 5px;
  margin: 5px 0;
}

.messages .bot-msg {
  text-align: left;
  background-color: #e0e0e0;
  padding: 5px;
  border-radius: 5px;
  margin: 5px 0;
}

.input-container {
  display: flex;
  margin-top: 10px;
}

input {
  flex-grow: 1;
  padding: 10px;
  border-radius: 5px;
  border: 1px solid #ccc;
}

button {
  padding: 10px 20px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 5px;
  margin-left: 10px;
  cursor: pointer;
}

button:hover {
  background-color: #45a049;
}

.loading {
  text-align: center;
  margin: 10px 0;
  font-size: 16px;
  color: #888;
}
</style>
