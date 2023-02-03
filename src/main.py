from fastapi import FastAPI, Request
import uvicorn
from api import models
from fastapi.middleware.cors import CORSMiddleware
from api.routers import project, session, log, pre_processing, statistics, process_schema, analyse_model, mappings, \
    filter, metrics
from api.routers import import_event_data, load_log
from api.database import engine
from fastapi.middleware.gzip import GZipMiddleware
# from fastapi_utils.timing import add_timing_middleware
import time
import os
from fastapi_utils.tasks import repeat_every
from repeat_tasks import Task1, Task2
import requests

description = """
Process Mining API for BPM Genesis help you do process stuff.   🚀

"""

app = FastAPI(
    docs_url='/docs',
    #openapi_url="/mining-broker-schema.json",
    title="Process Mining Broker",
    description=description,
    version="0.0.1",
    terms_of_service="https://bpmgenesis.com",
    contact={
        "name": "BPM Genesis",
        "url": "https://bpmgenesis.com",
        "email": "info@bpmgenesis.com",
    },
    # servers=[
    #     {"url": "http://127.0.0.1:5001/", "description": "Development environment"},
    #     {"url": "https://bpmgenesis.com/broker/organization", "description": "Production environment"},
    # ],
    # license_info={
    #     "name": "Apache 2.0",
    #     "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    # },
)


# origins = [
#     "http://127.0.0.1:5000",
#     "http://localhost:5000",
#     'https:/bpmgenesis.com'
# ]


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    print(process_time)
    response.headers["X-Process-Time"] = str(process_time)
    return response


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# add_timing_middleware(app, prefix="app", exclude="untimed")


app.include_router(metrics.router)
app.include_router(filter.router)
app.include_router(mappings.router)
app.include_router(analyse_model.router)
app.include_router(project.router)
app.include_router(session.router)
app.include_router(log.router)
app.include_router(pre_processing.router)
app.include_router(statistics.router)
app.include_router(import_event_data.router)
app.include_router(load_log.router)
app.include_router(process_schema.router)

# app.include_router(blog.router)
# app.include_router(user.router)

models.Base.metadata.create_all(engine)


try:
    # in local environment
    from dotenv import load_dotenv

    load_dotenv()
    gateway_url = os.getenv('realmmanager_broker')
except:
    pass


@app.on_event("startup")
@repeat_every(seconds=60 * 60)
def csp_import():
    # Task1()
    # Task2()
    return


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5001, log_level="info")
