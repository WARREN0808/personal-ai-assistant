from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import Base, engine, get_db
from app.llm_client import ask_llm
from app import models

Base.metadata.create_all(bind=engine)

app = FastAPI()


class MessageCreate(BaseModel):
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
    conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    user_message = models.Message(conversation_id=conversation_id, role="user", content=message.content)
    db.add(user_message)
    db.commit()

    messages = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.id)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in messages]

    try:
        reply_text = ask_llm(history)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur du modèle : {e}")

    assistant_message = models.Message(conversation_id=conversation_id, role="assistant", content=reply_text)
    db.add(assistant_message)
    db.commit()

    return {"reply": reply_text}


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return {
        "id": conversation.id,
        "created_at": conversation.created_at,
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at}
            for m in conversation.messages
        ],
    }
