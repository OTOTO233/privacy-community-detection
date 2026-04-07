"""
FastAPI 后端应用
提供REST API接口
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Dict, List
import json

from louvain_algorithm import LouvainDetector
from data_processor import DataProcessor
from differential_privacy import DifferentialPrivacy
from homomorphic_encryption import HomomorphicEncryption
from visualization import Visualizer

app = FastAPI(
    title="Privacy Community Detection API",
    description="基于隐私保护的社区检测系统",
    version="0.1.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DetectionRequest(BaseModel):
    """社区检测请求模型"""
    epsilon: Optional[float] = 1.0
    delta: Optional[float] = 1e-5
    use_encryption: Optional[bool] = False
    random_state: Optional[int] = 42


class DetectionResponse(BaseModel):
    """社区检测响应模型"""
    communities: Dict[int, int]
    statistics: Dict
    graph_info: Dict


@app.get("/")
async def root():
    """根端点"""
    return {"message": "Privacy Community Detection API"}


@app.post("/detect")
async def detect_communities(
        file: UploadFile = File(...),
        request: DetectionRequest = DetectionRequest()
):
    """
    上传数据集并执行社区检测
    """
    try:
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        # 读取数据
        graph = DataProcessor.read_dataset(tmp_path)

        # 应用差分隐私
        if request.epsilon > 0:
            dp = DifferentialPrivacy(epsilon=request.epsilon, delta=request.delta)
            # 可以在这里应用隐私保护

        # 执行社区检测
        detector = LouvainDetector(random_state=request.random_state)
        communities = detector.detect(graph)
        statistics = detector.get_statistics()

        # 获取图信息
        graph_info = DataProcessor.graph_statistics(graph)

        # 清理临时文件
        os.unlink(tmp_path)

        return {
            "communities": communities,
            "statistics": statistics,
            "graph_info": graph_info
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/visualize")
async def visualize_results(
        file: UploadFile = File(...),
        format: str = "spring"
):
    """
    生成社区检测可视化图像
    """
    try:
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        # 读取数据
        graph = DataProcessor.read_dataset(tmp_path)

        # 执行社区检测
        detector = LouvainDetector()
        communities = detector.detect(graph)

        # 生成可视化
        visualizer = Visualizer()
        output_path = tempfile.mktemp(suffix='.png')
        visualizer.visualize_communities(
            graph, communities,
            layout=format,
            output_path=output_path
        )

        # 清理临时文件
        os.unlink(tmp_path)

        return FileResponse(output_path, media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stats/{file_hash}")
async def get_statistics(file_hash: str):
    """获取检测统计信息"""
    # 这里可以从数据库或缓存中获取
    return {"stats": "placeholder"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)