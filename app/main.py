from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import Base, engine, get_db
from app import models

Base.metadata.create_all(bind=engine)

app = FastAPI()


class MessageCreate(BaseModel):
    role: str
    content: str


@app.get("/")
def read_root():
    return {"message": "Hello, l'assistant est en ligne"}


@app.post("/conversations")
def create_conversation(db: Session = Depends(get_db)):
    conversation = models.Conversation()
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return {"id": conversation.id, "created_at": conversation.created_at}


@app.post("/conversations/{conversation_id}/messages")
def create_message(conversation_id: int, message: MessageCreate, db: Session = Depends(get_db)):
    new_message = models.Message(
        conversation_id=conversation_id,
        role=message.role,
        content=message.content
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return {
        "id": new_message.id,
        "role": new_message.role,
        "content": new_message.content,
        "created_at": new_message.created_at
    }
