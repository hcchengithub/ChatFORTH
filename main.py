#!/usr/bin/env python
# coding: utf-8

# API connectes to OpenAI or Azure ChatBot models

# Usage example:
#     1. activate MyMLenv
#     2. start API server (this .py)
#        (MyMLenv) d:\...>uvicorn main:app --host 0.0.0.0 --port 5189
#     3. run <client-name>.htm client side where <client-name> is something like ChatLKK or Completify.
#     4. API url can be changed by giving url to 'endpoint' value from client side.
#     5. OpenAI API_KEY can be given from the request too, so as to enable most recent usages directly from user's own resources.
#

# Fast API
#   https://fastapi.tiangolo.com/
#
#   為了簡化前後端的工作，本程式採用 FastAPI 做成 API 的形式 release.
#
#   執行方式：
#       uvicorn main:app
#       uvicorn main:app --host 0.0.0.0 --port 5189
#
#   FastAPI 有提供測試網頁，以上 webserver 跑起來之後，用 http://localhost:5189/docs 測試。
#

# 版本
backend_version = "R08"  # 顯示在 http://localhost:5189 greeting

# In[5]:
import os, time, random, json, openai

setup_PROD = False # False: log 在螢幕上, True: log 到 log file


# 加上 rotating 循環使用 log files 避免爆掉
import logging
from logging.handlers import RotatingFileHandler

FORMAT = '%(levelname)s %(asctime)s %(message)s'
log_path_name = (os.environ.get('Downloads') + "\\chatlkk.log") if setup_PROD else ""

def reset_logging(level=logging.DEBUG, pathname=log_path_name, max_bytes=1_000_000, backup_count=10):
    # Remove all existing handlers from root logger
    for i in logging.root.handlers:
        logging.root.removeHandler(i)

    logger = logging.getLogger()

    if setup_PROD:
        # Add new rotating file handler to root logger after removing previous instances (if any)
        # Set up a rotating file handler with max size and backup count parameters
        handler = RotatingFileHandler(pathname, maxBytes=max_bytes, backupCount=backup_count)

        # Configure the logger with this handler and format string
        formatter = logging.Formatter(FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)  # only add Handler when setup_PROD=True

    else:
        # add Console Handler instead of File Handler
        console_handler=logging.StreamHandler()
        # console_handler.setLevel(level)
        console_formatter=logging.Formatter(FORMAT)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    logger.setLevel(level) # this line makes the difference, why?

reset_logging(logging.DEBUG)
logging.debug("This is a logging.debug message.")
logging.info("This is a logging.info message.")

# Pre-defined model table
model_gpt4      = "gpt-4"
model_32k_gpt4  = "gpt-4-32k"
model_chatgpt35 = "gpt-3.5-turbo"
model_wi_4      = ""
model_wi_4_32k  = ""
model_gpt3      = "text-davinci-003"
model_8k_ft     = ""
model_wi_35     = ""

model_config = {
    model_wi_35: {
        "model_type":   "prompt-model",
        "engine":       model_wi_35,
        "api_key":      "",
        "api_type":     "",
        "api_base":     "",
        "api_version":  "",
    },
    model_wi_4: {
        "model_type":   "chat-model",
        "engine":       model_wi_4,
        "api_key":      "",
        "api_type":     "",
        "api_base":     "",
        "api_version":  "",
    },
    model_wi_4_32k: {
        "model_type":   "chat-model",
        "engine":       model_wi_4_32k,
        "api_key":      "",
        "api_type":     "",
        "api_base":     "",
        "api_version":  "",
    },
    model_8k_ft: {
        "model_type":   "prompt-model",
        "model":        model_8k_ft,
        "api_key":      "",
        "api_type":     "",
        "api_base":     "",
        "stop":         ["\nAI:","\nHuman:"]
        #"api_version":  "",
    },
}

def get_api_params(ui):

    default_config = {
        "model":        ui.model,
        "api_key":      ui.api_key,
        "api_type":     ui.api_type,
        "api_base":     ui.api_base,
        "api_version":  ui.api_version,
        "model_type":   ui.model_type,
    }

    # This code line is assigning a value to the variable named 'config' based on the 
    # result of calling the 'get' method on an object called model_config. The first 
    # argument passed to the get() method is a key, which in this case is being 
    # provided by accessing the 'ui.model' attribute. The second argument passed to 
    # get() is a default value that will be returned if there's no matching key found 
    # in model_config. So essentially, this line of code retrieves a configuration 
    # object from model_config using ui.model as its key. If such an object exists, 
    # it will be assigned to config; otherwise, default_config (which is another 
    # variable defined elsewhere) will be used instead.    
    config = model_config.get(ui.model, default_config)

    params = {
        **config,
        'prompt': ui.prompt,
        'temperature': ui.temperature,
        'max_tokens': ui.max_tokens,
        'top_p': ui.top_p,
        'frequency_penalty': ui.frequency_penalty,
        'presence_penalty': ui.presence_penalty,
        "stop": ui.stop
    }

    return (params)
    # model_type = params.pop("model_type")
    # if model_type == "prompt-model":
    # if model_type == "chat-model":

def make_request(para : dict):
    logging.info(f"make_request({para})")
    model_type = para.pop("model_type")
    try:
        if (model_type == "chat-model"):
            # Chat models must call ChatCompletion(()
            para['messages'] = json.loads(para.pop("prompt")) # ChatML array 轉成 double stringified
            response = openai.ChatCompletion.create(**para)
        else:
            # Non-Chat models are prompt models call Completion()
            response = openai.Completion.create(**para)

        response['status'] = 1

    except Exception as err:
        logging.info(f"An error occurred in make_request(): {err}")
        response = {
            "status" : 0,
            "type": type(err).__name__,
            "message" : str(err)
        }

    logging.info(f"Response from make_request(): {response}")
    return response

# ### Fast API

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Union,List
from fastapi.responses import JSONResponse   # AI let me add this to study CORS issue
from fastapi.staticfiles import StaticFiles  # AI let me add this to study CORS issue

# /complete service calls OpenAI or Azure GPT models

## Fast API 需要設計好 UI 要從 user 取得的 data
class Input(BaseModel):
    model: str = model_chatgpt35
    model_type: str = "chat-model"
    prompt: str = "[{\"role\": \"user\", \"content\": \"don\'t tell me any joke\"}]"
    temperature: float = 0.5
    max_tokens: int = 256
    top_p: float = 1
    frequency_penalty: float = 1
    presence_penalty: float = 1
    stop: List = ["\nAI:","\nHuman:"]
    api_key: str = ''
    api_type: str = 'open_ai'
    api_base: str = 'https://api.openai.com/v1'
    api_version: str = ""

class UI(Input):
    def init(self, input_json):
        for k,v in input_json.items():
            setattr(self, k, v)

app = FastAPI()
ui  = UI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

## Mounts /ChatFORTH route to serve contents from ./static folder
app.mount("/ChatFORTH", StaticFiles(directory="static", html=True))

@app.get('/')
def base():
    logging.info("GET called at /, show where's the .html")
    return f"Hi! version {backend_version} at your service. API test page @ http://localhost:5189/docs , http://localhost:5189/ChatFORTH/ChatFORTH.html"

@app.post('/complete')
def base(inputs: Input):
    ui.init(inputs.__dict__)
    logging.info("--------------------------------------------------------------------------")
    logging.info("New request ui = %s" % str(ui))
    params = get_api_params(ui)
    response = make_request(params)
    return json.dumps(response)


# /token_count service counts the given text
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
assert enc.decode(enc.encode("hello world")) == "hello world"

class Input2(BaseModel):
    text: str = "[{\"role\": \"user\", \"content\": \"don\'t tell me any joke\"}]"

@app.post('/token_count')
def token_count(inputs: Input2):
    logging.info("--------------------------------------------------------------------------")
    tokens = enc.encode(inputs.text) # tiktoken encoder
    result = {"response": len(tokens)}
    logging.info(f"token count: {result}")
    return result

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app="main:app", host="0.0.0.0", port=5189)

# --- The End ---

