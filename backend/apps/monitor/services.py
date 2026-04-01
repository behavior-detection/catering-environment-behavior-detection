import requests
import json
import logging
import time
import os
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
        # 增加超时时间到5分钟
        self.timeout = getattr(settings, 'JANUS_TIMEOUT', 300)

    def process_query(self, query: str, time_range_hours: int = 24, violations_data: Dict = None) -> Dict[str, Any]:
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

            # ✅ 方案A：将Django预加载的JSON文件数据一并传给Janus
            if violations_data:
                request_data['violations_data'] = violations_data
                total = violations_data.get('summary', {}).get('total_records', 0)
                logger.info(f"向Janus传入预加载数据: 共{total}条记录")
            else:
                logger.warning("未传入预加载数据，Janus将查询数据库（violations_records可能为空）")

            logger.info(f"调用Janus AI服务: {url}, 超时设置: {self.timeout}秒")
            logger.debug(f"请求数据摘要: query={request_data.get('query')}, "
                         f"time_range={request_data.get('time_range_hours')}, "
                         f"has_data={bool(request_data.get('violations_data'))}")

            # 直接调用 requests.post（调用方已通过 sync_to_async 在独立线程里执行，无需再套线程池）
            # 原 ThreadPoolExecutor 方案有 bug：with 块退出时 executor.shutdown(wait=True) 会
            # 阻塞等子线程结束，导致超时后再多等 300 秒，总计可挂起 610 秒
            resp = requests.post(
                url,
                json=request_data,
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            resp.raise_for_status()
            result = resp.json()

            logger.info("Janus AI响应成功")
            return result

        except requests.exceptions.Timeout as e:
            logger.error(f"Janus AI服务超时: {str(e)}")
            return {
                'success': False,
                'message': f'AI服务响应超时（{self.timeout}秒），请稍后重试',
                'timeout': True,
                'fallback': True
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Janus AI服务请求失败: {str(e)}")
            return {
                'success': False,
                'message': f'AI服务暂时不可用: {str(e)}',
                'service_error': True,
                'fallback': True
            }
        except Exception as e:
            logger.error(f"Janus AI处理失败: {str(e)}")
            return {
                'success': False,
                'message': f'AI查询处理失败: {str(e)}',
                'processing_error': True,
                'fallback': True
            }

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
    """AI查询处理器 - 优化版"""

    def __init__(self):
        self.ai_service = JanusAIService()
        self.analyzer = ViolationAnalyzer()
        self.logger = logger
        # 添加文件缓存
        self._file_cache = {}
        self._cache_timestamp = {}
        self._cache_duration = 60

    def process_natural_language_query(self, query: str, time_range_hours: int = 24, eid: str = None) -> Dict[str, Any]:
        """处理自然语言查询 - 优先本地数据，Janus可用时增强分析"""
        try:
            detected_range = self._detect_time_range_from_query(query, time_range_hours)

            logger.info(f"开始AI查询处理: query='{query}', time_range={detected_range}, eid={eid}")

            violations_data = None
            if eid:
                violations_data = self._get_cached_file_data(eid, detected_range)
                if violations_data:
                    total = violations_data.get('summary', {}).get('total_records', 0)
                    logger.info(f"预加载文件数据成功: {total}条记录")
                else:
                    logger.warning(f"EID={eid} 暂无文件数据")

            if not self.ai_service.check_health():
                logger.warning("Janus服务不可用，直接使用本地数据分析")
                return self._process_with_local_data_only(query, detected_range, eid, 'Janus服务暂不可用，使用本地数据分析')

            ai_result = self.ai_service.process_query(query, detected_range, violations_data=violations_data)

            if ai_result.get('fallback', False):
                logger.warning("AI服务异常，使用本地数据作为备选方案")
                return self._process_with_local_data_only(query, detected_range, eid,
                                                          ai_result.get('message', 'AI服务异常'))

            return ai_result

        except Exception as e:
            self.logger.error(f"处理自然语言查询失败: {str(e)}")
            return self._process_with_local_data_only(query, time_range_hours, eid, f"查询处理异常: {str(e)}")

    def _process_with_local_data_only(self, query: str, time_range_hours: int, eid: str, error_msg: str) -> Dict[str, Any]:
        """仅使用本地数据处理查询的备选方案"""
        try:
            logger.info(f"使用本地数据备选方案处理查询")

            local_analysis = self._get_cached_file_data(eid, time_range_hours)
            ai_summary = self._analyze_query_keywords(query, local_analysis)

            summary = local_analysis.get('summary', {})

            return {
                'success': True,
                'query': query,
                'time_range_hours': time_range_hours,
                'eid': eid,
                'analysis': {
                    'direct_answer': ai_summary,
                    'detailed_explanation': f"数据来源：本地文件分析（{error_msg}）\n\n"
                        f"共检测到 {summary.get('total_records', 0)} 条记录，"
                        f"{summary.get('total_violations', 0)} 次违规行为，"
                        f"涉及 {summary.get('active_cameras', 0)} 个监控点。",
                    'suggestions': [
                        '建议启动Janus AI服务以获取更详细的分析',
                        '可尝试更具体的问题以获得更精确的回答'
                    ]
                },
                'data_summary': {
                    'total_violations': summary.get('total_violations', 0),
                    'total_records': summary.get('total_records', 0),
                    'active_cameras': summary.get('active_cameras', 0),
                    'time_description': summary.get('time_description', f'最近{time_range_hours}小时')
                },
                'data_source': 'local_files_fallback',
                'fallback_reason': error_msg,
                'processing_mode': 'local_only',
                'query_info': {
                    'detected_keywords': self._extract_keywords(query),
                    'time_range_adjusted': False,
                    'smart_detected_hours': time_range_hours
                }
            }

        except Exception as e:
            self.logger.error(f"本地数据备选方案也失败: {str(e)}")
            return {
                'success': False,
                'message': f'查询处理失败: {str(e)}',
                'fallback_failed': True
            }

    def _get_cached_file_data(self, eid: str, time_range_hours: int) -> Dict[str, Any]:
        """获取缓存的文件数据"""
        cache_key = f"file_data_{eid}_{time_range_hours}"
        current_time = time.time()

        # 检查缓存是否存在且未过期
        if (cache_key in self._cache_timestamp and
                current_time - self._cache_timestamp[cache_key] < self._cache_duration):
            logger.info(f"使用缓存数据: {cache_key}")
            return self._file_cache.get(cache_key, {})

        # 重新加载数据
        logger.info(f"重新加载文件数据: {cache_key}")
        data = self._load_file_data_optimized(eid, time_range_hours)
        self._file_cache[cache_key] = data
        self._cache_timestamp[cache_key] = current_time

        return data

    def _load_file_data_optimized(self, eid: str, time_range_hours: int) -> Dict[str, Any]:
        """优化的文件数据加载"""
        try:
            from .models import DeviceWarehouse, WarehouseFile

            warehouses = DeviceWarehouse.objects.filter(eid=eid)
            if not warehouses.exists():
                return {}

            files = WarehouseFile.objects.filter(warehouse__in=warehouses).exclude(
                file_path__endswith='.mp4'
            ).exclude(
                file_path__endswith='.avi'
            ).exclude(
                file_path__endswith='.mov'
            )

            all_violations = []
            file_count = 0
            processed_count = 0

            for file_record in files:
                file_count += 1
                try:
                    if os.path.exists(file_record.file_path):
                        file_size = os.path.getsize(file_record.file_path)
                        if file_size > 10 * 1024 * 1024:
                            logger.warning(f"跳过大文件: {file_record.file_path} ({file_size} bytes)")
                            continue

                        with open(file_record.file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            processed_count += 1

                            if isinstance(data, list):
                                for item in data:
                                    normalized = self._normalize_violation_record(item, eid, file_record)
                                    if normalized:
                                        all_violations.append(normalized)
                            else:
                                normalized = self._normalize_violation_record(data, eid, file_record)
                                if normalized:
                                    all_violations.append(normalized)

                except Exception as e:
                    logger.warning(f"处理文件失败 {file_record.file_path}: {e}")
                    continue

            # 基于时间范围筛选
            filtered_violations = self._filter_violations_by_time(all_violations, time_range_hours)

            # 聚合数据
            result = self._aggregate_violations_data(filtered_violations, time_range_hours)

            logger.info(
                f"文件数据加载完成: {processed_count}/{file_count} 文件处理成功, {len(filtered_violations)} 条有效记录")

            return result

        except Exception as e:
            self.logger.error(f"加载文件数据失败: {str(e)}")
            return {}

    def _enhance_with_file_data_optimized(self, ai_result: Dict[str, Any], time_range_hours: int, eid: str) -> Dict[
        str, Any]:
        """优化的文件数据增强"""
        try:
            # 使用缓存获取文件数据
            file_data = self._get_cached_file_data(eid, time_range_hours)

            if file_data:
                # 增强数据摘要
                if 'data_summary' not in ai_result:
                    ai_result['data_summary'] = {}

                ai_result['data_summary'].update({
                    'file_records_count': file_data.get('summary', {}).get('total_records', 0),
                    'file_total_violations': file_data.get('summary', {}).get('total_violations', 0),
                    'data_source': 'ai_service_with_files',
                    'eid': eid,
                    'enhanced_with_cache': True
                })

                # 添加详细的分析结果
                if 'analysis' not in ai_result:
                    ai_result['analysis'] = {}

                ai_result['analysis'].update(file_data)

            return ai_result

        except Exception as e:
            self.logger.warning(f"文件数据增强失败: {str(e)}")
            return ai_result

    def _analyze_query_keywords(self, query: str, data: dict) -> str:
        """基于关键词分析查询"""
        query_lower = query.lower()
        summary = data.get('summary', {})

        total_violations = summary.get('total_violations', 0)
        total_records = summary.get('total_records', 0)

        # 关键词匹配
        if any(word in query_lower for word in ['口罩', 'mask']):
            violations_by_type = data.get('violations_by_type', {})
            mask_violations = violations_by_type.get('mask', 0)
            return f"根据数据分析，共检测到 {mask_violations} 次口罩相关违规，占总违规的 {mask_violations / total_violations * 100:.1f}%" if total_violations > 0 else "未检测到口罩相关违规"

        elif any(word in query_lower for word in ['摄像头', '区域', '哪个']):
            violations_by_camera = data.get('violations_by_camera', {})
            if violations_by_camera:
                max_camera = max(violations_by_camera.items(), key=lambda x: x[1])
                return f"违规最多的是摄像头 {max_camera[0]}，共 {max_camera[1]} 次违规"
            return "暂无摄像头违规数据"

        elif any(word in query_lower for word in ['今天', '今日', '情况']):
            return f"今日共记录 {total_records} 条检测记录，发现 {total_violations} 次违规行为"

        else:
            return f"数据概览：共 {total_records} 条记录，{total_violations} 次违规，涉及 {summary.get('active_cameras', 0)} 个监控点"

    def _extract_keywords(self, query: str) -> List[str]:
        """提取查询关键词"""
        keywords = []
        query_lower = query.lower()

        keyword_map = {
            '口罩': 'mask',
            '帽子': 'hat',
            '手机': 'phone',
            '抽烟': 'cigarette',
            '老鼠': 'mouse',
            '今天': 'today',
            '摄像头': 'camera'
        }

        for chinese, english in keyword_map.items():
            if chinese in query_lower:
                keywords.append(english)

        return keywords

    # 保留原有的其他方法...
    def _detect_time_range_from_query(self, query: str, user_range: int) -> int:
        """从查询中智能检测时间范围"""
        query_lower = query.lower()

        time_keywords = {
            '今天': 24, '今日': 24, 'today': 24,
            '昨天': 48, '昨日': 48, 'yesterday': 48,
            '本周': 168, '这周': 168, 'this week': 168,
            '本月': 720, '这个月': 720, 'this month': 720,
            '所有': 0, '全部': 0, 'all': 0
        }

        for keyword, hours in time_keywords.items():
            if keyword in query_lower:
                self.logger.info(f"检测到时间关键词'{keyword}'，调整时间范围为{hours}小时")
                return hours

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

    def _normalize_violation_record(self, record: Dict, eid: str, file_record) -> Optional[Dict[str, Any]]:
        """标准化违规记录数据格式"""
        try:
            if not isinstance(record, dict):
                return None

            timestamp = record.get('timestamp')
            if not timestamp:
                return None

            normalized_timestamp = self._parse_timestamp(timestamp)
            if not normalized_timestamp:
                return None

            violations = record.get('violations', {})
            total_violations = int(record.get('total_violations', 0))

            return {
                'id': f"json_{record.get('camera_id', 'unknown')}_{int(time.time() * 1000000)}",
                'camera_id': str(record.get('camera_id', 'unknown')),
                'detection_timestamp': normalized_timestamp,
                'timestamp': normalized_timestamp,
                'total_violations': total_violations,
                'violations': violations,
                'formatted_violations': violations,
                'class_numbers': record.get('class_numbers', {}),
                'image_path': '',
                'created_at': normalized_timestamp,
                '_eid': eid,
                '_file_id': file_record.id,
                '_file_path': file_record.file_path,
                '_original_timestamp': str(timestamp)
            }

        except Exception as e:
            self.logger.error(f"标准化记录失败: {e}")
            return None

    def _parse_timestamp(self, timestamp_str: str) -> Optional[str]:
        """解析时间戳，支持中文日期、ISO格式、HH:MM:SS、MM:SS"""
        try:
            import re
            from datetime import datetime
            from django.utils import timezone

            if not timestamp_str:
                return None

            ts = timestamp_str.strip()

            # 格式1: 中文日期 "2025年08月07日星期四16:23:15"
            pattern = r'(\d{4})年(\d{2})月(\d{2})日[^0-9]*(\d{2}):(\d{2}):(\d{2})'
            match = re.match(pattern, ts)
            if match:
                year, month, day, hour, minute, second = match.groups()
                dt = datetime(
                    year=int(year), month=int(month), day=int(day),
                    hour=int(hour), minute=int(minute), second=int(second),
                    tzinfo=timezone.utc
                )
                return dt.isoformat()

            # 格式2: ISO格式 "2025-08-07T16:23:15" 或 "2025-08-07 16:23:15"
            iso_pattern = r'(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})'
            match = re.match(iso_pattern, ts)
            if match:
                year, month, day, hour, minute, second = match.groups()
                dt = datetime(
                    year=int(year), month=int(month), day=int(day),
                    hour=int(hour), minute=int(minute), second=int(second),
                    tzinfo=timezone.utc
                )
                return dt.isoformat()

            # 格式3: 仅时间 "16:23:15" (HH:MM:SS) — 使用今天的日期补全
            hms_pattern = r'^(\d{2}):(\d{2}):(\d{2})$'
            match = re.match(hms_pattern, ts)
            if match:
                h, m, s = match.groups()
                now = datetime.now(timezone.utc)
                dt = now.replace(hour=int(h), minute=int(m), second=int(s), microsecond=0)
                return dt.isoformat()

            # 格式4: 视频相对时间 "00:42" (MM:SS) — 使用今天的日期补全
            ms_pattern = r'^(\d{2}):(\d{2})$'
            match = re.match(ms_pattern, ts)
            if match:
                m, s = match.groups()
                now = datetime.now(timezone.utc)
                dt = now.replace(minute=int(m), second=int(s), microsecond=0)
                return dt.isoformat()

            self.logger.warning(f"无法识别的时间格式: {timestamp_str}")
            return None

        except Exception as e:
            self.logger.error(f"时间解析失败: {e}")
            return None

    def _filter_violations_by_time(self, violations: List[Dict], time_range_hours: int) -> List[Dict]:
        """根据时间范围筛选违规记录"""
        if time_range_hours == 0:
            return violations

        from datetime import datetime, timedelta
        from django.utils import timezone

        cutoff_time = timezone.now() - timedelta(hours=time_range_hours)
        filtered = []

        for violation in violations:
            timestamp_str = violation.get('detection_timestamp') or violation.get('timestamp')
            if timestamp_str:
                try:
                    violation_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if violation_time.tzinfo is None:
                        violation_time = violation_time.replace(tzinfo=timezone.utc)

                    if violation_time >= cutoff_time:
                        filtered.append(violation)
                except Exception as e:
                    self.logger.warning(f"时间筛选解析失败: {e}")
                    filtered.append(violation)

        return filtered

    def _aggregate_violations_data(self, violations: List[Dict], time_range_hours: int) -> Dict[str, Any]:
        """聚合违规数据"""
        try:
            total_violations = sum(v.get('total_violations', 0) for v in violations)
            violations_by_type = {}
            violations_by_camera = {}
            violations_by_hour = {}
            violations_by_date = {}

            for violation in violations:
                # 按类型统计
                formatted_violations = violation.get('violations', {})
                for vtype, count in formatted_violations.items():
                    if isinstance(count, (int, float)) and count > 0:
                        violations_by_type[vtype] = violations_by_type.get(vtype, 0) + int(count)

                # 按摄像头统计
                camera_id = violation.get('camera_id', 'unknown')
                v_count = violation.get('total_violations', 0)
                violations_by_camera[camera_id] = violations_by_camera.get(camera_id, 0) + v_count

                # 按时间统计
                timestamp = violation.get('detection_timestamp') or violation.get('timestamp')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        hour = dt.hour
                        violations_by_hour[hour] = violations_by_hour.get(hour, 0) + v_count

                        date_str = dt.date().isoformat()
                        violations_by_date[date_str] = violations_by_date.get(date_str, 0) + v_count
                    except:
                        pass

            return {
                'summary': {
                    'total_violations': total_violations,
                    'total_records': len(violations),
                    'active_cameras': len(violations_by_camera),
                    'time_description': self._get_time_description(time_range_hours)
                },
                'violations_by_type': violations_by_type,
                'violations_by_camera': violations_by_camera,
                'violations_by_hour': violations_by_hour,
                'violations_by_date': violations_by_date,
                'recent_records': sorted(violations,
                                         key=lambda x: x.get('detection_timestamp', ''), reverse=True)[:20]
            }

        except Exception as e:
            self.logger.error(f"数据聚合失败: {e}")
            return {}

    def _get_time_description(self, time_range_hours: int) -> str:
        """获取时间范围描述"""
        if time_range_hours == 0:
            return '所有历史数据'
        elif time_range_hours <= 24:
            return f'最近{time_range_hours}小时'
        else:
            days = time_range_hours // 24
            return f'最近{days}天'

    def process_natural_language_query_with_data(
        self, query: str, violations_data: list, time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """
        使用外部传入的违规数据列表进行AI查询（供 visitor_ai_query 使用）。
        violations_data 是已过滤好的原始记录列表，聚合后直接传给 Janus。
        """
        try:
            detected_range = self._detect_time_range_from_query(query, time_range_hours)

            # 聚合数据，转为 Janus 期望的格式
            aggregated = self._aggregate_violations_data(violations_data, detected_range)

            if not aggregated:
                logger.warning("process_natural_language_query_with_data: 聚合结果为空，使用本地分析")
                return self._process_with_local_data_only(
                    query, detected_range, None, "暂无符合条件的数据"
                )

            logger.info(
                f"visitor AI查询: query='{query}', "
                f"records={len(violations_data)}, time_range={detected_range}"
            )

            ai_result = self.ai_service.process_query(
                query, detected_range, violations_data=aggregated
            )

            if ai_result.get('fallback', False):
                return self._process_with_local_data_only(
                    query, detected_range, None, ai_result.get('message', 'AI服务异常')
                )

            return ai_result

        except Exception as e:
            self.logger.error(f"process_natural_language_query_with_data 失败: {str(e)}")
            return self._process_with_local_data_only(
                query, time_range_hours, None, f"查询处理异常: {str(e)}"
            )


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