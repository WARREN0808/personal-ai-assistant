from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import Base, engine, get_db
from app import models
from typing import Optional
from datetime import datetime
from app.llm_client import ask_llm, generate_tasks

Base.metadata.create_all(bind=engine)

app = FastAPI()


class MessageCreate(BaseModel):
    content: str

class GoalCreate(BaseModel):
    title: str
    deadline: Optional[datetime] = None

class TaskCreate(BaseModel):
    title: str

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

@app.post("/goals")
def create_goal(goal: GoalCreate, db: Session = Depends(get_db)):
    new_goal = models.Goal(title=goal.title, deadline=goal.deadline)
    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)

    try:
        task_titles = generate_tasks(new_goal.title, new_goal.deadline)
        for title in task_titles:
            task = models.Task(goal_id=new_goal.id, title=title)
            db.add(task)
        db.commit()
    except Exception as e:
        print(f"Erreur génération tâches : {e}")
        task_titles = []

    return {
        "id": new_goal.id,
        "title": new_goal.title,
        "deadline": new_goal.deadline,
        "tasks_generated": task_titles
    }

@app.post("/goals/{goal_id}/tasks")
def create_task(goal_id: int, task: TaskCreate, db: Session = Depends(get_db)):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if goal is None:
        raise HTTPException(status_code=404, detail="Objectif introuvable")
    new_task = models.Task(goal_id=goal_id, title=task.title)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return {"id": new_task.id, "goal_id": goal_id, "title": new_task.title}

@app.get("/goals")
def get_goals(db: Session = Depends(get_db)):
    goals = db.query(models.Goal).all()
    return [
        {
            "id": g.id,
            "title": g.title,
            "deadline": g.deadline,
            "status": g.status,
            "tasks": [
                {"id": t.id, "title": t.title, "status": t.status}
                for t in g.tasks
            ]
        }
        for g in goals
    ]
