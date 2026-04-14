"""Request/response models for evolutionary parameter optimization API."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field


class EAOptimizeRequest(BaseModel):
    """与前端实验表单字段一致，额外指定种群规模与代数。"""

    form: Dict[str, Any] = Field(..., description="与 /detect 相同的表单字典（含 dataset_name、algorithm、epsilon、lambd、biogrid_* 等）")
    population_size: int = Field(8, ge=2, le=40)
    generations: int = Field(6, ge=1, le=50)
    compare_baseline: bool = Field(True, description="是否用当前表单的 epsilon/lambd 跑一次作为对照")
    save_json: bool = Field(True, description="是否在项目 output/ 下保存结果 JSON")

    def max_evaluations(self) -> int:
        return self.population_size * self.generations
