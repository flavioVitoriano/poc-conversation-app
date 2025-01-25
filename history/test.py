import pytest
import mongomock
from fastapi.testclient import TestClient
from app import app  # Importa a aplicação FastAPI do arquivo main.py
from datetime import datetime
from bson import ObjectId
import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Carregar variáveis de ambiente para os testes
load_dotenv()

# Configurações para o banco de dados, mas usando o mongomock
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "historico_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "historicos")

# Função para configurar o banco de dados usando mongomock
@pytest.fixture(scope="module")
def mock_mongo_db():
    # Cria uma instância do mongomock para simular o MongoDB
    client = mongomock.MongoClient()
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    # Substitui o banco de dados real no app com o mock
    app.mongodb_client = client
    app.db = db
    app.collection = collection
    
    # Inserir dados pré-existentes no banco simulado
    collection.insert_many([
        {
            "conversation_id": "conv123",
            "user_id": "user456",
            "sender_name": "Alice",
            "content": "Olá, tudo bem?",
            "correlator_id": "corr789",
            "created_at": datetime.utcnow(),
        },
        {
            "conversation_id": "conv124",
            "user_id": "user456",
            "sender_name": "Bob",
            "content": "Oi, como vai?",
            "correlator_id": "corr790",
            "created_at": datetime.utcnow(),
        },
        {
            "conversation_id": "conv125",
            "user_id": "user789",
            "sender_name": "Charlie",
            "content": "Bom dia!",
            "correlator_id": "corr791",
            "created_at": datetime.utcnow(),
        },
    ])
    
    yield collection  # Isso garante que o banco de dados seja limpo entre os testes
    
    # Cleanup após os testes
    client.drop_database(DB_NAME)

# Criar um cliente para interagir com a API
client = TestClient(app)

# Teste para garantir que a aplicação esteja rodando
def test_app_is_up():
    response = client.get("/")
    assert response.status_code == 404  # FastAPI retorna 404 em "/"

# Teste para listar históricos
def test_list_historicos(mock_mongo_db):
    # Verificar se os dados já estão no banco simulado
    response = client.get("/historicos?user_id=user456")
    assert response.status_code == 200
    json_response = response.json()
    
    assert len(json_response) == 2  # Dois históricos com user_id "user456"
    assert json_response[0]["user_id"] == "user456"
    assert json_response[1]["user_id"] == "user456"
    
    # Verificar que o histórico de outro usuário não está presente
    response = client.get("/historicos?user_id=user789")
    assert response.status_code == 200
    json_response = response.json()
    assert len(json_response) == 1  # Apenas um histórico com user_id "user789"
    assert json_response[0]["user_id"] == "user789"

# Teste para deletar históricos
def test_delete_historicos(mock_mongo_db):
    # Antes de deletar, garantir que existem históricos para deletar
    response = client.get("/historicos?user_id=user456")
    assert response.status_code == 200
    assert len(response.json()) == 2  # Espera 2 históricos para o user_id "user456"

    # Deletar os históricos de "user456"
    response = client.delete("/historicos?user_id=user456")
    assert response.status_code == 200
    json_response = response.json()
    assert "message" in json_response
    assert json_response["message"] == "2 histórico(s) deletado(s)"

    # Verificar se os históricos de "user456" foram realmente deletados
    response = client.get("/historicos?user_id=user456")
    assert response.status_code == 200
    assert len(response.json()) == 0  # Não deve haver históricos de "user456" após a exclusão

    # Verificar se o histórico de "user789" ainda existe
    response = client.get("/historicos?user_id=user789")
    assert response.status_code == 200
    assert len(response.json()) == 1  # O histórico de "user789" ainda deve existir

# Teste para quando não houver histórico para deletar
def test_delete_historicos_not_found(mock_mongo_db):
    # Deletar com parâmetros que não correspondem a nada
    response = client.delete("/historicos?user_id=nonexistent_user")
    assert response.status_code == 404
    json_response = response.json()
    assert "detail" in json_response
    assert json_response["detail"] == "Nenhum histórico encontrado para deletar"
