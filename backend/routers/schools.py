from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from backend.database import get_db_connection

router = APIRouter()

@router.get("/directory")
def get_school_directory(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    level: Optional[str] = None,      # 本科 / 专科
    type_: Optional[str] = None,      # 综合 / 理工 / 师范 等
    province: Optional[str] = None,   # 所在省份
    keyword: Optional[str] = None     # 校名关键字
):
    """模块四：高校目录页面接口"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM school_info WHERE 1=1"
        params = []
        
        if level:
            query += " AND level = ?"
            params.append(level)
        if type_ and type_ != "全部":
            query += " AND school_type = ?"
            params.append(type_)
        if province and province != "全部":
            query += " AND province = ?"
            params.append(province)
        if keyword:
            query += " AND school_name LIKE ?"
            params.append(f"%{keyword}%")
            
        # 查询总数
        count_query = f"SELECT COUNT(*) as total FROM ({query})"
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # 分页并按排名排序
        query += " ORDER BY rank ASC, id ASC LIMIT ? OFFSET ?"
        params.extend([size, (page - 1) * size])
        
        cursor.execute(query, params)
        items = [dict(row) for row in cursor.fetchall()]
        
        return {
            "status": "success",
            "total": total,
            "page": page,
            "size": size,
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/filter")
def filter_schools(
    total_score: int,
    subject_type: str,
    batch: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    level: Optional[str] = None,      # 985 / 211 / 双一流 / 普通本科 / 专科
    province: Optional[str] = None,
    type_: Optional[str] = None,
    rec_type: Optional[str] = None    # reach / safe / guarantee
):
    """模块三：院校筛选列表接口 (需结合用户成绩进行推荐类别筛选)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取最新的录取年份
        cursor.execute("SELECT MAX(year) as max_year FROM school_admission WHERE subject_type = ? AND batch = ?", (subject_type, batch))
        year_row = cursor.fetchone()
        adm_year = year_row['max_year'] if year_row and year_row['max_year'] else 2024
        
        # 构建联合查询
        query = """
            SELECT a.school_name, a.province, a.min_score, a.min_rank,
                   i.school_type, i.is_985, i.is_211, i.dual_class, i.level
            FROM school_admission a
            LEFT JOIN school_info i ON a.school_name = i.school_name
            WHERE a.year = ? AND a.subject_type = ? AND a.batch = ? AND a.min_score IS NOT NULL
        """
        params = [adm_year, subject_type, batch]
        
        if province and province != "全部":
            query += " AND a.province = ?"
            params.append(province)
        if type_ and type_ != "全部":
            query += " AND i.school_type = ?"
            params.append(type_)
            
        if level and level != "全部":
            if level == "985":
                query += " AND i.is_985 = 1"
            elif level == "211":
                query += " AND i.is_211 = 1"
            elif level == "双一流":
                query += " AND i.dual_class != ''"
            elif level == "普通本科":
                query += " AND i.level = '本科' AND i.is_985 = 0 AND i.is_211 = 0"
            elif level == "专科":
                query += " AND i.level = '专科'"
                
        # 处理冲稳保条件筛选
        if rec_type and rec_type != "全部":
            # 冲一冲：5 <= diff <= 20  -> min_score - score >= 5 AND min_score - score <= 20
            # 稳一稳：-5 <= diff <= 4
            # 保一保：diff <= -10
            if rec_type == 'reach':
                query += " AND (a.min_score - ?) BETWEEN 5 AND 20"
                params.append(total_score)
            elif rec_type == 'safe':
                query += " AND (a.min_score - ?) BETWEEN -5 AND 4"
                params.append(total_score)
            elif rec_type == 'guarantee':
                query += " AND (a.min_score - ?) <= -10"
                params.append(total_score)

        # 查询总数
        count_query = f"SELECT COUNT(*) as total FROM ({query})"
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # 分页排序 (这里可以按分数倒序)
        query += " ORDER BY a.min_score DESC LIMIT ? OFFSET ?"
        params.extend([size, (page - 1) * size])
        
        cursor.execute(query, params)
        items = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # 计算对应的冲稳保类型和概率
            diff = row_dict['min_score'] - total_score
            rt = 'unknown'
            prob = 0
            if 5 <= diff <= 20:
                rt = 'reach'
                prob = int(40 - (diff - 5) * (20 / 15))
            elif -5 <= diff <= 4:
                rt = 'safe'
                prob = int(50 + (5 - diff) * (25 / 10))
            elif diff <= -10:
                rt = 'guarantee'
                prob = int(80 + (-diff - 6) * (15 / 14)) if diff <= -6 else 80
                
            row_dict['rec_type'] = rt
            row_dict['probability'] = prob
            items.append(row_dict)
            
        return {
            "status": "success",
            "total": total,
            "page": page,
            "size": size,
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
