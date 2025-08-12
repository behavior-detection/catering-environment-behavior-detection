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


class EnhancedViolationDataAnalyzer:
    """增强的基于真实违规数据的分析器 - 集成Janus-Pro"""

    def __init__(self):
        self.violation_mapping = {
            'no_mask': '未佩戴口罩',
            'no_hat': '未佩戴工作帽',
            'phone_usage': '使用手机',
            'smoking': '吸烟行为',
            'mouse_infestation': '鼠患问题',
            'uniform_violation': '工作服违规',
            'mask': '口罩问题',
            'hat': '工作帽问题',
            'phone': '手机使用',
            'cigarette': '吸烟',
            'mouse': '鼠患',
            'uniform': '工作服问题'
        }

        self.risk_severity = {
            'mouse_infestation': 10,
            'mouse': 10,
            'smoking': 9,
            'cigarette': 9,
            'no_mask': 6,
            'mask': 6,
            'no_hat': 4,
            'hat': 4,
            'phone_usage': 3,
            'phone': 3,
            'uniform_violation': 2,
            'uniform': 2
        }

        # 尝试加载Janus-Pro模型
        self.janus_model = None
        self.load_janus_model()

    def load_janus_model(self):
        """加载Janus-Pro模型"""
        try:
            # 检查模型路径
            model_path = "./models/janus-pro-1b"
            if not os.path.exists(model_path):
                logger.warning(f"Janus-Pro模型路径不存在: {model_path}")
                return

            # 尝试导入transformers
            try:
                from transformers import AutoModelForCausalLM, AutoProcessor
                import torch

                logger.info("正在加载Janus-Pro-1B模型...")

                # 加载处理器和模型
                self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
                self.janus_model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    trust_remote_code=True,
                    torch_dtype=torch.bfloat16,
                    device_map="auto"
                )

                logger.info("✅ Janus-Pro-1B模型加载成功")

            except ImportError as e:
                logger.warning(f"无法导入transformers库: {e}")
            except Exception as e:
                logger.error(f"加载Janus-Pro模型失败: {e}")

        except Exception as e:
            logger.error(f"初始化Janus-Pro模型失败: {e}")

    def use_janus_for_analysis(self, query: str, violation_data: Dict) -> str:
        """使用Janus-Pro进行智能分析"""
        if self.janus_model is None:
            return self.fallback_analysis(query, violation_data)

        try:
            # 构建分析提示
            prompt = self.build_analysis_prompt(query, violation_data)

            # 使用Janus-Pro生成分析
            inputs = self.processor(prompt, return_tensors="pt")

            with torch.no_grad():
                outputs = self.janus_model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.processor.tokenizer.eos_token_id
                )

            response = self.processor.decode(outputs[0], skip_special_tokens=True)

            # 提取生成的部分
            if prompt in response:
                response = response.replace(prompt, "").strip()

            logger.info("✅ Janus-Pro分析完成")
            return response

        except Exception as e:
            logger.error(f"Janus-Pro分析失败: {e}")
            return self.fallback_analysis(query, violation_data)

    def build_analysis_prompt(self, query: str, violation_data: Dict) -> str:
        """构建Janus-Pro分析提示"""
        prompt = f"""你是一个专业的餐饮环境安全分析专家，基于以下真实的违规检测数据回答问题。

违规数据摘要：
- 总违规次数: {violation_data.get('total_violations', 0)}
- 总检测记录: {violation_data.get('total_records', 0)}
- 活跃摄像头: {violation_data.get('active_cameras', 0)}
- 违规类型分布: {json.dumps(violation_data.get('violations_by_type', {}), ensure_ascii=False)}
- 摄像头分布: {json.dumps(violation_data.get('violations_by_camera', {}), ensure_ascii=False)}

用户问题: {query}

请提供专业、准确、具体的分析回答，包含：
1. 直接回答用户问题
2. 基于数据的详细分析
3. 具体的改进建议

回答:"""
        return prompt

    def fallback_analysis(self, query: str, violation_data: Dict) -> str:
        """备用分析方法（当Janus-Pro不可用时）"""
        logger.info("使用备用分析方法")

        # 基于规则的分析
        total_violations = violation_data.get('total_violations', 0)
        violations_by_type = violation_data.get('violations_by_type', {})

        if total_violations == 0:
            return "根据当前数据分析，系统运行状态良好，未检测到违规行为。建议继续保持现有的管理标准。"

        # 找出主要违规类型
        if violations_by_type:
            main_violation = max(violations_by_type.items(), key=lambda x: x[1])
            violation_name = self.violation_mapping.get(main_violation[0], main_violation[0])

            return f"基于真实检测数据分析，当前共检测到{total_violations}次违规，主要问题是{violation_name}（{main_violation[1]}次）。建议重点关注该项目的合规管理。"

        return f"检测到{total_violations}次违规行为，建议加强现场管理和员工培训。"

    def get_db_connection(self):
        """获取数据库连接"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            return conn
        except mysql.connector.Error as err:
            logger.error(f"数据库连接失败: {err}")
            return None

    def get_violation_data(self, time_range_hours: int = 24, query_all: bool = False) -> Dict[str, Any]:
        """从数据库获取真实违规数据"""
        conn = self.get_db_connection()
        if not conn:
            return {}

        try:
            cursor = conn.cursor(dictionary=True)

            # 根据参数决定查询范围
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
                time_desc = f"最近{time_range_hours}小时"
                logger.info(f"查询最近{time_range_hours}小时的数据")

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
                            'total_violations': record['total_violations']
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

            logger.info(f"数据统计完成: {total_records}条记录, {total_violations}次违规")

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

    def analyze_query(self, query: str, time_range_hours: int = 24) -> Dict[str, Any]:
        """分析自然语言查询 - 增强版本"""
        logger.info(f"处理查询: {query}")

        # 检查是否查询特定日期或所有数据
        query_all = False
        if any(keyword in query for keyword in ['所有', '全部', '历史', 'all']):
            query_all = True
            time_range_hours = 0
            logger.info("检测到查询所有数据的请求")

        # 获取真实数据
        data = self.get_violation_data(time_range_hours, query_all)

        if not data or data['summary']['total_records'] == 0:
            return {
                'success': True,
                'query': query,
                'analysis': {
                    'direct_answer': '当前查询范围内没有检测到违规数据。',
                    'detailed_explanation': f'系统在{data.get("summary", {}).get("time_description", "指定时间范围")}内未发现任何违规行为。请检查YOLO检测系统是否正常工作。',
                    'suggestions': [
                        '检查YOLO检测系统是否正常工作',
                        '确认batch_out目录中是否有新的检测数据',
                        '尝试查询更大的时间范围'
                    ]
                },
                'data_summary': data.get('summary', {}),
                'query_info': {
                    'query_all_data': query_all,
                    'time_range_hours': time_range_hours,
                    'janus_model_available': self.janus_model is not None
                }
            }

        # 使用Janus-Pro进行分析（如果可用）
        if self.janus_model is not None:
            logger.info("使用Janus-Pro进行智能分析")
            analysis_text = self.use_janus_for_analysis(query, data)

            # 解析Janus-Pro的回答
            analysis_result = self.parse_janus_response(analysis_text, data)
        else:
            logger.info("Janus-Pro不可用，使用规则引擎分析")
            analysis_result = self.process_natural_language_query(query, data, query_all)

        return {
            'success': True,
            'query': query,
            'analysis': analysis_result,
            'data_summary': data['summary'],
            'query_info': {
                'query_all_data': query_all,
                'time_range_hours': time_range_hours,
                'janus_model_available': self.janus_model is not None,
                'analysis_method': 'janus_pro' if self.janus_model is not None else 'rule_engine'
            },
            'timestamp': datetime.datetime.now().isoformat()
        }

    def parse_janus_response(self, response: str, data: Dict) -> Dict[str, Any]:
        """解析Janus-Pro的回答"""
        # 尝试从回答中提取结构化信息
        lines = response.split('\n')

        direct_answer = ""
        detailed_explanation = ""
        suggestions = []

        current_section = "direct"

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if '建议' in line or '改进' in line:
                current_section = "suggestions"
                continue
            elif '分析' in line or '详细' in line:
                current_section = "detailed"
                continue

            if current_section == "direct" and not direct_answer:
                direct_answer = line
            elif current_section == "detailed":
                detailed_explanation += line + " "
            elif current_section == "suggestions" and line.startswith(('-', '•', '1.', '2.', '3.')):
                suggestions.append(line.lstrip('-•123456789. '))

        # 如果解析失败，使用整个回答作为直接回答
        if not direct_answer:
            direct_answer = response[:200] + "..." if len(response) > 200 else response

        # 确保时间描述正确
        time_desc = data['summary'].get('time_description', '指定时间范围')
        if 'hours' in detailed_explanation or '小时' in detailed_explanation:
            detailed_explanation = detailed_explanation.replace(
                f"过去{data['summary'].get('time_range_hours', 0)}小时",
                time_desc
            ).replace(
                f"最近{data['summary'].get('time_range_hours', 0)}小时",
                time_desc
            )

        return {
            'direct_answer': direct_answer.strip(),
            'detailed_explanation': detailed_explanation.strip(),
            'suggestions': suggestions if suggestions else [
                '继续监控系统运行状态',
                '定期分析违规数据趋势',
                '根据数据制定针对性改进措施'
            ]
        }

    def process_natural_language_query(self, query: str, data: Dict[str, Any], query_all: bool = False) -> Dict[
        str, Any]:
        """处理自然语言查询 - 规则引擎版本"""
        query_lower = query.lower()

        violations_by_type = data['violations_by_type']
        violations_by_camera = data['violations_by_camera']
        summary = data['summary']
        time_desc = summary.get('time_description', '指定时间范围')

        # 查询类型识别
        if any(keyword in query_lower for keyword in ['今天', 'today', '现在', '当前']):
            return self.analyze_current_status(data, time_desc)
        elif any(keyword in query_lower for keyword in ['口罩', 'mask']):
            return self.analyze_specific_violation('mask', data, time_desc)
        elif any(keyword in query_lower for keyword in ['帽子', 'hat', '工作帽']):
            return self.analyze_specific_violation('hat', data, time_desc)
        elif any(keyword in query_lower for keyword in ['手机', 'phone']):
            return self.analyze_specific_violation('phone', data, time_desc)
        elif any(keyword in query_lower for keyword in ['吸烟', 'smoking', '烟']):
            return self.analyze_specific_violation('smoking', data, time_desc)
        elif any(keyword in query_lower for keyword in ['鼠', 'mouse']):
            return self.analyze_specific_violation('mouse', data, time_desc)
        elif any(keyword in query_lower for keyword in ['哪个', '哪里', '最多', '最高', '排名']):
            return self.analyze_ranking_and_distribution(data, time_desc)
        elif any(keyword in query_lower for keyword in ['风险', '危险', '安全']):
            return self.analyze_risk_assessment(data, time_desc)
        elif any(keyword in query_lower for keyword in ['建议', '改进', '措施', '怎么办']):
            return self.generate_improvement_suggestions(data, time_desc)
        elif any(keyword in query_lower for keyword in ['趋势', '变化', '对比']):
            return self.analyze_trends(data, time_desc)
        else:
            return self.analyze_general_overview(data, time_desc)

    def analyze_current_status(self, data: Dict[str, Any], time_desc: str) -> Dict[str, Any]:
        """分析当前状态"""
        summary = data['summary']
        violations_by_type = data['violations_by_type']

        if summary['total_violations'] == 0:
            return {
                'direct_answer': f'在{time_desc}内系统运行状态良好，未检测到任何违规行为。',
                'detailed_explanation': f'在{time_desc}内，{summary["active_cameras"]}个摄像头共进行了{summary["total_records"]}次检测，均未发现违规行为。这表明现场管理规范，员工合规意识较强。',
                'suggestions': [
                    '继续保持现有的管理标准',
                    '定期进行员工培训以维持高合规率',
                    '保持设备正常运行状态'
                ]
            }

        most_common = max(violations_by_type.items(), key=lambda x: x[1]) if violations_by_type else None

        if most_common:
            violation_name = self.violation_mapping.get(most_common[0], most_common[0])

            return {
                'direct_answer': f'在{time_desc}内检测到{summary["total_violations"]}次违规，主要问题是{violation_name}（{most_common[1]}次）。',
                'detailed_explanation': f'在{time_desc}内，系统共检测到{summary["total_violations"]}次违规行为，涉及{len(violations_by_type)}种违规类型。{violation_name}是最主要的问题，占总违规次数的{round(most_common[1] / summary["total_violations"] * 100)}%。',
                'suggestions': self.get_specific_suggestions(most_common[0])
            }

    def analyze_specific_violation(self, violation_keyword: str, data: Dict[str, Any], time_desc: str) -> Dict[
        str, Any]:
        """分析特定违规类型"""
        violations_by_type = data['violations_by_type']
        summary = data['summary']

        related_violations = {}
        for vtype, count in violations_by_type.items():
            if violation_keyword in vtype.lower():
                related_violations[vtype] = count

        if not related_violations:
            violation_display = self.violation_mapping.get(violation_keyword, violation_keyword)
            return {
                'direct_answer': f'在{time_desc}内未检测到{violation_display}相关的违规行为。',
                'detailed_explanation': f'系统在{time_desc}内进行了{summary["total_records"]}次检测，均未发现{violation_display}问题。这表明该项目前管理情况良好。',
                'suggestions': [
                    f'继续保持{violation_display}方面的良好表现',
                    '定期检查相关防护用品供应',
                    '持续进行员工培训'
                ]
            }

        total_related = sum(related_violations.values())
        violation_display = self.violation_mapping.get(violation_keyword, violation_keyword)

        return {
            'direct_answer': f'在{time_desc}内检测到{total_related}次{violation_display}相关违规。',
            'detailed_explanation': f'{violation_display}问题占总违规次数的{round(total_related / summary["total_violations"] * 100)}%。具体分布：' +
                                    '、'.join([f'{self.violation_mapping.get(vtype, vtype)}{count}次' for vtype, count in
                                              related_violations.items()]) + '。',
            'suggestions': self.get_specific_suggestions(violation_keyword)
        }

    def analyze_ranking_and_distribution(self, data: Dict[str, Any], time_desc: str) -> Dict[str, Any]:
        """分析排名和分布"""
        violations_by_camera = data['violations_by_camera']
        violations_by_type = data['violations_by_type']

        if not violations_by_camera:
            return {
                'direct_answer': f'在{time_desc}内没有违规数据可供排名分析。',
                'detailed_explanation': '系统运行正常，所有监控点均未检测到违规行为。',
                'suggestions': ['继续保持现有管理水平']
            }

        camera_ranking = sorted(violations_by_camera.items(), key=lambda x: x[1], reverse=True)
        violation_ranking = sorted(violations_by_type.items(), key=lambda x: x[1], reverse=True)

        top_camera = camera_ranking[0]
        top_violation = violation_ranking[0]

        return {
            'direct_answer': f'在{time_desc}内，违规最多的区域是{top_camera[0]}（{top_camera[1]}次），最常见的违规是{self.violation_mapping.get(top_violation[0], top_violation[0])}（{top_violation[1]}次）。',
            'detailed_explanation': f'摄像头违规排名：{", ".join([f"{cam}({count}次)" for cam, count in camera_ranking[:3]])}。违规类型排名：{", ".join([f"{self.violation_mapping.get(vtype, vtype)}({count}次)" for vtype, count in violation_ranking[:3]])}。',
            'suggestions': [
                f'重点关注{top_camera[0]}区域的管理',
                f'针对{self.violation_mapping.get(top_violation[0], top_violation[0])}问题制定专项改进措施',
                '加强高发区域的现场监督'
            ]
        }

    def analyze_risk_assessment(self, data: Dict[str, Any], time_desc: str) -> Dict[str, Any]:
        """风险评估分析"""
        violations_by_type = data['violations_by_type']
        summary = data['summary']

        if not violations_by_type:
            return {
                'direct_answer': '当前风险等级：无风险。',
                'detailed_explanation': f'在{time_desc}内系统未检测到任何违规行为，现场安全状况良好。',
                'suggestions': ['继续保持现有安全标准']
            }

        risk_score = 0
        high_risk_items = []

        for vtype, count in violations_by_type.items():
            severity = self.risk_severity.get(vtype, 1)
            risk_score += severity * count

            if severity >= 8:
                high_risk_items.append(f'{self.violation_mapping.get(vtype, vtype)}({count}次)')

        if risk_score >= 50:
            risk_level = '高风险'
            risk_desc = '存在严重安全隐患，需要立即采取措施'
        elif risk_score >= 25:
            risk_level = '中风险'
            risk_desc = '存在一定安全风险，需要及时关注和改进'
        elif risk_score > 0:
            risk_level = '低风险'
            risk_desc = '存在轻微问题，建议持续关注'
        else:
            risk_level = '无风险'
            risk_desc = '当前状况良好'

        return {
            'direct_answer': f'基于{time_desc}数据，当前风险等级：{risk_level}（风险分数：{risk_score}/100）。',
            'detailed_explanation': f'{risk_desc}。' + (
                f'高风险项目包括：{", ".join(high_risk_items)}。' if high_risk_items else ''),
            'suggestions': self.get_risk_mitigation_suggestions(risk_level, high_risk_items)
        }

    def analyze_trends(self, data: Dict[str, Any], time_desc: str) -> Dict[str, Any]:
        """趋势分析"""
        violations_by_hour = data['violations_by_hour']
        recent_records = data['recent_records']

        if not violations_by_hour:
            return {
                'direct_answer': f'基于{time_desc}的数据不足以进行趋势分析。',
                'detailed_explanation': '需要更多的历史数据来识别违规行为的时间模式和趋势。',
                'suggestions': ['继续收集数据以便进行趋势分析']
            }

        peak_hours = sorted(violations_by_hour.items(), key=lambda x: x[1], reverse=True)[:3]

        if len(recent_records) >= 5:
            recent_avg = sum(record['total_violations'] for record in recent_records[:5]) / 5
            older_avg = sum(record['total_violations'] for record in recent_records[5:]) / max(len(recent_records[5:]),
                                                                                               1)

            if recent_avg > older_avg * 1.2:
                trend = '上升'
            elif recent_avg < older_avg * 0.8:
                trend = '下降'
            else:
                trend = '稳定'
        else:
            trend = '数据不足'

        return {
            'direct_answer': f'基于{time_desc}的数据，违规趋势：{trend}。高发时段：{", ".join([f"{hour}点({count}次)" for hour, count in peak_hours])}。',
            'detailed_explanation': f'根据时间分布分析，违规行为主要集中在{", ".join([f"{hour}点" for hour, _ in peak_hours[:2]])}。最近的违规趋势呈{trend}状态。',
            'suggestions': [
                f'在{peak_hours[0][0]}点等高发时段加强监督',
                '分析高发时段的工作特点，制定针对性措施',
                '持续监控趋势变化'
            ]
        }

    def generate_improvement_suggestions(self, data: Dict[str, Any], time_desc: str) -> Dict[str, Any]:
        """生成改进建议"""
        violations_by_type = data['violations_by_type']
        violations_by_camera = data['violations_by_camera']

        if not violations_by_type:
            return {
                'direct_answer': f'基于{time_desc}的表现优秀，建议继续保持现有标准。',
                'detailed_explanation': '系统未检测到违规行为，表明管理制度执行良好。',
                'suggestions': [
                    '定期回顾和更新管理制度',
                    '保持员工培训的连续性',
                    '维护检测设备的正常运行'
                ]
            }

        suggestions = []
        sorted_violations = sorted(violations_by_type.items(),
                                   key=lambda x: self.risk_severity.get(x[0], 1),
                                   reverse=True)

        for vtype, count in sorted_violations[:3]:
            suggestions.extend(self.get_specific_suggestions(vtype))

        if violations_by_camera:
            worst_camera = max(violations_by_camera.items(), key=lambda x: x[1])
            suggestions.append(f'重点关注{worst_camera[0]}区域的管理改进')

        return {
            'direct_answer': f'基于{time_desc}的违规情况，建议优先处理{self.violation_mapping.get(sorted_violations[0][0], sorted_violations[0][0])}问题。',
            'detailed_explanation': f'系统检测到{len(violations_by_type)}种违规类型，建议按严重程度逐项改进。',
            'suggestions': suggestions[:6]
        }

    def analyze_general_overview(self, data: Dict[str, Any], time_desc: str) -> Dict[str, Any]:
        """通用概览分析"""
        summary = data['summary']
        violations_by_type = data['violations_by_type']

        return {
            'direct_answer': f'基于{time_desc}的系统概览：{summary["total_records"]}次检测，{summary["total_violations"]}次违规，涉及{summary["active_cameras"]}个监控点。',
            'detailed_explanation': f'在{time_desc}的检测情况分析中发现：共进行了{summary["total_records"]}次检测，发现{summary["total_violations"]}次违规，涉及{summary["active_cameras"]}个不同的监控点。主要违规类型包括：{", ".join([self.violation_mapping.get(vtype, vtype) for vtype in list(violations_by_type.keys())[:3]])}。',
            'suggestions': [
                '持续监控系统运行状态',
                '定期分析违规数据趋势',
                '根据数据制定针对性改进措施'
            ]
        }

    def get_specific_suggestions(self, violation_type: str) -> List[str]:
        """获取特定违规类型的建议"""
        suggestions_map = {
            'mask': [
                '确保充足的口罩供应',
                '加强口罩佩戴规范培训',
                '在入口设置佩戴提醒'
            ],
            'hat': [
                '配备合规的工作帽',
                '培训正确的佩戴方法',
                '定期检查佩戴情况'
            ],
            'phone': [
                '制定手机使用管理规定',
                '设置手机存放区域',
                '加强工作时间监督'
            ],
            'smoking': [
                '严格执行禁烟规定',
                '设置明显的禁烟标识',
                '建立违规处罚机制'
            ],
            'mouse': [
                '立即联系专业灭鼠服务',
                '检查并封堵可能的入侵通道',
                '加强环境清洁工作'
            ]
        }

        return suggestions_map.get(violation_type, ['加强相关管理', '定期培训员工', '建立监督机制'])

    def get_risk_mitigation_suggestions(self, risk_level: str, high_risk_items: List[str]) -> List[str]:
        """获取风险缓解建议"""
        if risk_level == '高风险':
            return [
                '立即停止相关作业直至问题解决',
                '召集紧急会议制定应对措施',
                '加强现场安全监督'
            ]
        elif risk_level == '中风险':
            return [
                '制定详细的改进计划',
                '增加安全检查频次',
                '加强员工安全意识培训'
            ]
        else:
            return [
                '继续保持现有安全标准',
                '定期进行安全评估',
                '持续改进管理制度'
            ]


# 创建分析器实例
analyzer = EnhancedViolationDataAnalyzer()


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        return jsonify({
            'status': 'healthy',
            'service': 'Enhanced Janus查询分析服务',
            'version': '3.0.0',
            'capabilities': {
                'natural_language_query': True,
                'real_data_analysis': True,
                'violation_assessment': True,
                'janus_pro_integration': analyzer.janus_model is not None
            },
            'janus_model_status': 'loaded' if analyzer.janus_model is not None else 'not_available',
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
    """自然语言查询接口"""
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': '缺少查询参数'
            }), 400

        query = data['query']
        time_range_hours = data.get('time_range_hours', 24)

        logger.info(
            f"处理查询: {query}, 时间范围: {time_range_hours}小时, Janus-Pro: {'可用' if analyzer.janus_model else '不可用'}")

        # 执行分析
        result = analyzer.analyze_query(query, time_range_hours)

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
        logger.error(f"获取数据摘要失败: {str(e)}")
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
            'capabilities': {
                'multimodal_understanding': True,
                'text_generation': True,
                'violation_analysis': True
            } if analyzer.janus_model is not None else {},
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
        print("启动增强的Janus查询分析服务...")
        print("功能: 基于真实违规数据的自然语言分析 + Janus-Pro集成")
        print("数据源: violations_records表")
        print("AI模型: Janus-Pro-1B (如果可用)")
        print("服务地址: http://localhost:5001")

        if analyzer.janus_model is not None:
            print("✅ Janus-Pro模型已加载，使用AI增强分析")
        else:
            print("⚠️ Janus-Pro模型未加载，使用规则引擎分析")
            print("要使用Janus-Pro，请将模型文件放置在 ./models/janus-pro-1b/ 目录")

        app.run(
            host='0.0.0.0',
            port=5001,
            debug=False,
            threaded=True
        )

    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        print(f"服务启动失败: {str(e)}")