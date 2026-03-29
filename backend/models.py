from pydantic import BaseModel
from typing import Optional, List

class AnalysisRequest(BaseModel):
    total_score: int
    province: str
    subject_type: str
    batch: str

class SchoolRecommendation(BaseModel):
    school_name: str
    province: str
    school_type: str # 院校类型（综合、理工等）
    is_985: bool
    is_211: bool
    dual_class: str
    min_score: int
    min_rank: int
    probability: int # 录取概率百分比
    rec_type: str # 冲一冲/稳一稳/保一保

class AnalysisResponse(BaseModel):
    status: str # "success" 或 "no_data"
    message: Optional[str] = None
    province: Optional[str] = None
    estimated_rank: Optional[int] = None
    total_schools: Optional[int] = None
    recommendations: Optional[dict] = None # {"reach": [], "safe": [], "guarantee": []}
