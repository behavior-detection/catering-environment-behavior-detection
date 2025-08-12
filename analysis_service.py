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
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
import mysql.connector
import threading
import time
from dataclasses import dataclass
import re
import sys

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
        logging.FileHandler('logs/analysis_service.logs', encoding='utf-8')
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


class DatabaseTimeSeriesAnalyzer:
    """基于数据库的时序分析引擎"""

    def __init__(self):
        self.connection_pool = []
        self.lock = threading.Lock()
        self.test_db_connection()

    def test_db_connection(self):
        """测试数据库连接"""
        conn = get_db_connection()
        if conn:
            logger.info("数据库连接成功")
            conn.close()
        else:
            logger.error("数据库连接失败")

    def get_violation_records(self, hours: int = 24) -> List[ViolationRecord]:
        """从数据库获取违规记录"""
        conn = get_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor(dictionary=True)

            # 查询指定时间范围内的违规记录
            query = """
            SELECT id, camera_id, detection_timestamp, violation_data, total_violations
            FROM violations_records
            WHERE detection_timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            ORDER BY detection_timestamp ASC
            """

            cursor.execute(query, (hours,))
            rows = cursor.fetchall()

            records = []
            for row in rows:
                try:
                    # 解析JSON数据
                    violation_data = json.loads(row['violation_data'])
                    violations = violation_data.get('violations', {})

                    # 为每个违规类型创建记录
                    for violation_type, count in violations.items():
                        if count > 0:
                            record = ViolationRecord(
                                record_id=row['id'],
                                timestamp=row['detection_timestamp'],
                                camera_id=row['camera_id'],
                                violation_type=violation_type,
                                count=count,
                                confidence=0.9  # 默认置信度
                            )
                            records.append(record)

                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"解析违规数据失败: {e}")
                    continue

            cursor.close()
            conn.close()

            logger.info(f"从数据库加载了 {len(records)} 条违规记录")
            return records

        except mysql.connector.Error as err:
            logger.error(f"查询违规记录失败: {err}")
            if conn:
                conn.close()
            return []

    def get_trend_data(self,
                       time_window: str = 'hour',
                       violation_type: str = 'all',
                       camera_id: str = 'all',
                       hours: int = 24) -> Dict[str, Any]:
        """获取趋势数据"""

        logger.info(f"获取趋势数据: window={time_window}, type={violation_type}, camera={camera_id}")

        # 从数据库获取数据
        violation_records = self.get_violation_records(hours)

        # 生成时间序列
        now = get_current_time()
        if time_window == 'minute':
            time_points = [now - datetime.timedelta(minutes=i) for i in range(hours * 60, 0, -1)]
            format_str = '%H:%M'
        elif time_window == 'hour':
            time_points = [now - datetime.timedelta(hours=i) for i in range(hours, 0, -1)]
            format_str = '%H:00'
        else:  # day
            time_points = [now - datetime.timedelta(days=i) for i in range(hours, 0, -1)]
            format_str = '%m-%d'

        # 聚合数据
        current_data = []
        for time_point in time_points:
            count = self._get_violations_in_timeframe(
                violation_records, time_point, time_window, violation_type, camera_id
            )
            current_data.append(count)

        # 计算移动平均
        moving_avg = self._calculate_moving_average(current_data, window=3)

        # 生成时间标签
        time_labels = [tp.strftime(format_str) for tp in time_points]

        return {
            'time_labels': time_labels,
            'current_data': current_data,
            'moving_average': moving_avg,
            'summary': {
                'total_violations': sum(current_data),
                'avg_per_period': np.mean(current_data) if current_data else 0,
                'peak_time': time_labels[np.argmax(current_data)] if current_data else None,
                'trend_direction': self._calculate_trend_direction(current_data)
            }
        }

    def _get_violations_in_timeframe(self, records, time_point, window, violation_type, camera_id):
        """获取指定时间段内的违规数量"""
        time_point = ensure_timezone_aware(time_point)

        if window == 'minute':
            start_time = time_point
            end_time = time_point + datetime.timedelta(minutes=1)
        elif window == 'hour':
            start_time = time_point
            end_time = time_point + datetime.timedelta(hours=1)
        else:  # day
            start_time = time_point
            end_time = time_point + datetime.timedelta(days=1)

        count = 0
        for record in records:
            record_time = ensure_timezone_aware(record.timestamp)

            if start_time <= record_time < end_time:
                if violation_type == 'all' or record.violation_type == violation_type:
                    if camera_id == 'all' or record.camera_id == camera_id:
                        count += record.count

        return count

    def _calculate_moving_average(self, data: List[int], window: int = 3) -> List[float]:
        """计算移动平均"""
        if len(data) < window:
            return [float(x) for x in data]

        moving_avg = []
        for i in range(len(data)):
            if i < window - 1:
                moving_avg.append(float(data[i]))
            else:
                avg = sum(data[i - window + 1:i + 1]) / window
                moving_avg.append(round(avg, 1))

        return moving_avg

    def _calculate_trend_direction(self, data: List[int]) -> str:
        """计算趋势方向"""
        if len(data) < 2:
            return 'stable'

        recent_avg = np.mean(data[-6:])  # 最近6个点
        earlier_avg = np.mean(data[-12:-6]) if len(data) >= 12 else np.mean(data[:-6])

        if recent_avg > earlier_avg * 1.1:
            return 'increasing'
        elif recent_avg < earlier_avg * 0.9:
            return 'decreasing'
        else:
            return 'stable'

    def get_statistics(self, time_range: str = '24h') -> Dict[str, Any]:
        """获取统计数据"""
        if time_range == '1h':
            hours = 1
        elif time_range == '24h':
            hours = 24
        elif time_range == '7d':
            hours = 24 * 7
        else:
            hours = 24

        # 从数据库获取相关记录
        records = self.get_violation_records(hours)

        if not records:
            return {
                'time_range': time_range,
                'summary': {
                    'total_violations': 0,
                    'total_records': 0,
                    'unique_cameras': 0,
                    'avg_violations_per_record': 0
                },
                'violations_by_type': {},
                'violations_by_camera': {},
                'trend_data': self.get_trend_data('hour', hours=min(hours, 168))
            }

        total_violations = sum(r.count for r in records)
        unique_cameras = len(set(r.camera_id for r in records))

        # 按类型统计
        violations_by_type = {}
        for record in records:
            violations_by_type[record.violation_type] = violations_by_type.get(record.violation_type, 0) + record.count

        # 按摄像头统计
        violations_by_camera = {}
        for record in records:
            violations_by_camera[record.camera_id] = violations_by_camera.get(record.camera_id, 0) + record.count

        return {
            'time_range': time_range,
            'summary': {
                'total_violations': total_violations,
                'total_records': len(set(r.record_id for r in records if r.record_id)),
                'unique_cameras': unique_cameras,
                'avg_violations_per_record': total_violations / len(records) if records else 0
            },
            'violations_by_type': violations_by_type,
            'violations_by_camera': violations_by_camera,
            'trend_data': self.get_trend_data('hour', hours=min(hours, 168))
        }

    def add_violation_record(self, camera_id: str, violations: Dict[str, int], image_path: str = None):
        """添加违规记录到数据库"""
        conn = get_db_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()

            violation_data = {
                'violations': violations,
                'total_violations': sum(violations.values()),
                'timestamp': get_current_time().isoformat()
            }

            query = """
            INSERT INTO violations_records 
            (camera_id, detection_timestamp, violation_data, image_path, total_violations)
            VALUES (%s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                camera_id,
                get_current_time(),
                json.dumps(violation_data),
                image_path,
                violation_data['total_violations']
            ))

            record_id = cursor.lastrowid
            cursor.close()
            conn.close()

            logger.info(f"添加违规记录成功: ID={record_id}, 摄像头={camera_id}")
            return record_id

        except mysql.connector.Error as err:
            logger.error(f"添加违规记录失败: {err}")
            if conn:
                conn.close()
            return False


class AnomalyDetector:
    """异常检测引擎"""

    def __init__(self, analyzer: DatabaseTimeSeriesAnalyzer):
        self.analyzer = analyzer
        self.detection_config = {
            'z_score_threshold': 2.5,
            'trend_window': 10,
            'alert_cooldown': 600
        }

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """检测异常并生成预警"""
        alerts = []

        try:
            # 获取最近的数据进行异常检测
            trend_data = self.analyzer.get_trend_data('hour', hours=24)
            current_data = trend_data['current_data']

            if len(current_data) < 5:
                return alerts

            # Z-Score异常检测
            mean_val = np.mean(current_data[:-1])
            std_val = np.std(current_data[:-1])

            if std_val > 0:
                latest_point = current_data[-1]
                z_score = abs((latest_point - mean_val) / std_val)

                if z_score > self.detection_config['z_score_threshold']:
                    alert = {
                        'id': f"anomaly_{uuid.uuid4().hex[:8]}",
                        'timestamp': get_current_time().isoformat(),
                        'camera_id': "系统检测",
                        'type': "statistical_anomaly",
                        'severity': self._calculate_severity(z_score),
                        'message': f"检测到异常违规模式 (Z-Score: {z_score:.1f})",
                        'z_score': z_score,
                        'time_ago': '刚刚'
                    }
                    alerts.append(alert)

            # 趋势异常检测
            if len(current_data) >= self.detection_config['trend_window']:
                recent_trend = self._calculate_trend_slope(current_data[-self.detection_config['trend_window']:])

                if abs(recent_trend) > 1.5:
                    trend_type = "上升" if recent_trend > 0 else "下降"
                    alert = {
                        'id': f"trend_{uuid.uuid4().hex[:8]}",
                        'timestamp': get_current_time().isoformat(),
                        'camera_id': "多区域",
                        'type': "trend_anomaly",
                        'severity': "medium",
                        'message': f"违规频率呈{trend_type}趋势 (变化率: {recent_trend:.2f})",
                        'z_score': 0.0,
                        'time_ago': '刚刚'
                    }
                    alerts.append(alert)

        except Exception as e:
            logger.error(f"异常检测过程出错: {e}")

        return alerts

    def _calculate_severity(self, z_score: float) -> str:
        """根据Z-Score计算严重程度"""
        if z_score > 4.0:
            return "critical"
        elif z_score > 3.0:
            return "high"
        elif z_score > 2.5:
            return "medium"
        else:
            return "low"

    def _calculate_trend_slope(self, data: List[int]) -> float:
        """计算趋势斜率"""
        x = np.arange(len(data))
        y = np.array(data)
        slope = np.polyfit(x, y, 1)[0]
        return slope

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活跃预警"""
        return self.detect_anomalies()


class NaturalLanguageProcessor:
    """自然语言查询处理器"""

    def __init__(self, analyzer: DatabaseTimeSeriesAnalyzer):
        self.analyzer = analyzer

    def process_query(self, query: str) -> Dict[str, Any]:
        """处理自然语言查询"""
        logger.info(f"处理查询: {query}")

        # 获取最近24小时的数据
        records = self.analyzer.get_violation_records(24)

        if not records:
            return {
                'text': '当前数据库中暂无违规检测数据。系统正在等待数据输入。',
                'data': [],
                'insight': '请确保违规检测系统正常运行并向数据库写入数据。'
            }

        # 处理不同类型的查询
        if '今天' in query or 'today' in query.lower():
            return self._handle_today_query(records)
        elif '昨天' in query or 'yesterday' in query.lower():
            return self._handle_yesterday_query(records)
        elif '本周' in query or 'this week' in query.lower():
            return self._handle_week_query()
        elif '口罩' in query or 'mask' in query.lower():
            return self._handle_specific_violation_query(records, 'mask', '口罩佩戴')
        elif '帽子' in query or 'hat' in query.lower():
            return self._handle_specific_violation_query(records, 'hat', '工作帽佩戴')
        elif '手机' in query or 'phone' in query.lower():
            return self._handle_specific_violation_query(records, 'phone', '手机使用')
        elif '吸烟' in query or 'smoking' in query.lower():
            return self._handle_specific_violation_query(records, 'smoking', '吸烟行为')
        elif '最高' in query or 'highest' in query.lower():
            return self._handle_ranking_query(records)
        else:
            return self._handle_general_query(records)

    def _handle_today_query(self, records: List[ViolationRecord]) -> Dict[str, Any]:
        """处理今天相关查询"""
        current_time = get_current_time()
        today = current_time.date()
        today_records = []

        for record in records:
            record_time = ensure_timezone_aware(record.timestamp)
            if record_time.date() == today:
                today_records.append(record)

        total_violations = sum(r.count for r in today_records)
        violations_by_type = {}

        for record in today_records:
            violations_by_type[record.violation_type] = violations_by_type.get(record.violation_type, 0) + record.count

        return {
            'text': f'今日违规检测数据分析：',
            'data': [
                {'type': '总违规次数', 'count': total_violations},
                {'type': '检测记录数', 'count': len(set(r.record_id for r in today_records if r.record_id))},
                {'type': '涉及摄像头', 'count': len(set(r.camera_id for r in today_records))}
            ],
            'violations_breakdown': violations_by_type,
            'insight': f'今日共检测到{total_violations}次违规，涉及{len(set(r.camera_id for r in today_records))}个监控点。'
        }

    def _handle_yesterday_query(self, records: List[ViolationRecord]) -> Dict[str, Any]:
        """处理昨天相关查询"""
        yesterday_records = self.analyzer.get_violation_records(48)  # 获取48小时数据
        current_time = get_current_time()
        yesterday = current_time.date() - datetime.timedelta(days=1)

        yesterday_data = []
        for record in yesterday_records:
            record_time = ensure_timezone_aware(record.timestamp)
            if record_time.date() == yesterday:
                yesterday_data.append(record)

        if not yesterday_data:
            return {
                'text': '昨日暂无违规检测数据。',
                'data': [],
                'insight': '昨日系统可能未运行或未检测到违规行为。'
            }

        total_violations = sum(r.count for r in yesterday_data)
        violations_by_type = {}

        for record in yesterday_data:
            violations_by_type[record.violation_type] = violations_by_type.get(record.violation_type, 0) + record.count

        return {
            'text': '昨日违规检测数据分析：',
            'data': [
                {'type': '总违规次数', 'count': total_violations},
                {'type': '检测记录数', 'count': len(set(r.record_id for r in yesterday_data if r.record_id))}
            ],
            'violations_breakdown': violations_by_type,
            'insight': f'昨日共检测到{total_violations}次违规。'
        }

    def _handle_week_query(self) -> Dict[str, Any]:
        """处理本周相关查询"""
        week_records = self.analyzer.get_violation_records(7 * 24)  # 7天数据

        total_violations = sum(r.count for r in week_records)
        violations_by_type = {}

        for record in week_records:
            violations_by_type[record.violation_type] = violations_by_type.get(record.violation_type, 0) + record.count

        return {
            'text': '本周违规检测数据统计：',
            'data': [
                {'type': '总违规次数', 'count': total_violations},
                {'type': '日均违规', 'count': round(total_violations / 7, 1)}
            ],
            'violations_breakdown': violations_by_type,
            'insight': f'本周共检测到{total_violations}次违规，日均{round(total_violations / 7, 1)}次。'
        }

    def _handle_specific_violation_query(self, records: List[ViolationRecord], keyword: str, display_name: str) -> Dict[
        str, Any]:
        """处理特定违规类型查询"""
        specific_violations = [r for r in records if keyword.lower() in r.violation_type.lower()]
        total_violations = sum(r.count for r in specific_violations)

        return {
            'text': f'{display_name}违规情况分析：',
            'data': [
                {'type': f'{display_name}违规', 'count': total_violations},
                {'type': '检测记录数', 'count': len(specific_violations)}
            ],
            'insight': f'检测到{total_violations}次{display_name}违规。' if total_violations > 0 else f'近期未检测到{display_name}违规。'
        }

    def _handle_ranking_query(self, records: List[ViolationRecord]) -> Dict[str, Any]:
        """处理排名查询"""
        violations_by_type = {}
        for record in records:
            violations_by_type[record.violation_type] = violations_by_type.get(record.violation_type, 0) + record.count

        if not violations_by_type:
            return {
                'text': '暂无违规数据进行排名分析。',
                'data': [],
                'insight': '请确保检测系统正常运行。'
            }

        sorted_violations = sorted(violations_by_type.items(), key=lambda x: x[1], reverse=True)

        return {
            'text': '违规类型频次排名：',
            'data': [{'type': vtype, 'count': count} for vtype, count in sorted_violations],
            'insight': f'违规频率最高的是{sorted_violations[0][0]}，共{sorted_violations[0][1]}次。'
        }

    def _handle_general_query(self, records: List[ViolationRecord]) -> Dict[str, Any]:
        """处理一般查询"""
        total_violations = sum(r.count for r in records)
        unique_cameras = len(set(r.camera_id for r in records))

        return {
            'text': '基于数据库违规检测数据的分析：',
            'data': [
                {'type': '总违规次数', 'count': total_violations},
                {'type': '活跃摄像头', 'count': unique_cameras},
                {'type': '检测记录数', 'count': len(set(r.record_id for r in records if r.record_id))}
            ],
            'insight': f'系统正在正常运行，已检测到{total_violations}次违规行为。'
        }


# 初始化系统组件
analyzer = DatabaseTimeSeriesAnalyzer()
detector = AnomalyDetector(analyzer)
nlp_processor = NaturalLanguageProcessor(analyzer)


# 后台异常检测任务
def background_anomaly_detection():
    """后台异常检测任务"""
    while True:
        try:
            new_alerts = detector.detect_anomalies()
            if new_alerts:
                logger.info(f"检测到 {len(new_alerts)} 个新预警")
        except Exception as e:
            logger.error(f"异常检测任务失败: {e}")
        time.sleep(60)


# 启动后台任务
detection_thread = threading.Thread(target=background_anomaly_detection, daemon=True)
detection_thread.start()


# API路由定义
@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    # 测试数据库连接
    conn = get_db_connection()
    db_status = "connected" if conn else "disconnected"
    if conn:
        conn.close()

    return jsonify({
        'status': 'healthy',
        'service': '时序分析服务',
        'version': '2.0.0',
        'database': db_status,
        'timestamp': get_current_time().isoformat()
    })


@app.route('/api/analysis/trend', methods=['GET'])
def get_trend_analysis():
    """获取趋势分析数据"""
    try:
        time_window = request.args.get('window', 'hour')
        violation_type = request.args.get('type', 'all')
        camera_id = request.args.get('camera', 'all')
        hours = int(request.args.get('hours', '24'))

        trend_data = analyzer.get_trend_data(
            time_window=time_window,
            violation_type=violation_type,
            camera_id=camera_id,
            hours=hours
        )

        return jsonify({
            'success': True,
            'data': trend_data,
            'timestamp': get_current_time().isoformat()
        })

    except Exception as e:
        logger.error(f"获取趋势分析数据失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analysis/nlp-query', methods=['POST'])
def nlp_query():
    """自然语言查询处理"""
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': '缺少查询参数'
            }), 400

        query = data['query']
        logger.info(f"处理NLP查询: {query}")

        result = nlp_processor.process_query(query)

        return jsonify({
            'success': True,
            'query': query,
            'result': result,
            'timestamp': get_current_time().isoformat()
        })

    except Exception as e:
        logger.error(f"NLP查询处理失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analysis/alerts', methods=['GET'])
def get_alerts():
    """获取预警信息"""
    try:
        alerts = detector.get_active_alerts()

        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts),
            'timestamp': get_current_time().isoformat()
        })

    except Exception as e:
        logger.error(f"获取预警信息失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analysis/statistics', methods=['GET'])
def get_statistics():
    """获取统计数据"""
    try:
        time_range = request.args.get('range', '24h')
        statistics = analyzer.get_statistics(time_range)

        return jsonify({
            'success': True,
            'statistics': statistics,
            'timestamp': get_current_time().isoformat()
        })

    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analysis/submit-violation', methods=['POST'])
def submit_violation():
    """提交违规数据"""
    try:
        data = request.get_json()

        # 验证必需字段
        required_fields = ['camera_id', 'violations']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必需字段: {field}'
                }), 400

        camera_id = data['camera_id']
        violations = data['violations']
        image_path = data.get('image_path')

        # 验证违规数据格式
        if not isinstance(violations, dict):
            return jsonify({
                'success': False,
                'error': '违规数据格式错误'
            }), 400

        # 添加到数据库
        record_id = analyzer.add_violation_record(camera_id, violations, image_path)

        if record_id:
            return jsonify({
                'success': True,
                'message': '违规数据已保存到数据库',
                'record_id': record_id,
                'timestamp': get_current_time().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': '保存违规数据失败'
            }), 500

    except Exception as e:
        logger.error(f"提交违规数据失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/data/generate-sample', methods=['POST'])
def generate_sample_data():
    """生成样本数据"""
    try:
        data = request.get_json()
        count = data.get('count', 50) if data else 50

        # 违规类型
        violation_types = ['no_mask', 'no_hat', 'phone_usage', 'smoking', 'hygiene_violation']
        camera_ids = ['CAM001', 'CAM002', 'CAM003', 'CAM004']

        success_count = 0
        current_time = get_current_time()

        for i in range(count):
            # 生成时间（过去7天内随机时间）
            random_hours = np.random.uniform(0, 7 * 24)
            record_time = current_time - datetime.timedelta(hours=random_hours)

            # 随机选择摄像头
            camera_id = np.random.choice(camera_ids)

            # 生成违规数据
            violations = {}

            # 根据时间段生成不同概率的违规
            hour = record_time.hour
            if 8 <= hour <= 18:  # 工作时间
                violation_prob = 0.3
                max_violations = 4
            elif 19 <= hour <= 22:  # 晚班
                violation_prob = 0.2
                max_violations = 2
            else:  # 夜间
                violation_prob = 0.1
                max_violations = 1

            # 随机生成违规
            for violation_type in violation_types:
                if np.random.random() < violation_prob:
                    violations[violation_type] = np.random.randint(1, max_violations + 1)

            # 偶尔生成高违规数据
            if np.random.random() < 0.05:  # 5%概率
                critical_type = np.random.choice(violation_types)
                violations[critical_type] = np.random.randint(8, 15)

            # 只有当有违规时才添加记录
            if violations:
                # 使用数据库直接插入，绕过时间限制
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()

                        violation_data = {
                            'violations': violations,
                            'total_violations': sum(violations.values()),
                            'timestamp': record_time.isoformat()
                        }

                        query = """
                        INSERT INTO violations_records 
                        (camera_id, detection_timestamp, violation_data, total_violations)
                        VALUES (%s, %s, %s, %s)
                        """

                        cursor.execute(query, (
                            camera_id,
                            record_time,
                            json.dumps(violation_data),
                            violation_data['total_violations']
                        ))

                        success_count += 1
                        cursor.close()
                        conn.close()

                    except mysql.connector.Error as err:
                        logger.error(f"插入样本数据失败: {err}")
                        if conn:
                            conn.close()

        return jsonify({
            'success': True,
            'message': f'成功生成 {success_count} 条样本数据',
            'generated_count': success_count,
            'timestamp': get_current_time().isoformat()
        })

    except Exception as e:
        logger.error(f"生成样本数据失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/data/clear', methods=['POST'])
def clear_data():
    """清空数据"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': '数据库连接失败'
            }), 500

        cursor = conn.cursor()

        # 清空两个表的数据
        cursor.execute("DELETE FROM ai_analysis_reports")
        cursor.execute("DELETE FROM violations_records")

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': '数据已清空',
            'timestamp': get_current_time().isoformat()
        })

    except mysql.connector.Error as err:
        logger.error(f"清空数据失败: {err}")
        return jsonify({
            'success': False,
            'error': str(err)
        }), 500


@app.route('/api/data/status', methods=['GET'])
def get_data_status():
    """获取数据状态"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': '数据库连接失败'
            }), 500

        cursor = conn.cursor()

        # 获取违规记录数量
        cursor.execute("SELECT COUNT(*) FROM violations_records")
        violation_count = cursor.fetchone()[0]

        # 获取分析报告数量
        cursor.execute("SELECT COUNT(*) FROM ai_analysis_reports")
        report_count = cursor.fetchone()[0]

        # 获取最新记录时间
        cursor.execute("SELECT MAX(detection_timestamp) FROM violations_records")
        latest_record = cursor.fetchone()[0]

        # 获取摄像头统计
        cursor.execute("SELECT camera_id, COUNT(*) FROM violations_records GROUP BY camera_id")
        camera_stats = dict(cursor.fetchall())

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'data': {
                'violation_records': violation_count,
                'analysis_reports': report_count,
                'latest_record': latest_record.isoformat() if latest_record else None,
                'camera_statistics': camera_stats
            },
            'timestamp': get_current_time().isoformat()
        })

    except mysql.connector.Error as err:
        logger.error(f"获取数据状态失败: {err}")
        return jsonify({
            'success': False,
            'error': str(err)
        }), 500


# 测试路由
@app.route('/', methods=['GET'])
def index():
    """首页测试路由"""
    return jsonify({
        'message': '时序分析服务正在运行（数据库版本）',
        'status': 'healthy',
        'database': 'MySQL',
        'timestamp': get_current_time().isoformat(),
        'endpoints': [
            '/api/health',
            '/api/analysis/trend',
            '/api/analysis/alerts',
            '/api/analysis/statistics',
            '/api/analysis/nlp-query',
            '/api/analysis/submit-violation',
            '/api/data/generate-sample',
            '/api/data/clear',
            '/api/data/status'
        ]
    })


# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'API端点未找到',
        'message': '请检查请求的URL是否正确',
        'available_endpoints': [
            '/api/health',
            '/api/analysis/trend',
            '/api/analysis/alerts',
            '/api/analysis/statistics',
            '/api/analysis/nlp-query',
            '/api/analysis/submit-violation',
            '/api/data/generate-sample',
            '/api/data/clear',
            '/api/data/status'
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': '服务器内部错误',
        'message': '请稍后重试或联系管理员'
    }), 500


if __name__ == '__main__':
    try:
        print("启动时序分析服务（数据库版本）...")
        print("时序分析引擎: 已加载")
        print("异常检测引擎: 已启动")
        print("自然语言处理: 已就绪")
        print("数据源: MySQL数据库")
        print("服务地址: http://localhost:5002")
        print("API端点:")
        print("  - GET  /api/health")
        print("  - GET  /api/analysis/trend")
        print("  - GET  /api/analysis/alerts")
        print("  - GET  /api/analysis/statistics")
        print("  - POST /api/analysis/nlp-query")
        print("  - POST /api/analysis/submit-violation")
        print("  - POST /api/data/generate-sample")
        print("  - POST /api/data/clear")
        print("  - GET  /api/data/status")
        print("所有组件启动完成")

        app.run(
            host='0.0.0.0',
            port=5002,
            debug=False,
            threaded=True
        )

    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        print(f"服务启动失败: {str(e)}")
        print("请检查端口5002是否被占用，或检查其他错误信息")