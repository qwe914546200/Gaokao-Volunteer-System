from fastapi import APIRouter, HTTPException
from backend.models import AnalysisRequest, AnalysisResponse, SchoolRecommendation
from backend.database import get_db_connection

router = APIRouter()

def calculate_probability(diff: int, rec_type: str) -> int:
    """计算模拟录取概率"""
    # diff = 院校最低分 - 用户分数
    # 冲一冲：分数低于院校 5~20 分 (diff 在 5 到 20 之间)，概率 20%~40%
    if rec_type == 'reach':
        if diff >= 20: return 20
        if diff <= 5: return 40
        # 线性映射
        return int(40 - (diff - 5) * (20 / 15))
    
    # 稳一稳：分数与院校相差 ±5 分 (diff 在 -5 到 4 之间)，概率 50%~75%
    elif rec_type == 'safe':
        if diff >= 5: return 50
        if diff <= -5: return 75
        # diff 从 5 降到 -5，概率从 50% 升到 75%
        return int(50 + (5 - diff) * (25 / 10))
    
    # 保一保：分数高于院校 10 分以上 (diff <= -10)，概率 80%~95%
    elif rec_type == 'guarantee':
        if diff >= -5: return 80 # 保底逻辑，不应该出现
        if diff <= -20: return 95
        # diff 从 -6 到 -20，概率从 80% 到 95%
        return int(80 + (-diff - 6) * (15 / 14))
    
    return 0

@router.post("/recommend", response_model=AnalysisResponse)
def recommend_schools(req: AnalysisRequest):
    # 1. 省份数据缺失处理 (模块五)
    if req.province != "四川":
        return AnalysisResponse(
            status="no_data",
            province=req.province,
            message=f"抱歉，目前暂无【{req.province}】的录取数据，开发者正在加紧收集中，请稍后再试。"
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 2. 估算全省位次 (查询最近年份的一分一段表)
        # 找到最近一年的数据
        cursor.execute("SELECT MAX(year) as max_year FROM score_segment WHERE subject_type = ?", (req.subject_type,))
        year_row = cursor.fetchone()
        if not year_row or not year_row['max_year']:
            raise HTTPException(status_code=404, detail="未找到对应的位次数据")
        max_year = year_row['max_year']

        cursor.execute("""
            SELECT cumulative_count FROM score_segment 
            WHERE year = ? AND subject_type = ? AND score_min <= ?
            ORDER BY score_min DESC LIMIT 1
        """, (max_year, req.subject_type, req.total_score))
        rank_row = cursor.fetchone()
        estimated_rank = rank_row['cumulative_count'] if rank_row else 0

        # 3. 冲稳保智能推荐 (模块二)
        # 我们查询往年（如2024年或数据库最新年份）的录取数据，并与基础信息表连接
        cursor.execute("""
            SELECT MAX(year) as max_year FROM school_admission 
            WHERE subject_type = ? AND batch = ?
        """, (req.subject_type, req.batch))
        adm_year_row = cursor.fetchone()
        adm_max_year = adm_year_row['max_year'] if adm_year_row and adm_year_row['max_year'] else 2024

        cursor.execute("""
            SELECT a.school_name, a.province, a.min_score, a.min_rank,
                   i.school_type, i.is_985, i.is_211, i.dual_class
            FROM school_admission a
            LEFT JOIN school_info i ON a.school_name = i.school_name
            WHERE a.year = ? AND a.subject_type = ? AND a.batch = ? AND a.min_score IS NOT NULL
        """, (adm_max_year, req.subject_type, req.batch))
        
        schools_data = cursor.fetchall()
        
        recommendations = {"reach": [], "safe": [], "guarantee": []}
        total_schools = 0

        for row in schools_data:
            school_min_score = row['min_score']
            diff = school_min_score - req.total_score

            rec_type = None
            if 5 <= diff <= 20:
                rec_type = 'reach'
            elif -5 <= diff <= 4:
                rec_type = 'safe'
            elif diff <= -10:
                rec_type = 'guarantee'

            if rec_type:
                total_schools += 1
                
                # 为了限制返回数据量，每类最多返回 20 条（可根据需要调整）
                if len(recommendations[rec_type]) < 20:
                    prob = calculate_probability(diff, rec_type)
                    recommendations[rec_type].append({
                        "school_name": row['school_name'],
                        "province": row['province'],
                        "school_type": row['school_type'] or "综合",
                        "is_985": bool(row['is_985']),
                        "is_211": bool(row['is_211']),
                        "dual_class": row['dual_class'] or "",
                        "min_score": school_min_score,
                        "min_rank": row['min_rank'] or 0,
                        "probability": prob,
                        "rec_type": rec_type
                    })

        # 排序：冲一冲按概率升序（分差大的在前），保一保按概率降序（分差小的在前）
        recommendations["reach"] = sorted(recommendations["reach"], key=lambda x: x["probability"])
        recommendations["safe"] = sorted(recommendations["safe"], key=lambda x: x["probability"], reverse=True)
        recommendations["guarantee"] = sorted(recommendations["guarantee"], key=lambda x: x["probability"])

        return AnalysisResponse(
            status="success",
            estimated_rank=estimated_rank,
            total_schools=total_schools,
            recommendations=recommendations
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
