#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import datetime
from datetime import timedelta, timezone
import uuid
import logging
import traceback
import mysql.connector
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
from dataclasses import dataclass
import re
import sys
import os

# 强制设置编码
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# 设置环境变量
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/janus_service.logs', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CORS配置
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})


@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
        return response


# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'analysis_reports',
    'charset': 'utf8mb4',
    'autocommit': True
}


def get_db_connection():
    """获取数据库连接"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        logger.error(f"数据库连接失败: {err}")
        return None


def ensure_timezone_aware(dt):
    """确保datetime对象是时区感知的"""
    if dt is None:
        return None

    if isinstance(dt, str):
        try:
            if dt.endswith('Z'):
                dt = dt.replace('Z', '+00:00')
            dt = datetime.datetime.fromisoformat(dt)
        except:
            try:
                dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
            except:
                dt = datetime.datetime.now()

    if not isinstance(dt, datetime.datetime):
        return datetime.datetime.now(timezone.utc)

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_current_time():
    """获取当前时区感知的时间"""
    return datetime.datetime.now(timezone.utc)


@dataclass
class ViolationRecord:
    timestamp: datetime.datetime
    camera_id: str
    violation_type: str
    count: int
    confidence: float
    record_id: int = None

    def __post_init__(self):
        self.timestamp = ensure_timezone_aware(self.timestamp)


class SmartTimeRangeAnalyzer:
    """智能时间范围分析器 - 修复AI回答和时间范围问题"""

    def __init__(self):
        self.violation_mapping = {
            'no_mask': '未佩戴口罩',
            'no_hat': '未佩戴工作帽',
            'phone_usage': '使用手机',
            'smoking': '吸烟行为',
            'mouse_infestation': '鼠患问题',
            'uniform_violation': '工作服违规',
            'mask': '口罩违规',
            'hat': '工作帽违规',
            'phone': '手机使用',
            'cigarette': '吸烟',
            'mouse': '鼠患',
            'uniform': '工作服问题'
        }

        # 修复：调整风险权重，避免分数过高
        self.risk_weights = {
            'mouse_infestation': 8,
            'mouse': 8,
            'smoking': 7,
            'cigarette': 7,
            'no_mask': 3,
            'mask': 3,
            'no_hat': 2,
            'hat': 2,
            'phone_usage': 1,
            'phone': 1,
            'uniform_violation': 1,
            'uniform': 1
        }

        # 修复：不预设摄像头位置，动态获取
        self.camera_locations = {}

        # 尝试加载Janus-Pro模型
        self.janus_model = None
        self.vl_chat_processor = None
        self.load_janus_model()

    def load_janus_model(self):
        """加载Janus-Pro模型"""
        try:
            model_path = "./models/janus-pro-1b"
            if not os.path.exists(model_path):
                logger.warning(f"Janus-Pro模型路径不存在: {model_path}")
                return

            try:
                from janus.models import MultiModalityCausalLM, VLChatProcessor
                import torch

                logger.info("正在加载Janus-Pro-1B模型...")

                self.vl_chat_processor = VLChatProcessor.from_pretrained(
                    model_path,
                    trust_remote_code=True
                )

                self.janus_model = MultiModalityCausalLM.from_pretrained(
                    model_path,
                    trust_remote_code=True,
                    torch_dtype=torch.bfloat16,
                    device_map="auto"
                )

                logger.info("✅ Janus-Pro-1B模型加载成功")

            except ImportError as e:
                logger.warning(f"无法导入Janus库: {e}")
            except Exception as e:
                logger.error(f"加载Janus-Pro模型失败: {e}")

        except Exception as e:
            logger.error(f"初始化Janus-Pro模型失败: {e}")

    def smart_time_range_detection(self, query: str, user_time_range: int) -> int:
        """智能时间范围检测 - 根据查询内容自动调整时间范围"""

        # 修复：确保输入参数有效
        if user_time_range is None or user_time_range == 0:
            user_time_range = 24
            logger.warning("用户时间范围无效，设置为默认24小时")

        try:
            user_time_range = int(user_time_range)
        except (ValueError, TypeError):
            user_time_range = 24
            logger.warning("用户时间范围转换失败，设置为默认24小时")

        if user_time_range <= 0:
            user_time_range = 24

        query_lower = query.lower()

        # 今天/今日相关
        if any(keyword in query_lower for keyword in ['今天', '今日', 'today', '当天']):
            logger.info(f"检测到'今天'查询，自动调整时间范围为24小时")
            return 24

        # 昨天相关
        elif any(keyword in query_lower for keyword in ['昨天', '昨日', 'yesterday']):
            logger.info(f"检测到'昨天'查询，自动调整时间范围为48小时（用于对比）")
            return 48

        # 本周相关
        elif any(keyword in query_lower for keyword in ['本周', '这周', '这一周', 'this week', '一周']):
            logger.info(f"检测到'本周'查询，自动调整时间范围为168小时（7天）")
            return 168

        # 本月相关
        elif any(keyword in query_lower for keyword in ['本月', '这个月', 'this month', '一个月']):
            logger.info(f"检测到'本月'查询，自动调整时间范围为720小时（30天）")
            return 720

        # 最近X小时
        elif '小时' in query_lower:
            hour_match = re.search(r'(\d+)\s*小时', query_lower)
            if hour_match:
                hours = int(hour_match.group(1))
                logger.info(f"检测到'{hours}小时'查询，自动调整时间范围")
                return hours

        # 最近X天
        elif '天' in query_lower:
            day_match = re.search(r'(\d+)\s*天', query_lower)
            if day_match:
                days = int(day_match.group(1))
                hours = days * 24
                logger.info(f"检测到'{days}天'查询，自动调整时间范围为{hours}小时")
                return hours

        # 没有特定时间指示，使用用户选择的时间范围
        else:
            logger.info(f"未检测到特定时间词汇，使用用户选择的时间范围: {user_time_range}小时")
            return user_time_range

    def get_camera_display_name(self, camera_id: str) -> str:
        """获取摄像头显示名称"""
        return f"{camera_id}摄像头"

    def get_violation_data(self, time_range_hours: int = 24, query_all: bool = False) -> Dict[str, Any]:
        """从数据库获取真实违规数据"""

        # 修复：确保时间范围参数有效
        if time_range_hours is None:
            time_range_hours = 24
            logger.warning("时间范围参数为None，设置为默认24小时")

        try:
            time_range_hours = int(time_range_hours)
        except (ValueError, TypeError):
            time_range_hours = 24
            logger.warning("时间范围参数无效，设置为默认24小时")

        if time_range_hours <= 0 and not query_all:
            time_range_hours = 24

        conn = get_db_connection()
        if not conn:
            return {}

        try:
            cursor = conn.cursor(dictionary=True)

            if query_all or time_range_hours <= 0:
                query = """
                SELECT 
                    id, camera_id, detection_timestamp, violation_data, 
                    total_violations, created_at
                FROM violations_records
                ORDER BY detection_timestamp DESC
                """
                cursor.execute(query)
                time_desc = "所有历史数据"
                logger.info("查询所有历史数据")
            else:
                query = """
                SELECT 
                    id, camera_id, detection_timestamp, violation_data, 
                    total_violations, created_at
                FROM violations_records
                WHERE detection_timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                ORDER BY detection_timestamp DESC
                """
                cursor.execute(query, (time_range_hours,))

                # 修复：生成更准确的时间描述
                if time_range_hours == 1:
                    time_desc = "最近1小时"
                elif time_range_hours == 24:
                    time_desc = "最近24小时"
                elif time_range_hours == 48:
                    time_desc = "最近48小时"
                elif time_range_hours == 72:
                    time_desc = "最近3天"
                elif time_range_hours == 168:
                    time_desc = "最近7天"
                elif time_range_hours == 720:
                    time_desc = "最近30天"
                else:
                    time_desc = f"最近{time_range_hours}小时"

                logger.info(f"查询{time_desc}的数据，时间范围参数: {time_range_hours}")

            records = cursor.fetchall()
            logger.info(f"从数据库获取到{len(records)}条记录")

            # 统计数据
            total_records = len(records)
            total_violations = 0

            violations_by_type = {}
            violations_by_camera = {}
            violations_by_hour = {}
            recent_records = []

            for record in records:
                try:
                    # 解析违规数据
                    violation_data = json.loads(record['violation_data'])
                    violations = violation_data.get('violations', {})

                    # 按类型统计
                    for vtype, count in violations.items():
                        if isinstance(count, (int, float)) and count > 0:
                            violations_by_type[vtype] = violations_by_type.get(vtype, 0) + count
                            total_violations += count

                    # 按摄像头统计
                    camera_id = record['camera_id']
                    violations_by_camera[camera_id] = violations_by_camera.get(camera_id, 0) + record[
                        'total_violations']

                    # 按小时统计
                    hour = record['detection_timestamp'].hour
                    violations_by_hour[hour] = violations_by_hour.get(hour, 0) + record['total_violations']

                    # 最近记录
                    if len(recent_records) < 10:
                        recent_records.append({
                            'camera_id': camera_id,
                            'timestamp': record['detection_timestamp'].isoformat(),
                            'violations': violations,
                            'total_violations': record['total_violations'],
                            'record_id': record['id']
                        })

                except json.JSONDecodeError as e:
                    logger.error(f"解析违规数据失败: {e}")
                    camera_id = record['camera_id']
                    violations_by_camera[camera_id] = violations_by_camera.get(camera_id, 0) + record[
                        'total_violations']
                    total_violations += record['total_violations']
                    continue

            cursor.close()
            conn.close()

            logger.info(f"数据统计完成: {total_records}条记录, {total_violations}次违规，时间描述: {time_desc}")

            return {
                'summary': {
                    'total_records': total_records,
                    'total_violations': total_violations,
                    'active_cameras': len(violations_by_camera),
                    'time_range_hours': time_range_hours if not query_all else 0,
                    'time_description': time_desc,
                    'query_all': query_all
                },
                'violations_by_type': violations_by_type,
                'violations_by_camera': violations_by_camera,
                'violations_by_hour': violations_by_hour,
                'recent_records': recent_records
            }

        except mysql.connector.Error as err:
            logger.error(f"查询违规数据失败: {err}")
            if conn:
                conn.close()
            return {}

    def analyze_query_smart(self, query: str, violation_data: Dict) -> str:
        """智能分析查询"""

        logger.info(f"智能分析查询: {query}")

        summary = violation_data.get('summary', {})
        violations_by_type = violation_data.get('violations_by_type', {})
        violations_by_camera = violation_data.get('violations_by_camera', {})
        violations_by_hour = violation_data.get('violations_by_hour', {})

        query_lower = query.lower()

        # 摄像头排名查询
        if any(keyword in query_lower for keyword in ['哪个', '哪里', '最多', '最高', '排名', '摄像头']):
            return self.analyze_camera_ranking_fixed(violation_data)

        # 口罩相关查询
        elif any(keyword in query_lower for keyword in ['口罩', 'mask']):
            return self.analyze_mask_detailed_fixed(violation_data)

        # 帽子相关查询
        elif any(keyword in query_lower for keyword in ['帽子', 'hat', '工作帽']):
            return self.analyze_hat_detailed_fixed(violation_data)

        # 手机相关查询
        elif any(keyword in query_lower for keyword in ['手机', 'phone']):
            return self.analyze_phone_detailed_fixed(violation_data)

        # 吸烟相关查询
        elif any(keyword in query_lower for keyword in ['吸烟', 'smoking', '烟']):
            return self.analyze_smoking_detailed_fixed(violation_data)

        # 风险评估查询
        elif any(keyword in query_lower for keyword in ['风险', '危险', '安全']):
            return self.analyze_risk_detailed_fixed(violation_data)

        # 趋势分析查询
        elif any(keyword in query_lower for keyword in ['趋势', '变化', '对比']):
            return self.analyze_trends_detailed_fixed(violation_data)

        # 建议相关查询
        elif any(keyword in query_lower for keyword in ['建议', '改进', '措施', '怎么办']):
            return self.generate_suggestions_detailed_fixed(violation_data)

        # 时间相关查询
        elif any(keyword in query_lower for keyword in ['今天', '昨天', '本周', 'today', 'yesterday']):
            return self.analyze_time_specific_fixed(query, violation_data)

        # 默认综合分析
        else:
            return self.analyze_comprehensive_overview_fixed(violation_data)

    def analyze_camera_ranking_fixed(self, violation_data: Dict) -> str:
        """修复版摄像头违规排名分析"""
        violations_by_camera = violation_data.get('violations_by_camera', {})
        summary = violation_data.get('summary', {})

        if not violations_by_camera:
            return f"基于{summary.get('time_description', '当前数据范围')}，暂无摄像头违规数据可供排名分析。"

        # 按违规次数排序
        camera_ranking = sorted(violations_by_camera.items(), key=lambda x: x[1], reverse=True)
        total_violations = summary.get('total_violations', 0)

        result = f"📊 摄像头违规排名分析（基于{summary.get('time_description', '数据范围')}）\n\n"
        result += "🏆 违规排行榜：\n"

        for i, (camera_id, count) in enumerate(camera_ranking[:5], 1):
            percentage = (count / total_violations * 100) if total_violations > 0 else 0
            camera_display = self.get_camera_display_name(camera_id)
            result += f"{i}. {camera_display}: {count}次违规 ({percentage:.1f}%)\n"

        # 重点分析违规最多的摄像头
        top_camera = camera_ranking[0]
        top_camera_id, top_count = top_camera
        top_camera_display = self.get_camera_display_name(top_camera_id)
        top_percentage = (top_count / total_violations * 100) if total_violations > 0 else 0

        result += f"\n🔍 重点关注摄像头：\n"
        result += f"• {top_camera_display} 违规最多，共{top_count}次\n"
        result += f"• 占总违规的 {top_percentage:.1f}%，需要重点管理\n"

        result += f"\n💡 改进建议：\n"
        result += f"• 重点检查{top_camera_display}监控区域的管理制度执行情况\n"
        result += f"• 加强该区域的现场监督和培训\n"
        result += f"• 分析该区域违规频发的根本原因\n"
        result += f"• 建立违规记录档案，定期回顾分析"

        return result

    def analyze_risk_detailed_fixed(self, violation_data: Dict) -> str:
        """修复版详细风险评估"""
        violations_by_type = violation_data.get('violations_by_type', {})
        summary = violation_data.get('summary', {})

        if not violations_by_type:
            return "✅ 风险评估：当前无安全风险，系统运行正常"

        # 修复：调整风险计算逻辑
        risk_score = 0
        high_risk_items = []

        # 计算基础风险分数
        for vtype, count in violations_by_type.items():
            weight = self.risk_weights.get(vtype, 1)
            # 修复：限制单项最大贡献，避免分数过高
            item_score = min(weight * count, 50)  # 单项最多贡献50分
            risk_score += item_score

            if weight >= 6:  # 高风险项目
                violation_name = self.violation_mapping.get(vtype, vtype)
                high_risk_items.append(f'{violation_name}({count}次)')

        # 修复：设置风险分数上限
        risk_score = min(risk_score, 100)  # 最高100分

        # 风险等级判定
        if risk_score >= 80:
            risk_level = '🔴 高风险'
            risk_desc = '存在严重安全隐患，需要立即采取措施'
        elif risk_score >= 50:
            risk_level = '🟡 中风险'
            risk_desc = '存在一定安全风险，需要及时关注和改进'
        elif risk_score >= 20:
            risk_level = '🟠 低-中风险'
            risk_desc = '存在轻微到中等问题，建议持续关注'
        elif risk_score > 0:
            risk_level = '🟢 低风险'
            risk_desc = '存在轻微问题，建议持续关注'
        else:
            risk_level = '✅ 无风险'
            risk_desc = '当前状况良好'

        result = f"🎯 安全风险评估报告\n\n"
        result += f"📊 风险等级：{risk_level} (分数: {risk_score}/100)\n"
        result += f"📋 评估结果：{risk_desc}\n\n"

        if high_risk_items:
            result += f"⚠️ 高风险项目：{', '.join(high_risk_items)}\n\n"

        # 详细的风险因子分析
        result += "🔍 风险因子分析：\n"
        sorted_violations = sorted(violations_by_type.items(), key=lambda x: self.risk_weights.get(x[0], 1) * x[1],
                                   reverse=True)
        for vtype, count in sorted_violations[:5]:
            violation_name = self.violation_mapping.get(vtype, vtype)
            weight = self.risk_weights.get(vtype, 1)
            contribution = min(weight * count, 50)
            result += f"• {violation_name}: {count}次 (风险贡献: {contribution}分)\n"

        result += "\n💡 风险缓解建议：\n"
        if risk_score >= 80:
            result += "• 🚨 立即停止高风险作业，排查安全隐患\n"
            result += "• 📋 召集紧急会议制定应对措施\n"
            result += "• 👥 加强现场安全监督"
        elif risk_score >= 50:
            result += "• 📋 制定详细的改进计划\n"
            result += "• 🔍 增加安全检查频次\n"
            result += "• 👨‍🏫 加强员工安全意识培训"
        else:
            result += "• ✅ 继续保持现有安全标准\n"
            result += "• 📊 定期进行安全评估\n"
            result += "• 🔄 持续改进管理制度"

        return result

    def analyze_mask_detailed_fixed(self, violation_data: Dict) -> str:
        """修复版详细分析口罩佩戴情况"""
        violations_by_type = violation_data.get('violations_by_type', {})
        violations_by_camera = violation_data.get('violations_by_camera', {})
        summary = violation_data.get('summary', {})

        # 统计口罩相关违规
        mask_violations = 0
        for vtype, count in violations_by_type.items():
            if 'mask' in vtype.lower():
                mask_violations += count

        total_violations = summary.get('total_violations', 0)

        result = f"😷 口罩佩戴合规分析（基于{summary.get('time_description', '数据范围')}）\n\n"

        if mask_violations == 0:
            result += "✅ 优秀表现：未检测到任何口罩违规行为\n"
            result += f"• 在{summary.get('total_records', 0)}次检测中，口罩佩戴100%合规\n"
            result += "• 员工安全防护意识强，值得表扬\n\n"
            result += "🎯 保持建议：\n"
            result += "• 继续保持良好的口罩佩戴习惯\n"
            result += "• 定期检查口罩供应和质量\n"
            result += "• 持续开展安全意识教育"
        else:
            mask_percentage = (mask_violations / total_violations * 100) if total_violations > 0 else 0

            # 判断风险等级
            if mask_percentage > 40:
                risk_level = "🔴 高风险"
                urgency = "需要立即整改"
            elif mask_percentage > 20:
                risk_level = "🟡 中风险"
                urgency = "需要及时关注"
            else:
                risk_level = "🟢 低风险"
                urgency = "建议持续改进"

            result += f"📊 违规统计：\n"
            result += f"• 口罩违规次数：{mask_violations}次\n"
            result += f"• 占总违规比例：{mask_percentage:.1f}%\n"
            result += f"• 风险等级：{risk_level}\n"
            result += f"• 处理建议：{urgency}\n\n"

            # 分析各摄像头的情况
            result += "📍 各摄像头违规分布：\n"
            for camera_id, total_count in violations_by_camera.items():
                camera_display = self.get_camera_display_name(camera_id)
                percentage = (total_count / total_violations * 100) if total_violations > 0 else 0
                result += f"• {camera_display}: {total_count}次违规 ({percentage:.1f}%)\n"

            result += "\n🎯 改进措施：\n"
            if mask_percentage > 40:
                result += "• 🚨 立即检查口罩供应是否充足\n"
                result += "• 📋 开展紧急口罩佩戴培训\n"
                result += "• 👥 安排专人监督口罩佩戴\n"
                result += "• 📌 在所有入口设置佩戴提醒"
            elif mask_percentage > 20:
                result += "• 📋 加强口罩佩戴宣传教育\n"
                result += "• 🔍 增加现场检查频次\n"
                result += "• 📦 确保口罩供应充足\n"
                result += "• 👨‍🏫 开展规范佩戴培训"
            else:
                result += "• 🔄 定期提醒员工正确佩戴\n"
                result += "• 📊 持续监控佩戴情况\n"
                result += "• 🏆 建立佩戴表彰机制"

        return result

    def analyze_hat_detailed_fixed(self, violation_data: Dict) -> str:
        """修复版详细分析工作帽佩戴情况"""
        violations_by_type = violation_data.get('violations_by_type', {})
        summary = violation_data.get('summary', {})

        hat_violations = 0
        for vtype, count in violations_by_type.items():
            if 'hat' in vtype.lower():
                hat_violations += count

        total_violations = summary.get('total_violations', 0)

        result = f"👷 工作帽佩戴合规分析（基于{summary.get('time_description', '数据范围')}）\n\n"

        if hat_violations == 0:
            result += "✅ 工作帽佩戴合规率：100%\n"
            result += "• 所有员工均正确佩戴工作帽\n"
            result += "• 食品安全防护措施到位"
        else:
            hat_percentage = (hat_violations / total_violations * 100) if total_violations > 0 else 0
            result += f"📊 工作帽违规：{hat_violations}次 ({hat_percentage:.1f}%)\n"
            result += "🎯 建议：加强工作帽佩戴培训，确保食品安全标准"

        return result

    def analyze_phone_detailed_fixed(self, violation_data: Dict) -> str:
        """修复版详细分析手机使用情况"""
        violations_by_type = violation_data.get('violations_by_type', {})
        summary = violation_data.get('summary', {})

        phone_violations = 0
        for vtype, count in violations_by_type.items():
            if 'phone' in vtype.lower():
                phone_violations += count

        result = f"📱 手机使用规范分析（基于{summary.get('time_description', '数据范围')}）\n\n"

        if phone_violations == 0:
            result += "✅ 工作期间手机使用规范，未发现违规"
        else:
            total_violations = summary.get('total_violations', 0)
            phone_percentage = (phone_violations / total_violations * 100) if total_violations > 0 else 0
            result += f"📊 手机使用违规：{phone_violations}次 ({phone_percentage:.1f}%)\n"
            result += "🎯 建议：制定手机使用规定，设置存放区域"

        return result

    def analyze_smoking_detailed_fixed(self, violation_data: Dict) -> str:
        """修复版详细分析吸烟行为"""
        violations_by_type = violation_data.get('violations_by_type', {})
        summary = violation_data.get('summary', {})

        smoking_violations = 0
        for vtype, count in violations_by_type.items():
            if any(keyword in vtype.lower() for keyword in ['smoking', 'cigarette', '烟']):
                smoking_violations += count

        result = f"🚭 吸烟行为监控分析（基于{summary.get('time_description', '数据范围')}）\n\n"

        if smoking_violations == 0:
            result += "✅ 禁烟规定执行良好，未检测到吸烟违规"
        else:
            result += f"🚨 严重警告：检测到{smoking_violations}次吸烟违规！\n"
            result += "🎯 紧急措施：\n"
            result += "• 立即加强禁烟监督\n"
            result += "• 设置明显禁烟标识\n"
            result += "• 建立严格处罚机制\n"
            result += "• 开展消防安全培训"

        return result

    def analyze_trends_detailed_fixed(self, violation_data: Dict) -> str:
        """修复版详细趋势分析"""
        violations_by_hour = violation_data.get('violations_by_hour', {})
        summary = violation_data.get('summary', {})

        if not violations_by_hour:
            return f"📈 违规趋势分析\n\n基于{summary.get('time_description', '当前数据')}，数据量不足以进行详细趋势分析。建议积累更多数据后重新分析。"

        peak_hours = sorted(violations_by_hour.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_hours_text = [f"{hour}点({count}次)" for hour, count in peak_hours if count > 0]

        result = f"📈 违规趋势分析\n\n"
        result += f"⏰ 高发时段：{', '.join(peak_hours_text) if peak_hours_text else '无明显高发时段'}\n"
        if peak_hours_text:
            result += f"💡 建议：在{peak_hours[0][0]}点等时段加强监督管理"

        return result

    def generate_suggestions_detailed_fixed(self, violation_data: Dict) -> str:
        """修复版生成详细改进建议"""
        violations_by_type = violation_data.get('violations_by_type', {})
        violations_by_camera = violation_data.get('violations_by_camera', {})
        summary = violation_data.get('summary', {})

        if not violations_by_type:
            return f"✅ 改进建议\n\n基于{summary.get('time_description', '当前数据')}的表现优秀，建议继续保持现有管理标准。"

        result = f"💡 改进建议方案（基于{summary.get('time_description', '数据范围')}）\n\n"

        # 按严重程度排序
        sorted_violations = sorted(violations_by_type.items(),
                                   key=lambda x: self.risk_weights.get(x[0], 1) * x[1],
                                   reverse=True)

        result += "🎯 优先改进项目：\n"
        for i, (vtype, count) in enumerate(sorted_violations[:3], 1):
            violation_name = self.violation_mapping.get(vtype, vtype)
            result += f"{i}. {violation_name}：{count}次违规\n"

        # 摄像头重点关注
        if violations_by_camera:
            worst_camera = max(violations_by_camera.items(), key=lambda x: x[1])
            camera_display = self.get_camera_display_name(worst_camera[0])
            result += f"\n📍 重点关注摄像头：{camera_display}（{worst_camera[1]}次违规）\n"

        result += "\n🔧 系统性改进措施：\n"
        result += "• 建立违规行为登记制度\n"
        result += "• 定期开展安全培训\n"
        result += "• 制定奖惩机制\n"
        result += "• 持续监控和数据分析"

        return result

    def analyze_time_specific_fixed(self, query: str, violation_data: Dict) -> str:
        """修复版分析特定时间的情况"""
        summary = violation_data.get('summary', {})
        violations_by_type = violation_data.get('violations_by_type', {})

        time_desc = summary.get('time_description', '指定时间范围')
        total_violations = summary.get('total_violations', 0)

        result = f"📅 违规情况分析（{time_desc}）\n\n"
        result += f"📊 总违规次数：{total_violations}次\n"
        result += f"📝 检测记录数：{summary.get('total_records', 0)}条\n"
        result += f"📹 活跃摄像头：{summary.get('active_cameras', 0)}个\n\n"

        if violations_by_type:
            result += "🔍 主要违规类型：\n"
            sorted_types = sorted(violations_by_type.items(), key=lambda x: x[1], reverse=True)
            for vtype, count in sorted_types[:5]:
                violation_name = self.violation_mapping.get(vtype, vtype)
                percentage = (count / total_violations * 100) if total_violations > 0 else 0
                result += f"• {violation_name}：{count}次 ({percentage:.1f}%)\n"

        # 基于数据量给出评估
        if total_violations == 0:
            result += "\n✅ 评估：当前时段表现优秀，未发现违规行为"
        elif total_violations <= 10:
            result += "\n✅ 评估：违规情况较少，整体可控"
        elif total_violations <= 50:
            result += "\n⚠️ 评估：存在一定违规，需要关注"
        else:
            result += "\n🚨 评估：违规较多，需要重点管理"

        return result

    def analyze_comprehensive_overview_fixed(self, violation_data: Dict) -> str:
        """修复版综合概览分析"""
        summary = violation_data.get('summary', {})
        violations_by_type = violation_data.get('violations_by_type', {})
        violations_by_camera = violation_data.get('violations_by_camera', {})

        result = f"📊 餐饮环境安全综合分析报告\n\n"

        # 数据概览
        result += f"📈 数据概览（{summary.get('time_description', '数据范围')}）：\n"
        result += f"• 检测记录：{summary.get('total_records', 0)}条\n"
        result += f"• 违规总数：{summary.get('total_violations', 0)}次\n"
        result += f"• 监控摄像头：{summary.get('active_cameras', 0)}个\n\n"

        # 违规类型分析
        if violations_by_type:
            result += "🔍 违规类型分析：\n"
            sorted_types = sorted(violations_by_type.items(), key=lambda x: x[1], reverse=True)
            for vtype, count in sorted_types:
                violation_name = self.violation_mapping.get(vtype, vtype)
                percentage = (count / summary.get('total_violations', 1)) * 100
                result += f"• {violation_name}：{count}次 ({percentage:.1f}%)\n"
            result += "\n"

        # 摄像头分析
        if violations_by_camera:
            result += "📍 摄像头违规分析：\n"
            sorted_cameras = sorted(violations_by_camera.items(), key=lambda x: x[1], reverse=True)
            for camera_id, count in sorted_cameras:
                camera_display = self.get_camera_display_name(camera_id)
                percentage = (count / summary.get('total_violations', 1)) * 100
                result += f"• {camera_display}：{count}次 ({percentage:.1f}%)\n"
            result += "\n"

        # 总体评估
        total_violations = summary.get('total_violations', 0)
        if total_violations == 0:
            result += "✅ 总体评估：优秀，当前管理规范"
        elif total_violations <= 20:
            result += "✅ 总体评估：良好，存在少量可改进项"
        elif total_violations <= 100:
            result += "⚠️ 总体评估：一般，需要加强管理"
        else:
            result += "🚨 总体评估：需要重点改进"

        return result

    def generate_direct_answer(self, query: str, violation_data: Dict) -> str:
        """生成直接回答 - 修复AI回答提取问题"""
        query_lower = query.lower()
        summary = violation_data.get('summary', {})
        violations_by_type = violation_data.get('violations_by_type', {})
        violations_by_camera = violation_data.get('violations_by_camera', {})

        total_violations = summary.get('total_violations', 0)
        time_desc = summary.get('time_description', '数据范围')

        # 口罩相关查询
        if any(keyword in query_lower for keyword in ['口罩', 'mask']):
            mask_violations = sum(count for vtype, count in violations_by_type.items() if 'mask' in vtype.lower())
            if mask_violations > 0:
                percentage = (mask_violations / total_violations * 100) if total_violations > 0 else 0
                return f"检测到{mask_violations}次口罩违规，占总违规的{percentage:.1f}%"
            else:
                return f"口罩佩戴合规情况良好，未检测到违规行为"

        # 工作帽相关查询
        elif any(keyword in query_lower for keyword in ['帽子', 'hat', '工作帽']):
            hat_violations = sum(count for vtype, count in violations_by_type.items() if 'hat' in vtype.lower())
            if hat_violations > 0:
                percentage = (hat_violations / total_violations * 100) if total_violations > 0 else 0
                return f"检测到{hat_violations}次工作帽违规，占总违规的{percentage:.1f}%"
            else:
                return f"工作帽佩戴合规情况良好，未检测到违规行为"

        # 手机相关查询
        elif any(keyword in query_lower for keyword in ['手机', 'phone']):
            phone_violations = sum(count for vtype, count in violations_by_type.items() if 'phone' in vtype.lower())
            if phone_violations > 0:
                percentage = (phone_violations / total_violations * 100) if total_violations > 0 else 0
                return f"检测到{phone_violations}次手机使用违规，占总违规的{percentage:.1f}%"
            else:
                return f"手机使用规范，未检测到违规行为"

        # 吸烟相关查询
        elif any(keyword in query_lower for keyword in ['吸烟', 'smoking', '烟']):
            smoking_violations = sum(count for vtype, count in violations_by_type.items()
                                     if any(keyword in vtype.lower() for keyword in ['smoking', 'cigarette', '烟']))
            if smoking_violations > 0:
                return f"严重警告：检测到{smoking_violations}次吸烟违规！"
            else:
                return f"禁烟规定执行良好，未检测到吸烟违规"

        # 摄像头排名查询
        elif any(keyword in query_lower for keyword in ['哪个', '哪里', '最多', '最高', '排名', '摄像头']):
            if violations_by_camera:
                top_camera = max(violations_by_camera.items(), key=lambda x: x[1])
                camera_display = self.get_camera_display_name(top_camera[0])
                percentage = (top_camera[1] / total_violations * 100) if total_violations > 0 else 0
                return f"{camera_display}违规最多，共{top_camera[1]}次违规，占总违规的{percentage:.1f}%"
            else:
                return f"暂无摄像头违规数据可供分析"

        # 风险评估查询
        elif any(keyword in query_lower for keyword in ['风险', '危险', '安全']):
            # 计算风险分数
            risk_score = 0
            for vtype, count in violations_by_type.items():
                weight = self.risk_weights.get(vtype, 1)
                risk_score += min(weight * count, 50)
            risk_score = min(risk_score, 100)

            if risk_score >= 80:
                risk_level = '高风险'
            elif risk_score >= 50:
                risk_level = '中风险'
            elif risk_score >= 20:
                risk_level = '低-中风险'
            elif risk_score > 0:
                risk_level = '低风险'
            else:
                risk_level = '无风险'

            return f"当前安全风险等级为{risk_level}，风险分数{risk_score}/100"

        # 趋势分析查询
        elif any(keyword in query_lower for keyword in ['趋势', '变化', '对比']):
            violations_by_hour = violation_data.get('violations_by_hour', {})
            if violations_by_hour:
                peak_hour = max(violations_by_hour.items(), key=lambda x: x[1])
                return f"违规高发时段为{peak_hour[0]}点，共{peak_hour[1]}次违规"
            else:
                return f"数据量不足以分析违规趋势"

        # 建议相关查询
        elif any(keyword in query_lower for keyword in ['建议', '改进', '措施', '怎么办']):
            if violations_by_type:
                top_violation = max(violations_by_type.items(), key=lambda x: x[1])
                violation_name = self.violation_mapping.get(top_violation[0], top_violation[0])
                return f"主要问题是{violation_name}({top_violation[1]}次)，建议重点改进此类违规"
            else:
                return f"表现优秀，建议继续保持现有管理标准"

        # 默认综合分析
        else:
            if total_violations > 0:
                return f"基于{time_desc}，共检测到{total_violations}次违规，涉及{len(violations_by_camera)}个摄像头"
            else:
                return f"基于{time_desc}，未检测到任何违规行为，管理状况良好"

    def analyze_query(self, query: str, user_time_range_hours: int = 24) -> Dict[str, Any]:
        """分析自然语言查询 - 修复AI回答和时间范围显示问题"""
        logger.info(f"处理查询: {query}, 用户时间范围: {user_time_range_hours}")

        # 修复：确保时间范围参数有效
        if user_time_range_hours is None:
            user_time_range_hours = 24
            logger.warning("用户时间范围为None，设置为默认24小时")

        # 智能时间范围检测
        smart_time_range = self.smart_time_range_detection(query, user_time_range_hours)

        # 检查是否查询所有数据
        query_all = False
        if any(keyword in query for keyword in ['所有', '全部', '历史', 'all']):
            query_all = True
            smart_time_range = 0
            logger.info("检测到查询所有数据的请求")

        # 获取数据
        data = self.get_violation_data(smart_time_range, query_all)

        if not data or data['summary']['total_records'] == 0:
            return {
                'success': True,
                'query': query,
                'analysis': {
                    'direct_answer': f'在{data.get("summary", {}).get("time_description", "指定时间范围")}内没有检测到违规数据。',
                    'detailed_explanation': f'系统在{data.get("summary", {}).get("time_description", "指定时间范围")}内未发现任何违规行为，表明当前管理状况良好。建议继续保持现有管理标准，定期检查系统运行状态。',
                    'suggestions': [
                        '继续保持现有管理标准',
                        '定期检查检测系统运行状态',
                        '保持员工培训和安全意识教育',
                        '建立预防性管理机制'
                    ]
                },
                'data_summary': data.get('summary', {}),
                'query_info': {
                    'query_all_data': query_all,
                    'user_selected_hours': user_time_range_hours,
                    'smart_detected_hours': smart_time_range,
                    'time_range_adjusted': smart_time_range != user_time_range_hours,
                    'janus_model_available': self.janus_model is not None,
                    'analysis_method': 'smart_time_range_engine'
                }
            }

        # 使用智能规则分析
        logger.info("使用智能时间范围引擎进行分析")

        # 修复：生成直接回答
        direct_answer = self.generate_direct_answer(query, data)

        # 生成详细分析
        analysis_text = self.analyze_query_smart(query, data)

        # 修复：改进分析结果解析
        analysis_result = self.parse_analysis_result_fixed_v2(analysis_text, query, data, direct_answer)

        return {
            'success': True,
            'query': query,
            'analysis': analysis_result,
            'data_summary': data['summary'],
            'query_info': {
                'query_all_data': query_all,
                'user_selected_hours': user_time_range_hours,
                'smart_detected_hours': smart_time_range,
                'time_range_adjusted': smart_time_range != user_time_range_hours,
                'janus_model_available': self.janus_model is not None,
                'analysis_method': 'smart_time_range_engine'
            },
            'timestamp': datetime.datetime.now().isoformat()
        }

    def parse_analysis_result_fixed_v2(self, analysis_text: str, query: str, data: Dict, direct_answer: str) -> Dict[
        str, Any]:
        """修复版2.0 - 解析分析结果，修复AI回答提取问题"""

        # 从分析文本中提取改进建议
        suggestions = []
        lines = [line.strip() for line in analysis_text.split('\n') if line.strip()]

        # 查找建议相关的行
        in_suggestions_section = False
        for line in lines:
            if any(keyword in line for keyword in ['改进建议', '改进措施', '🎯', '💡', '建议']):
                in_suggestions_section = True
                continue

            if in_suggestions_section and line.startswith('•'):
                clean_suggestion = line.lstrip('• ').strip()
                if len(clean_suggestion) > 5:  # 过滤太短的建议
                    suggestions.append(clean_suggestion)
            elif in_suggestions_section and not line.startswith('•') and len(line) > 20:
                # 如果遇到非建议行且比较长，说明建议部分结束
                break

        # 如果没有找到建议，生成默认建议
        if not suggestions:
            query_lower = query.lower()
            if '风险' in query_lower:
                suggestions = [
                    '定期进行安全风险评估',
                    '建立风险预警机制',
                    '加强高风险区域监管',
                    '制定应急预案'
                ]
            elif '摄像头' in query_lower or '哪个' in query_lower:
                suggestions = [
                    '重点监管违规频发区域',
                    '分析违规原因并制定对策',
                    '加强现场管理和培训',
                    '建立定期检查制度'
                ]
            elif '口罩' in query_lower:
                suggestions = [
                    '确保口罩供应充足',
                    '加强口罩佩戴培训',
                    '设置佩戴提醒标识',
                    '建立佩戴检查制度'
                ]
            elif '帽子' in query_lower or '工作帽' in query_lower:
                suggestions = [
                    '确保工作帽供应充足',
                    '加强工作帽佩戴培训',
                    '设置佩戴提醒标识',
                    '建立佩戴检查制度'
                ]
            elif '手机' in query_lower:
                suggestions = [
                    '制定手机使用规定',
                    '设置手机存放区域',
                    '加强手机使用管理培训',
                    '建立违规处罚机制'
                ]
            elif '吸烟' in query_lower:
                suggestions = [
                    '立即加强禁烟监督',
                    '设置明显禁烟标识',
                    '建立严格处罚机制',
                    '开展消防安全培训'
                ]
            else:
                suggestions = [
                    '持续监控违规数据变化',
                    '定期分析违规趋势和模式',
                    '根据分析结果制定针对性改进措施',
                    '加强重点区域的现场管理'
                ]

        return {
            'direct_answer': direct_answer,
            'detailed_explanation': analysis_text,
            'suggestions': suggestions[:6]  # 限制建议数量
        }


# 创建分析器实例
analyzer = SmartTimeRangeAnalyzer()


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        return jsonify({
            'status': 'healthy',
            'service': 'Fixed Janus查询分析服务',
            'version': '3.3.0',
            'fixes': [
                '修复AI回答提取问题 - 生成准确的直接回答',
                '修复时间范围undefined显示问题',
                '智能时间范围检测优化',
                '改进分析结果解析v2.0',
                '优化各类查询的直接回答生成'
            ],
            'capabilities': {
                'natural_language_query': True,
                'smart_time_range_detection': True,
                'fixed_response_parsing': True,
                'accurate_direct_answers': True,
                'real_data_analysis': True,
                'detailed_violation_analysis': True,
                'janus_pro_integration': analyzer.janus_model is not None
            },
            'janus_model_status': 'loaded' if analyzer.janus_model is not None else 'not_available',
            'analysis_method': 'smart_time_range_engine_v2',
            'timestamp': datetime.datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/api/query', methods=['POST'])
def natural_language_query():
    """自然语言查询接口 - 修复版"""
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': '缺少查询参数'
            }), 400

        query = data['query']

        # 修复：确保时间范围参数正确处理
        user_time_range_hours = data.get('time_range_hours', 24)

        logger.info(f"接收到原始时间范围参数: {user_time_range_hours}, 类型: {type(user_time_range_hours)}")

        # 处理各种可能的无效值
        if user_time_range_hours is None or user_time_range_hours == 'undefined' or user_time_range_hours == '':
            user_time_range_hours = 24
            logger.warning(f"时间范围参数无效(None/undefined/空)，使用默认值24小时")

        try:
            user_time_range_hours = int(float(user_time_range_hours))  # 先转float再转int，处理字符串数字
            if user_time_range_hours <= 0:
                user_time_range_hours = 24
                logger.warning(f"时间范围参数≤0，使用默认值24小时")
        except (ValueError, TypeError) as e:
            user_time_range_hours = 24
            logger.warning(f"时间范围参数转换失败: {e}，使用默认值24小时")

        logger.info(f"处理查询: {query}, 最终时间范围: {user_time_range_hours}小时")

        # 执行智能时间范围分析
        result = analyzer.analyze_query(query, user_time_range_hours)

        # 确保返回的时间描述正确
        if 'data_summary' in result and 'time_description' in result['data_summary']:
            logger.info(f"分析完成，时间范围: {result['data_summary']['time_description']}")
        else:
            logger.warning("返回结果中缺少时间描述信息")

        return jsonify(result)

    except Exception as e:
        logger.error(f"查询处理失败: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/data-summary', methods=['GET'])
def get_data_summary():
    """获取数据摘要"""
    try:
        time_range_hours = int(request.args.get('hours', 24))
        data = analyzer.get_violation_data(time_range_hours)

        return jsonify({
            'success': True,
            'data': data,
            'janus_model_available': analyzer.janus_model is not None,
            'timestamp': datetime.datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"获取Janus状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/janus/status', methods=['GET'])
def get_janus_status():
   """获取Janus-Pro模型状态"""
   try:
       return jsonify({
           'success': True,
           'janus_model_loaded': analyzer.janus_model is not None,
           'model_path': "./models/janus-pro-1b",
           'model_available': os.path.exists("./models/janus-pro-1b"),
           'analysis_method': 'smart_time_range_engine_v2',
           'new_features': [
               'Fixed AI answer extraction',
               'Fixed time range undefined display',
               'Smart time range detection',
               'Accurate direct answer generation',
               'Context-aware time descriptions'
           ],
           'capabilities': {
               'smart_time_detection': True,
               'fixed_format_parsing': True,
               'accurate_direct_answers': True,
               'context_aware_analysis': True,
               'multimodal_understanding': analyzer.janus_model is not None,
           },
           'timestamp': datetime.datetime.now().isoformat()
       })
   except Exception as e:
       logger.error(f"获取Janus状态失败: {str(e)}")
       return jsonify({
           'success': False,
           'error': str(e)
       }), 500


if __name__ == '__main__':
    try:
        print("启动Fixed Janus查询分析服务...")
        print("主要修复:")
        print("  1. ✅ 修复AI回答提取问题 - 针对不同查询类型生成准确的直接回答")
        print("  2. ✅ 修复时间范围undefined显示 - 确保时间参数正确处理和显示")
        print("  3. ✅ 智能时间范围检测 - 自动识别'今天'、'本周'等词汇")
        print("  4. ✅ 改进分析结果解析 - 避免重复标题和格式问题")
        print("  5. ✅ 优化各类查询处理 - 口罩、风险、趋势等查询的准确回答")
        print()
        print("修复效果预览:")
        print("  口罩查询 → '检测到X次口罩违规，占总违规的X%'")
        print("  风险查询 → '当前安全风险等级为X风险，风险分数X/100'")
        print("  摄像头查询 → 'X摄像头违规最多，共X次违规，占总违规的X%'")
        print("  趋势查询 → '违规高发时段为X点，共X次违规'")
        print("  时间范围 → '最近24小时' 而不是 'undefined'")
        print()
        print("数据源: violations_records表")
        print("分析引擎: 智能时间范围引擎 v2.0")
        print("服务地址: http://localhost:5001")

        if analyzer.janus_model is not None:
            print("✅ Janus-Pro模型已加载，支持多模态分析")
        else:
            print("⚠️ Janus-Pro模型未加载，使用智能规则引擎")

        print("\n修复前后对比:")
        print("修复前:")
        print("  查询问题: 口罩佩戴情况怎么样？")
        print("  分析范围: 基于最近undefined小时的数据")
        print("  AI回答: • cam_34摄像头: 39次违规 (4.0%)")
        print()
        print("修复后:")
        print("  查询问题: 口罩佩戴情况怎么样？")
        print("  分析范围: 基于最近24小时的数据")
        print("  AI回答: 检测到503次口罩违规，占总违规的52.1%")

        print("\n现在可以测试修复效果！")

        app.run(
            host='0.0.0.0',
            port=5001,
            debug=False,
            threaded=True
        )

    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        print(f"服务启动失败: {str(e)}")



