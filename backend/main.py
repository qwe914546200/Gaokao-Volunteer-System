from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import analysis, schools

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

@app.get("/")
def read_root():
    return {"message": "Welcome to 智慧升学平台 API. 访问 /docs 查看接口文档。"}

if __name__ == "__main__":
    import uvicorn
    # 本地启动：python main.py
    uvicorn.run(app, host="0.0.0.0", port=8000)
