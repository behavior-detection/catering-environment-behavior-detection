# apps/monitor/services.py
import requests
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count, Q
from collections import defaultdict
from typing import Dict, List, Any, Optional

from .models import ViolationRecord, SystemConfig

logger = logging.getLogger(__name__)


class JanusAIService:
    """Janus AI服务类"""

    def __init__(self):
        self.base_url = getattr(settings, 'JANUS_SERVICE_URL', 'http://localhost:5001')
        self.timeout = getattr(settings, 'JANUS_TIMEOUT', 60)

    def process_query(self, query: str, time_range_hours: int = 24) -> Dict[str, Any]:
        """处理AI查询"""
        try:
            url = f"{self.base_url}/api/query"

            # 准备请求数据
            request_data = {
                'query': query,
                'time_range_hours': int(time_range_hours) if time_range_hours else 24
            }

            # 如果是0，表示查询所有数据
            if int(time_range_hours) == 0:
                request_data['query_all'] = True

            logger.info(f"调用Janus AI服务: {url}")
            logger.debug(f"请求数据: {request_data}")

            response = requests.post(
                url,
                json=request_data,
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"Janus AI响应成功")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Janus AI服务请求失败: {str(e)}")
            raise Exception(f"AI服务不可用: {str(e)}")
        except Exception as e:
            logger.error(f"Janus AI处理失败: {str(e)}")
            raise Exception(f"AI查询失败: {str(e)}")

    def check_health(self) -> bool:
        """检查Janus AI服务健康状态"""
        try:
            url = f"{self.base_url}/api/health"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_service_status(self) -> Dict[str, Any]:
        """获取Janus AI服务状态详情"""
        try:
            url = f"{self.base_url}/api/health"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {'status': 'error', 'message': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


class ViolationAnalyzer:
    """违规数据分析器"""

    # 违规类型中文映射
    VIOLATION_MAPPING = {
        'mask': '未佩戴口罩',
        'hat': '未佩戴工作帽',
        'phone': '使用手机',
        'cigarette': '吸烟行为',
        'mouse': '鼠患问题',
        'uniform': '工作服违规',
        'person': '人员检测',
        'no_mask': '未佩戴口罩',
        'no_hat': '未佩戴工作帽',
        'phone_usage': '使用手机',
        'smoking': '吸烟行为',
        'mouse_infestation': '鼠患问题',
        'uniform_violation': '工作服违规',
        'unknown': '未知违规'
    }

    def __init__(self):
        self.logger = logger

    def analyze_records(self, records, time_range: str, query_all: bool = False) -> Dict[str, Any]:
        """分析违规记录"""
        try:
            # 基础统计
            total_records = len(records)
            total_violations = sum(record.total_violations for record in records)

            # 按类型统计
            violations_by_type = self._analyze_by_type(records)

            # 按摄像头统计
            violations_by_camera = self._analyze_by_camera(records)

            # 按小时统计
            violations_by_hour = self._analyze_by_hour(records)

            # 按日期统计
            violations_by_date = self._analyze_by_date(records)

            # 最近记录
            recent_records = self._get_recent_records(records)

            # 时间描述
            time_description = self._get_time_description(time_range, query_all)

            response_data = {
                'time_range': time_range,
                'summary': {
                    'total_violations': total_violations,
                    'total_records': total_records,
                    'active_cameras': len(violations_by_camera),
                    'query_interval': time_description,
                    'time_field_used': 'detection_timestamp',
                    'data_source': 'django_backend',
                    'query_timestamp': timezone.now().isoformat(),
                    'time_description': time_description
                },
                'violations_by_type': violations_by_type,
                'violations_by_camera': violations_by_camera,
                'violations_by_hour': violations_by_hour,
                'violations_by_date': violations_by_date,
                'recent_records': recent_records
            }

            self.logger.info(f"违规数据分析完成: {total_records}条记录, {total_violations}次违规")
            return response_data

        except Exception as e:
            self.logger.error(f"违规数据分析失败: {str(e)}")
            raise

    def _analyze_by_type(self, records) -> Dict[str, int]:
        """按违规类型分析"""
        violations_by_type = defaultdict(int)

        for record in records:
            try:
                violation_data = record.violation_data
                if isinstance(violation_data, dict):
                    violations = violation_data.get('violations', {})
                    for vtype, count in violations.items():
                        if isinstance(count, (int, float)) and count > 0:
                            violations_by_type[vtype] += int(count)

            except Exception as e:
                self.logger.warning(f"解析违规数据失败 (记录ID: {record.id}): {str(e)}")
                continue

        return dict(violations_by_type)

    def _analyze_by_camera(self, records) -> Dict[str, int]:
        """按摄像头分析"""
        violations_by_camera = defaultdict(int)

        for record in records:
            violations_by_camera[record.camera_id] += record.total_violations

        return dict(violations_by_camera)

    def _analyze_by_hour(self, records) -> Dict[int, int]:
        """按小时分析"""
        violations_by_hour = defaultdict(int)

        for record in records:
            hour = record.detection_timestamp.hour
            violations_by_hour[hour] += record.total_violations

        return dict(violations_by_hour)

    def _analyze_by_date(self, records) -> Dict[str, int]:
        """按日期分析"""
        violations_by_date = defaultdict(int)

        for record in records:
            date_str = record.detection_timestamp.date().isoformat()
            violations_by_date[date_str] += record.total_violations

        return dict(violations_by_date)

    def _get_recent_records(self, records, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近记录"""
        # 按时间排序，取最近的记录
        sorted_records = sorted(records, key=lambda x: x.detection_timestamp, reverse=True)

        recent = []
        for record in sorted_records[:limit]:
            recent.append({
                'camera_id': record.camera_id,
                'timestamp': record.detection_timestamp.isoformat(),
                'total_violations': record.total_violations,
                'violations': record.formatted_violations,
                'created_at': record.created_at.isoformat()
            })

        return recent

    def _get_time_description(self, time_range: str, query_all: bool) -> str:
        """获取时间范围描述"""
        if query_all:
            return '所有历史数据'

        time_mapping = {
            '1h': '最近1小时',
            '24h': '最近24小时',
            '7d': '最近7天',
            '30d': '最近30天',
            'all': '所有历史数据'
        }

        return time_mapping.get(time_range, '最近24小时')


class ViolationDataProcessor:
    """违规数据处理器 - 兼容原有YOLO数据格式"""

    def __init__(self):
        self.logger = logger

    def process_yolo_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理YOLO检测数据"""
        try:
            camera_id = data.get('camera_id', 'unknown')
            detection_timestamp = data.get('detection_timestamp') or data.get('timestamp')
            violation_data = data.get('violation_data', {})
            total_violations = data.get('total_violations', 0)

            # 解析时间戳
            if isinstance(detection_timestamp, str):
                try:
                    if detection_timestamp.endswith('Z'):
                        detection_timestamp = detection_timestamp.replace('Z', '+00:00')
                    detection_timestamp = datetime.fromisoformat(detection_timestamp)
                except ValueError:
                    detection_timestamp = timezone.now()
            elif not isinstance(detection_timestamp, datetime):
                detection_timestamp = timezone.now()

            # 处理违规数据
            if isinstance(violation_data, str):
                violation_data = json.loads(violation_data)

            # 确保违规数据格式正确
            if not isinstance(violation_data, dict):
                violation_data = {}

            if 'violations' not in violation_data:
                violation_data['violations'] = {}

            # 计算总违规数
            if total_violations == 0 and violation_data.get('violations'):
                total_violations = sum(
                    count for count in violation_data['violations'].values()
                    if isinstance(count, (int, float)) and count > 0
                )

            return {
                'camera_id': camera_id,
                'detection_timestamp': detection_timestamp,
                'violation_data': violation_data,
                'total_violations': total_violations,
                'processed_at': timezone.now()
            }

        except Exception as e:
            self.logger.error(f"处理YOLO数据失败: {str(e)}")
            raise Exception(f"数据处理失败: {str(e)}")

    def save_processed_data(self, processed_data: Dict[str, Any]) -> 'ViolationRecord':
        """保存处理后的数据"""
        try:
            # 检查重复数据
            existing = ViolationRecord.objects.filter(
                camera_id=processed_data['camera_id'],
                detection_timestamp=processed_data['detection_timestamp'],
                total_violations=processed_data['total_violations']
            ).first()

            if existing:
                self.logger.info(f"跳过重复记录: {processed_data['camera_id']}")
                return existing

            # 创建新记录
            record = ViolationRecord.objects.create(
                camera_id=processed_data['camera_id'],
                detection_timestamp=processed_data['detection_timestamp'],
                violation_data=processed_data['violation_data'],
                total_violations=processed_data['total_violations']
            )

            self.logger.info(f"保存违规记录成功: ID={record.id}")
            return record

        except Exception as e:
            self.logger.error(f"保存数据失败: {str(e)}")
            raise Exception(f"数据保存失败: {str(e)}")


class AIQueryProcessor:
    """AI查询处理器"""

    def __init__(self):
        self.ai_service = JanusAIService()
        self.analyzer = ViolationAnalyzer()
        self.logger = logger

    def process_natural_language_query(self, query: str, time_range_hours: int = 24) -> Dict[str, Any]:
        """处理自然语言查询"""
        try:
            # 智能时间范围检测
            detected_range = self._detect_time_range_from_query(query, time_range_hours)

            # 调用AI服务
            result = self.ai_service.process_query(query, detected_range)

            # 添加本地数据增强
            if result.get('success'):
                result = self._enhance_with_local_data(result, detected_range)

            return result

        except Exception as e:
            self.logger.error(f"处理自然语言查询失败: {str(e)}")
            raise

    def _detect_time_range_from_query(self, query: str, user_range: int) -> int:
        """从查询中智能检测时间范围"""
        query_lower = query.lower()

        # 时间关键词检测
        time_keywords = {
            '今天': 24,
            '今日': 24,
            'today': 24,
            '昨天': 48,
            '昨日': 48,
            'yesterday': 48,
            '本周': 168,
            '这周': 168,
            'this week': 168,
            '本月': 720,
            '这个月': 720,
            'this month': 720,
            '所有': 0,
            '全部': 0,
            'all': 0
        }

        for keyword, hours in time_keywords.items():
            if keyword in query_lower:
                self.logger.info(f"检测到时间关键词'{keyword}'，调整时间范围为{hours}小时")
                return hours

        # 数字时间检测
        import re
        hour_match = re.search(r'(\d+)\s*小时', query_lower)
        if hour_match:
            hours = int(hour_match.group(1))
            self.logger.info(f"检测到具体小时数: {hours}")
            return hours

        day_match = re.search(r'(\d+)\s*天', query_lower)
        if day_match:
            days = int(day_match.group(1))
            hours = days * 24
            self.logger.info(f"检测到具体天数: {days}天，转换为{hours}小时")
            return hours

        return user_range

    def _enhance_with_local_data(self, ai_result: Dict[str, Any], time_range_hours: int) -> Dict[str, Any]:
        """使用本地数据增强AI结果"""
        try:
            # 获取本地数据
            if time_range_hours == 0:
                records = list(ViolationRecord.objects.all())
            else:
                records = list(ViolationRecord.get_violations_by_time_range(time_range_hours))

            # 添加本地统计数据
            if records:
                local_analysis = self.analyzer.analyze_records(records, f"{time_range_hours}h", time_range_hours == 0)

                # 增强数据摘要
                if 'data_summary' not in ai_result:
                    ai_result['data_summary'] = {}

                ai_result['data_summary'].update({
                    'local_records_count': len(records),
                    'local_total_violations': sum(r.total_violations for r in records),
                    'local_cameras_count': len(set(r.camera_id for r in records)),
                    'local_latest_record': records[0].detection_timestamp.isoformat() if records else None
                })

            return ai_result

        except Exception as e:
            self.logger.warning(f"本地数据增强失败: {str(e)}")
            return ai_result


class SystemMonitor:
    """系统监控服务"""

    def __init__(self):
        self.logger = logger

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            # 数据库状态
            db_status = self._check_database_status()

            # AI服务状态
            ai_service = JanusAIService()
            ai_status = ai_service.get_service_status()

            # 数据统计
            data_stats = self._get_data_statistics()

            overall_status = all([
                db_status['status'] == 'OK',
                ai_status.get('status') != 'error'
            ])

            return {
                'overall_status': 'healthy' if overall_status else 'degraded',
                'timestamp': timezone.now().isoformat(),
                'components': {
                    'database': db_status,
                    'ai_service': ai_status,
                    'data_statistics': data_stats
                }
            }

        except Exception as e:
            self.logger.error(f"系统状态检查失败: {str(e)}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }

    def _check_database_status(self) -> Dict[str, Any]:
        """检查数据库状态"""
        try:
            count = ViolationRecord.objects.count()
            return {
                'status': 'OK',
                'records_count': count,
                'connection': 'active'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e),
                'connection': 'failed'
            }

    def _get_data_statistics(self) -> Dict[str, Any]:
        """获取数据统计"""
        try:
            now = timezone.now()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)

            stats = {
                'total_records': ViolationRecord.objects.count(),
                'records_last_24h': ViolationRecord.objects.filter(
                    created_at__gte=last_24h
                ).count(),
                'records_last_7d': ViolationRecord.objects.filter(
                    created_at__gte=last_7d
                ).count(),
                'total_violations': ViolationRecord.objects.aggregate(
                    Sum('total_violations')
                )['total_violations__sum'] or 0,
                'unique_cameras': ViolationRecord.objects.values(
                    'camera_id'
                ).distinct().count()
            }

            # 最新记录时间
            latest_record = ViolationRecord.objects.order_by('-detection_timestamp').first()
            if latest_record:
                stats['latest_record_time'] = latest_record.detection_timestamp.isoformat()

            return stats

        except Exception as e:
            self.logger.error(f"获取数据统计失败: {str(e)}")
            return {'error': str(e)}