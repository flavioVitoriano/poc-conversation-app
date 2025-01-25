import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
import requests
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from tools import available_tools, tools_store
from loguru import logger
from langchain.callbacks.tracers import ConsoleCallbackHandler

# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()

# Obter a chave da API e a URL base da OpenAI das variáveis de ambiente
api_key = os.getenv("OPENAI_API_KEY", "your-api-key")
api_base = os.getenv("OPENAI_API_BASE_URL", "http://localhost:11434/v1")
model = os.getenv("OPENAI_MODEL", "qwen2.5:7b-instruct-q8_0")
history_base_url = os.getenv("HISTORy_API_BASE_URL", "http://localhost:8000")

# Criação do app FastAPI
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitindo requisições das origens especificadas
    allow_credentials=True,
    allow_methods=["*"],  # Permitindo todos os métodos HTTP (GET, POST, etc)
    allow_headers=["*"],  # Permitindo todos os cabeçalhos
)

# Definindo o modelo de dados para a requisição
class QuestionRequest(BaseModel):
    question: str
    user_id: str
    conversation_id: str
    correlator_id: str

# Criando o prompt template do LangChain
prompt_template = """
Baseado na PERSONA e nas INFORMACOES ADICIONAIS, continue a CONVERSA com o usuário.
As mensagems com 'assistant' são referentes as suas respostas, enquanto as mensagens com 'user' são referentes às perguntas do usuário.

PERSONA:
Nome: Alberto
Personalidade: Alberto é um assistente culto e amigável. Ele sempre responde de forma educada e compreensiva.
Conhecimentos: Alberto tem conhecimentos profundos sobre civilizações antigas e é um entusiasta da cultura oriental.

INFORMACOES ADICIONAIS:
{% if executed_tools %}
Para auxiliar na resposta da ultima mensagem do usuário, tive que executar a/as ferramenta/s abaixo:
{% for tool in executed_tools %}
Ferramenta: {{tool.name}}
Descrição: {{tool.description}}
Argumentos: {{tool.args}}
Saída: {{tool.output}}

{% endfor %}}
{% else %}
Sem informações adicionais
{% endif %}

CONVERSA:
{% for message in messages %}
{{message.sender}}: {{message.content}}
{% endfor %}
user: {{question}}
assistant: 
"""
prompt = PromptTemplate(input_variables=["question"], template=prompt_template, template_format="jinja2")

# Setup do modelo LLM do LangChain com OpenAI
llm = ChatOpenAI(model=model, temperature=0.7, api_key=api_key, base_url=api_base)  # Configure conforme necessário
llm_tool_caller = llm.bind_tools(available_tools)
llm_chain = prompt | llm | StrOutputParser()

# Função para obter a resposta em streaming de tokens
def generate_streaming_response(question: str, messages: list, executed_tools: list):
    for chunk in llm_chain.stream({
        "question": question,
        "messages": messages,
        "executed_tools": executed_tools,
    }, config={'callbacks': [ConsoleCallbackHandler()]}):
        yield chunk

def create_history(user_id: str, conversation_id: str, correlator_id: str, sender_name: str, content: str):
    historico_data = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "correlator_id": correlator_id,
        "sender_name": sender_name,
        "content": content,
    }
    response = requests.post(f"{history_base_url}/historicos", json=historico_data)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Erro ao criar histórico")
    
    logger.info(f"Created history with ID: {response.json()['id']}")
    return response.json()

def get_history(user_id: str, conversation_id: str, limit: int):
    response = requests.get(f"{history_base_url}/historicos", params={"limit": limit, "user_id": user_id, "conversation_id": conversation_id})
    messages = list(response.json())
    messages.reverse()

    return messages

def execute_tools(question: str):
    result = llm_tool_caller.invoke(question)
    tool_calls  = result.tool_calls

    response = []

    for tool_call in tool_calls:
        tool = tools_store[tool_call["name"]]
        result = tool.invoke(tool_call["args"])
        response.append({
            "name": tool_call["name"],
            "description": tool.description,
            "output": result,
            "args": tool_call["args"]
        })
        logger.info(f"Executed tool: {tool_call['name']} with args: {tool_call['args']}")
    
    return response

@app.post("/ask-question")
async def ask_question(request: QuestionRequest):
    try:
        # Preparando a pergunta com LangChain
        question = request.question

        # mensagens
        messages = get_history(user_id=request.user_id, conversation_id=request.conversation_id, limit=10)

        # tools
        executed_tools = execute_tools(question)

        # create user history
        create_history(
            user_id=request.user_id, 
            conversation_id=request.conversation_id, 
            correlator_id=request.correlator_id, 
            sender_name="user", 
            content=question)
        
        # Gerando resposta em streaming
        response_stream = generate_streaming_response(question=question, messages=messages, executed_tools=executed_tools)

        def make_gen():
            full_response = ""
            
            for chunk in response_stream:
                full_response += chunk
                yield chunk
        
            create_history(
                user_id=request.user_id, 
                conversation_id=request.conversation_id, 
                correlator_id=request.correlator_id, 
                sender_name="assistant", 
                content=full_response
            )

        # Enviando a resposta como um StreamingResponse
        return StreamingResponse(make_gen(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
