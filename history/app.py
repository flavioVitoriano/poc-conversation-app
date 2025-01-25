from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Acessar variáveis de ambiente
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "historico_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "historicos")

# Conexão com o MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitindo requisições das origens especificadas
    allow_credentials=True,
    allow_methods=["*"],  # Permitindo todos os métodos HTTP (GET, POST, etc)
    allow_headers=["*"],  # Permitindo todos os cabeçalhos
)

# Modelos Pydantic
class HistoricoBase(BaseModel):
    conversation_id: str
    user_id: str
    sender_name: str
    content: str
    correlator_id: str
    created_at: datetime = Field(default_factory=datetime.now)

class HistoricoCreate(HistoricoBase):
    pass

class Historico(HistoricoBase):
    id: str

    class Config:
        orm_mode = True


# Funções para manipulação do MongoDB
def get_historicos(user_id: Optional[str] = None, conversation_id: Optional[str] = None, limit: Optional[int] = None) -> List[dict]:
    query = {}
    if user_id:
        query["user_id"] = user_id
    if conversation_id:
        query["conversation_id"] = conversation_id
    
    cursor = collection.find(query).sort("created_at", -1)  # Ordem decrescente (do mais recente para o mais antigo)
    
    if limit:
        cursor = cursor.limit(limit)

    return list(cursor)


def create_historico(historico: HistoricoCreate) -> dict:
    historico_dict = historico.dict()
    historico_dict["created_at"] = historico_dict.get("created_at", datetime.utcnow())

    result = collection.insert_one(historico_dict)
    historico_dict["_id"] = result.inserted_id

    return historico_dict


def delete_historicos(user_id: Optional[str] = None, conversation_id: Optional[str] = None) -> int:
    query = {}
    if user_id:
        query["user_id"] = user_id
    if conversation_id:
        query["conversation_id"] = conversation_id

    result = collection.delete_many(query)
    return result.deleted_count


# Endpoints FastAPI
@app.get("/historicos", response_model=List[Historico])
async def list_historicos(
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    limit: Optional[int] = None,
):
    historicos = get_historicos(user_id=user_id, conversation_id=conversation_id, limit=limit)

    # Converte o _id para str antes de retornar
    for historico in historicos:
        historico["id"] = str(historico["_id"])
        del historico["_id"]
    return historicos


@app.post("/historicos", response_model=Historico)
async def create_historico_view(historico: HistoricoCreate):
    new_historico = create_historico(historico)
    # Converte o _id para str antes de retornar
    new_historico["id"] = str(new_historico["_id"])
    del new_historico["_id"]
    return new_historico


@app.delete("/historicos", response_model=dict)
async def delete_historicos_view(
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
):
    deleted_count = delete_historicos(user_id=user_id, conversation_id=conversation_id)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Nenhum histórico encontrado para deletar")
    
    return {"message": f"{deleted_count} histórico(s) deletado(s)"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
