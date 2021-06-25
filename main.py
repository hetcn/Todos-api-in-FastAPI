import urllib
import os

from starlette.types import ASGIApp

host_server = os.environ.get('host_server', 'localhost')
db_server_port = urllib.parse.quote_plus(str(os.environ.get('db_server_port', '5432')))
database_name = os.environ.get('database_name', 'postgres')
db_username = urllib.parse.quote_plus(str(os.environ.get('db_username', 'provide username here')))
db_password = urllib.parse.quote_plus(str(os.environ.get('db_password', 'provide password here')))
ssl_mode = urllib.parse.quote_plus(str(os.environ.get('ssl_mode','prefer')))
DATABASE_URL = 'postgresql://{}:{}@{}:{}/{}?sslmode={}'.format(db_username, db_password, host_server, db_server_port, database_name, ssl_mode)

import sqlalchemy

metadata = sqlalchemy.MetaData()

todos = sqlalchemy.Table(
    "todos",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("title", sqlalchemy.String),
    sqlalchemy.Column("description", sqlalchemy.String),
)

engine = sqlalchemy.create_engine(
    #DATABASE_URL, connect_args={"check_same_thread": False}
    DATABASE_URL, pool_size=3, max_overflow=0
)
metadata.create_all(engine)


from pydantic import BaseModel

class TodosIn(BaseModel):
    title: str
    description: str

class Todo(BaseModel):
    id: int
    title: str
    description: str


from fastapi import FastAPI
# from fastapi.middleware.core import CORSMiddleware
from typing import List

app = FastAPI(title="REST API using FastAPI PostgreSQL Async EndPoints")
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"]
# )

import databases
database = databases.Database(DATABASE_URL)

@app.on_event('startup')
async def startup():
    await    database.connect()

@app.on_event('shutdown')
async def shutdown():
    await database.disconnect() 


@app.post("/todos/",response_model=Todo)
async def create_todo(todo:TodosIn):
    query = todos.insert().values(title=todo.title,description=todo.description)
    last_record_id = await database.execute(query)
    return {**todo.dict(),"id":last_record_id}

@app.get("/todos/",response_model=List[Todo])
async def read_todos(skip:int=0,take: int = 20):
    query = todos.select().offset(skip).limit(take)
    return await database.fetch_all(query)

@app.put('/todos/{todo_id}',response_model=Todo)
async def update_todo(todo_id:int,payload:TodosIn):
    query = todos.update().where(todos.c.id == todo_id).values(title=payload.title,description=payload.description)
    await database.execute(query)
    return {**payload.dict(),"id":todo_id}

@app.get("/todos/{todo_id}",response_model=Todo)
async def read_todos(todo_id:int):
    query = todos.select().where(todos.c.id == todo_id)
    return await database.fetch_one(query)

@app.delete("/notes/{todo_id}")
async def delete_todes(todo_id:int):
    query = todos.delete().where(todos.c.id == todo_id)
    await database.execute(query)
    return {"message":"Todo with id: {} deleted successfully".format(todo_id)}

