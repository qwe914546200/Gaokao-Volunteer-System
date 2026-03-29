import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from backend.routers import analysis, schools

app = FastAPI(
    title="智慧升学平台 API",
    description="高考志愿填报模拟系统后端接口",
    version="1.0.0"
)

# 允许跨域请求，方便本地直接打开 HTML 文件调试
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router, prefix="/api/analysis", tags=["模块一/二/五：成绩分析与推荐"])
app.include_router(schools.router, prefix="/api/schools", tags=["模块三/四：院校查询"])

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")

@app.get("/")
def read_root():
    if os.path.exists(INDEX_FILE):
        return FileResponse(INDEX_FILE)
    return {"message": "前端页面不存在，请确认 index.html 已部署到项目根目录。"}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    # 本地启动：python main.py
    uvicorn.run(app, host="0.0.0.0", port=8000)
