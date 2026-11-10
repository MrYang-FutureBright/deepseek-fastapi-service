from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from chat import request_model
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger=logging.getLogger(__name__)

app=FastAPI()
class Question(BaseModel):
    question: str
@app.get("/health")
def health():
    return {"status":"OK"}

@app.post("/chat")
def chat(data: Question):
    logger.info("受到请求")

    question = data.question.strip()
    if not question:
        logger.warning("用户提交了空问题 status_code=400")
        raise HTTPException(
            status_code=400,
            detail="问题不可为空"
        )
    message=[
        {"role": "system","content": "你是一个AI助手"},
        {"role": "user","content": question}
    ]
    start=time.perf_counter()
    try:
        answer=request_model(message)
        if answer is None:
            raise HTTPException(
            status_code=502,
            detail="模型请求失败"
            )
    except HTTPException as e:
        elapsed=time.perf_counter()-start
        logger.error(
        "模型调用失败 status=%s detail=%s elapsed=%.3fs",
        e.status_code,
              e.detail,
              elapsed
        )
        raise

    elapsed=time.perf_counter()-start
    logger.info(
        "模型成功返回答案 elapsed=%.3fs",
        elapsed
    )
    return {"answer":answer}



