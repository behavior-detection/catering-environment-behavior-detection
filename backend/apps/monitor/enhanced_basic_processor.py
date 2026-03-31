# apps/monitor/enhanced_basic_processor.py - 最终修复版本

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from collections import defaultdict
from .models import ViolationRecord
from dataclasses import dataclass, field
from django.utils import timezone
# 导入 dateutil 库来更强大地处理相对日期
from dateutil.relativedelta import relativedelta
from django.db.models.functions import TruncHour, TruncDay, TruncWeek
from dateutil.parser import isoparse

logger = logging.getLogger(__name__)

class ViolationAnalyzer:
    """违规数据分析器"""

    VIOLATION_MAPPING = {
        'mask': '未佩戴口罩', 'no_mask': '未佩戴口罩',
        'hat': '未佩戴工作帽', 'no_hat': '未佩戴工作帽',
        'phone': '使用手机', 'phone_usage': '使用手机',
        'smoking': '吸烟行为', 'cigarette': '吸烟行为',
        'mouse': '鼠患问题', 'mouse_infestation': '鼠患问题',
        'uniform': '工作服违规', 'uniform_violation': '工作服违规',
        'unknown': '未知违规'
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def analyze_records(self, records: List[ViolationRecord], time_range: str, query_all: bool = False) -> Dict[str, Any]:
        """分析违规记录的核心方法"""
        try:
            total_records = len(records)
            total_violations = sum(record.total_violations for record in records)
            violations_by_type = self._analyze_by_type(records)
            violations_by_camera = self._analyze_by_camera(records)
            violations_by_hour = self._analyze_by_hour(records)
            violations_by_date = self._analyze_by_date(records)
            recent_records = self._get_recent_records(records)
            time_description = self._get_time_description(time_range, query_all)

            return {
                'time_range': time_range,
                'summary': {
                    'total_violations': total_violations,
                    'total_records': total_records,
                    'active_cameras': len(violations_by_camera),
                    'time_description': time_description
                },
                'violations_by_type': violations_by_type,
                'violations_by_camera': violations_by_camera,
                'violations_by_hour': violations_by_hour,
                'violations_by_date': violations_by_date,
                'recent_records': recent_records
            }
        except Exception as e:
            self.logger.error(f"违规数据分析失败: {str(e)}")
            raise

    def _analyze_by_type(self, records: List[ViolationRecord]) -> Dict[str, int]:
        violations_by_type = defaultdict(int)
        for record in records:
            for vtype, count in record.formatted_violations.items():
                if isinstance(count, (int, float)) and count > 0:
                    violations_by_type[vtype] += int(count)
        return dict(violations_by_type)

    def _analyze_by_camera(self, records: List[ViolationRecord]) -> Dict[str, int]:
        violations_by_camera = defaultdict(int)
        for record in records:
            violations_by_camera[record.camera_id] += record.total_violations
        return dict(violations_by_camera)

    def _analyze_by_hour(self, records: List[ViolationRecord]) -> Dict[int, int]:
        violations_by_hour = defaultdict(int)
        for record in records:
            hour = record.detection_timestamp.hour
            violations_by_hour[hour] += record.total_violations
        return dict(violations_by_hour)

    def _analyze_by_date(self, records: List[ViolationRecord]) -> Dict[str, int]:
        violations_by_date = defaultdict(int)
        for record in records:
            date_str = record.detection_timestamp.date().isoformat()
            violations_by_date[date_str] += record.total_violations
        return dict(violations_by_date)

    def _get_recent_records(self, records: List[ViolationRecord], limit: int = 10) -> List[Dict[str, Any]]:
        sorted_records = sorted(records, key=lambda x: x.detection_timestamp, reverse=True)
        recent = []
        for record in sorted_records[:limit]:
            recent.append({
                'id': record.id,
                'camera_id': record.camera_id,
                'timestamp': record.detection_timestamp.isoformat(),
                'total_violations': record.total_violations,
                'violations': record.formatted_violations,
                'created_at': record.created_at.isoformat()
            })
        return recent

    def _get_time_description(self, time_range: str, query_all: bool) -> str:
        if query_all: return '所有历史数据'
        return {'1h':'最近1小时','24h':'最近24小时','7d':'最近7天','30d':'最近30天','all':'所有历史数据'}.get(time_range, '最近24小时')

@dataclass
class QueryStructure:
    """查询结构化信息"""
    time_filters: List[str]  # 时间筛选条件
    camera_filters: List[str]  # 摄像头筛选条件
    violation_filters: List[str]  # 违规类型筛选条件
    analysis_types: List[str]  # 分析类型
    metrics: List[str]  # 指标类型
    is_structured: bool  # 是否为结构化查询
    confidence: float  # 结构化置信度
    original_query: str = field(default="")

class QueryStructureAnalyzer:
    """查询结构分析器 - 基于语义要素而不是正则匹配"""

    def __init__(self):
        # 定义查询要素词典
        # --- 时间要素 ---
        self.time_elements = {
            'absolute': ['今天', '昨天', '前天', '明天', '今日', '昨日', '本日', '后天'],
            'relative': ['最近', '过去', '近期', '上周', '本周', '这周', '上个月', '本月', '这个月', '去年', '今年'],
            'specific': ['日', '月', '年', '号', '星期', '周一', '周二', '周三', '周四', '周五', '周六', '周日',
                         '星期天', '月份'],
            'duration': ['分钟', '小时', '天', '周', '星期', '月', '季度', '年']
        }

        # --- 摄像头要素 ---
        self.camera_elements = {
            'identifiers': ['摄像头', 'cam', 'camera', '监控', '探头', '机位', '监控点'],
            # 优化正则表达式，忽略大小写，并兼容空格
            'numbers': re.compile(r'(cam[_\s\-]?\d+|d\s?\d+|\d+\s?号)', re.IGNORECASE)
        }

        # --- 违规类型要素 ---
        self.violation_elements = {
            'mask': ['口罩', '面罩', '戴口罩', '未戴口罩', '没戴口罩'],
            'hat': ['帽子', '工作帽', '安全帽', '厨师帽', '戴帽', '未戴帽', '没戴帽'],
            'smoking': ['吸烟', '抽烟', '香烟', '烟', '点烟', '烟头'],
            'phone': ['手机', '电话', '通话', '玩手机', '看手机', '打电话'],
            'mouse': ['老鼠', '鼠患', '害虫', '有老鼠'],
            'uniform': ['工作服', '制服', '着装', '服装', '工服', '厨师服', '穿工服']
        }

        # --- 分析意图要素 ---
        self.analysis_elements = {
            'listing': ['哪些', '哪个', '有哪些', '有什么', '什么', '列出', '所有', '清单', '查一下', '一份'],
            'aggregation': ['统计', '总计', '合计', '汇总', '情况', '怎么样', '总结', '数据', '一共', '多少次', '总数',
                            '概览'],
            'comparison': ['比较', '对比', '差异', '相比', '和', '与', '哪个更', '不同', 'vs'],
            'ranking': ['排序', '排行', '最多', '最少', '前几', '后几', '最高', '最低', '排名', 'TOP', '最突出', '最好',
                        '最差'],
            'trend': ['趋势', '变化', '发展', '走势', '上升', '下降', '增加', '减少', '改善', '恶化', '波动'],
            'distribution': ['分布', '分配', '时段', '时间段', '什么时候', '时间点', '高发期', '上午', '下午', '晚上',
                             '夜间'],
            'risk':         ['风险', '危险', '安全', '评估', '状况', '隐患', '等级', '注意'],
            'rate':         ['率', '比例', '百分比', '占比'],
            # 根源分析意图
            'root_cause':   ['原因', '为什么', '根源', '为啥', '咋回事']
        }


        # --- 指标要素 ---
        self.metric_elements = {
            'count': ['次数', '数量', '个数', '条数', '多少', '几例', '总数'],
            'frequency': ['频率', '频次', '经常性', '多频繁', '发生率'],
            'percentage': ['百分比', '比例', '占比', '百分率', '构成'],
            'score': ['分数', '评分', '得分', '指数', '评级']
        }

    def analyze_query_structure(self, query: str) -> QueryStructure:
        """分析查询的结构化信息"""
        query_lower = query.lower().strip()

        # 提取各类要素
        time_filters = self._extract_time_elements(query_lower)
        camera_filters = self._extract_camera_elements(query_lower)
        violation_filters = self._extract_violation_elements(query_lower)
        analysis_types = self._extract_analysis_elements(query_lower)
        metrics = self._extract_metric_elements(query_lower)

        # 计算结构化程度
        structured_elements = len(time_filters) + len(camera_filters) + len(violation_filters) + len(analysis_types)
        total_words = len(query_lower.split())

        # 结构化判断逻辑
        is_structured = self._is_structured_query(
            query_lower, time_filters, camera_filters,
            violation_filters, analysis_types, structured_elements, total_words
        )

        confidence = min(structured_elements * 0.25 + 0.1, 1.0)

        structure = QueryStructure(
            time_filters=time_filters,
            camera_filters=camera_filters,
            violation_filters=violation_filters,
            analysis_types=analysis_types,
            metrics=metrics,
            is_structured=is_structured,
            confidence=confidence
        )
        # Assign the original query
        structure.original_query = query

        return structure

    def _extract_time_elements(self, query: str) -> List[str]:
        """提取时间相关要素"""
        elements = []

        for category, terms in self.time_elements.items():
            for term in terms:
                if term in query:
                    elements.append(f"{category}:{term}")

        # 检查具体日期模式
        date_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{1,2}月\d{1,2}日',
            r'\d{1,2}号'
        ]

        for pattern in date_patterns:
            if re.search(pattern, query):
                elements.append("specific_date")
                break

        return list(set(elements))

    def _extract_camera_elements(self, query: str) -> List[str]:
        """提取摄像头相关要素"""
        elements = []

        # 检查摄像头标识词
        for identifier in self.camera_elements['identifiers']:
            if identifier in query:
                elements.append("camera_mentioned")
                break

        # 检查具体摄像头编号
        matches = self.camera_elements['numbers'].findall(query)
        if matches:
            elements.extend([f"camera_id:{match}" for match in matches])

        return elements

    def _extract_violation_elements(self, query: str) -> List[str]:
        """提取违规类型要素"""
        elements = []

        for violation_type, terms in self.violation_elements.items():
            for term in terms:
                if term in query:
                    elements.append(f"violation:{violation_type}")
                    break

        return list(set(elements))

    def _extract_analysis_elements(self, query: str) -> List[str]:
        """提取分析类型要素"""
        elements = []

        for analysis_type, terms in self.analysis_elements.items():
            for term in terms:
                if term in query:
                    elements.append(f"analysis:{analysis_type}")
                    break

        return list(set(elements))

    def _extract_metric_elements(self, query: str) -> List[str]:
        """提取指标要素"""
        elements = []

        for metric_type, terms in self.metric_elements.items():
            for term in terms:
                if term in query:
                    elements.append(f"metric:{metric_type}")
                    break

        return list(set(elements))

    def _is_structured_query(self, query: str, time_filters: List[str],
                             camera_filters: List[str], violation_filters: List[str],
                             analysis_types: List[str], structured_elements: int,
                             total_words: int) -> bool:
        """判断是否为结构化查询"""

        # 明确的非结构化查询
        unstructured_patterns = [
            '系统', '功能', '介绍', '是什么', '怎么', '如何', '为什么',
            '你好', '谢谢', '再见', '笑话'
        ]

        for pattern in unstructured_patterns:
            if pattern in query:
                return False

        # 结构化查询的判断条件
        conditions = [
            # 条件1：包含时间筛选要素
            len(time_filters) > 0,
            # 条件2：包含摄像头要素
            len(camera_filters) > 0,
            # 条件3：包含违规类型要素
            len(violation_filters) > 0,
            # 条件4：包含分析类型要素
            len(analysis_types) > 0,
            # 条件5：结构化要素占比较高
            structured_elements >= 2 and structured_elements / max(total_words, 1) > 0.3
        ]

        # 至少满足2个条件才认为是结构化查询
        satisfied_conditions = sum(conditions)

        return satisfied_conditions >= 2


class StructuredQueryProcessor:
    """结构化查询处理器 - 专门处理模板化查询"""

    def __init__(self):
        self.structure_analyzer = QueryStructureAnalyzer()
        # --- 原有代码 ---
        self.violation_mapping = {
            'mask': {'terms': ['口罩', '面罩'], 'display': '口罩佩戴', 'fields': ['mask', 'no_mask']},
            'hat': {'terms': ['帽子', '工作帽', '安全帽'], 'display': '工作帽佩戴', 'fields': ['hat', 'no_hat']},
            'smoking': {'terms': ['吸烟', '抽烟', '烟'], 'display': '吸烟行为', 'fields': ['smoking', 'cigarette']},
            'phone': {'terms': ['手机', '电话'], 'display': '手机使用', 'fields': ['phone', 'phone_usage']},
            'mouse': {'terms': ['老鼠', '鼠患'], 'display': '鼠患问题', 'fields': ['mouse', 'mouse_infestation']},
            'uniform': {'terms': ['工作服', '制服', '着装'], 'display': '工作服规范',
                        'fields': ['uniform', 'uniform_violation']}
        }
        self.risk_weights = {
            'smoking': 10, 'mouse': 8, 'phone': 6,
            'uniform': 4, 'mask': 3, 'hat': 2
        }
        self.TIME_KEYWORD_MAP = self._initialize_time_keyword_map()

    def _initialize_time_keyword_map(self) -> Dict:
        """[新增] 初始化中央时间关键词字典"""
        now = timezone.now()

        today = {'start': now.replace(hour=0, minute=0, second=0), 'end': now, 'desc': '今天'}
        yesterday = {'start': (now - timedelta(days=1)).replace(hour=0, minute=0, second=0),
                     'end': (now - timedelta(days=1)).replace(hour=23, minute=59, second=59), 'desc': '昨天'}
        this_week = {'start': (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0), 'end': now,
                     'desc': '本周'}
        last_week = {'start': (now - timedelta(days=now.weekday() + 7)).replace(hour=0, minute=0, second=0),
                     'end': (now - timedelta(days=now.weekday() + 1)).replace(hour=23, minute=59, second=59),
                     'desc': '上周'}
        this_month = {'start': now.replace(day=1, hour=0, minute=0, second=0), 'end': now, 'desc': '本月'}
        last_month = {'start': (now.replace(day=1) - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0),
                      'end': (now.replace(day=1) - timedelta(days=1)).replace(hour=23, minute=59, second=59),
                      'desc': '上个月'}

        return {
            '今天': today,
            '昨天': yesterday,
            '本周': this_week,
            '这周': this_week,  # 同义词
            '上周': last_week,
            '本月': this_month,
            '这个月': this_month,  # 同义词
            '上个月': last_month
        }

    def process_structured_query(self, query: str, structure: Optional[QueryStructure],
                                 custom_time_range: Optional[Dict] = None,
                                 force_analysis_type: Optional[str] = None) -> Dict[str, Any]:
        """处理结构化查询的总入口"""
        if structure is None:
            structure = self.structure_analyzer.analyze_query_structure(query)

        if custom_time_range and custom_time_range.get('start_time'):
            start_utc = isoparse(custom_time_range['start_time'])
            end_utc = isoparse(custom_time_range['end_time'])
            start_local = timezone.localtime(start_utc)
            end_local = timezone.localtime(end_utc)
            time_range_info = {
                'start_time': start_local,
                'end_time': end_local,
                'description': f"从 {start_local.strftime('%Y-%m-%d %H:%M')} 到 {end_local.strftime('%Y-%m-%d %H:%M')}"
            }
        else:
            time_range_info = self._parse_time_range_v2(structure)

        analysis_type = self._parse_analysis_type(structure.analysis_types)
        queryset = self._build_queryset_v2(time_range_info, self._parse_camera_filter(structure.camera_filters),
                                           self._parse_violation_type(structure.violation_filters))

        # 意图优先级判断 (已修复)
        if 'root_cause' in analysis_type:
            return self._generate_root_cause_analysis(queryset, time_range_info, query)
        elif 'risk' in analysis_type:
            return self._generate_enhanced_risk_analysis(queryset, time_range_info)
        elif 'trend' in analysis_type:
            return self._generate_enhanced_trend_analysis(queryset, time_range_info)
        elif 'ranking' in analysis_type:
            return self._generate_ranking_analysis(queryset, time_range_info,
                                                   self._parse_violation_type(structure.violation_filters),
                                                   self._parse_camera_filter(structure.camera_filters), query)
        elif 'distribution' in analysis_type:
            return self._generate_distribution_analysis(queryset, time_range_info,
                                                        self._parse_camera_filter(structure.camera_filters),
                                                        self._parse_violation_type(structure.violation_filters))
        elif 'comparison' in analysis_type:
            return self._generate_comparison_analysis(queryset, time_range_info, query)
        elif 'listing' in analysis_type:
            return self._generate_listing_analysis(queryset, time_range_info, query)
        else:
            return self._generate_statistical_analysis(queryset, time_range_info,
                                                       self._parse_camera_filter(structure.camera_filters),
                                                       self._parse_violation_type(structure.violation_filters))

    def _parse_violation_type(self, violation_filters: List[str]) -> Optional[str]:
        """解析违规类型过滤条件"""
        for violation_filter in violation_filters:
            if violation_filter.startswith('violation:'):
                return violation_filter.split(':', 1)[1]
        return None

    def _parse_analysis_type(self, analysis_types: List[str]) -> List[str]:
        """解析分析类型"""
        types = []
        for analysis_type in analysis_types:
            if analysis_type.startswith('analysis:'):
                types.append(analysis_type.split(':', 1)[1])
        return types

    def _parse_time_range_v2(self, structure: QueryStructure) -> Dict[str, Any]:
        """
        智能时间解析引擎：根据查询意图选择不同的默认时间范围。
        """
        now = timezone.now()
        # 从 structure 对象中获取所有需要的信息，不再需要外部传入 time_filters
        query_lower = structure.original_query.lower()

        # --- 第一步：优先匹配查询中的显式时间关键词 ---
        # (这部分逻辑与之前完全相同)
        match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', query_lower)
        if match:
            year, month, day = map(int, match.groups())
            try:
                start_time = datetime(year, month, day, 0, 0, 0, tzinfo=now.tzinfo)
                end_time = datetime(year, month, day, 23, 59, 59, tzinfo=now.tzinfo)
                return {'start_time': start_time, 'end_time': end_time, 'description': f"{year}年{month}月{day}日"}
            except ValueError:
                pass
        if '上个月' in query_lower or '上月' in query_lower:
            last_month_end = now.replace(day=1) - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            return {'start_time': last_month_start.replace(hour=0, minute=0, second=0),
                    'end_time': last_month_end.replace(hour=23, minute=59, second=59), 'description': '上个月'}
        if '本月' in query_lower:
            start_time = now.replace(day=1, hour=0, minute=0, second=0)
            return {'start_time': start_time, 'end_time': now, 'description': '本月'}
        if '昨天' in query_lower:
            yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0)
            yesterday_end = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59)
            return {'start_time': yesterday_start, 'end_time': yesterday_end, 'description': '昨天'}
        if '今天' in query_lower:
            today_start = now.replace(hour=0, minute=0, second=0)
            return {'start_time': today_start, 'end_time': now, 'description': '今天'}
        match = re.search(r'(最近|过去|近)?\s*(\d+|半)\s*(天|周|月|年)\s*(内)?', query_lower)
        if match:
            _, num_str, unit = match.groups()[:3]
            num = 0.5 if num_str == '半' else int(num_str)
            if unit == '天':
                delta = timedelta(days=num)
            elif unit == '周':
                delta = timedelta(weeks=num)
            elif unit == '月':
                delta = relativedelta(months=num)
            elif unit == '年':
                delta = relativedelta(years=num)
            if num == 0.5 and unit == '年': delta = relativedelta(months=6)
            start_time = now - delta
            return {'start_time': start_time, 'end_time': now, 'description': match.group(0).strip()}

        # --- 第二步：如果没有任何显式时间，则应用智能默认 ---
        logger.info("查询中未发现显式时间，应用智能默认时间范围。")
        analysis_types = {item.split(':')[1] for item in structure.analysis_types}

        if 'listing' in analysis_types or not analysis_types:
            logger.info("意图为'列举'或'通用查询'，默认使用3小时。")
            return {'start_time': now - timedelta(hours=3), 'end_time': now, 'description': '最近3hs (默认)'}
        else:
            logger.info(f"意图为 {analysis_types}，默认使用24小时。")
            return {'start_time': now - timedelta(hours=24), 'end_time': now, 'description': '最近24hs (默认)'}

    def _build_queryset_v2(self, time_range_info: Dict, camera_filter: str, violation_type: str):
        """
        [重构] V2版本的查询构建，使用精确的 start_time 和 end_time。
        """
        queryset = ViolationRecord.objects.all()

        # 精确时间过滤
        if 'start_time' in time_range_info and 'end_time' in time_range_info:
            queryset = queryset.filter(
                detection_timestamp__gte=time_range_info['start_time'],
                detection_timestamp__lte=time_range_info['end_time']
            )

        if camera_filter:
            queryset = queryset.filter(camera_id__iexact=camera_filter)

        # [ 核心修复 ]
        # 补上被遗漏的、根据违规类型进行筛选的功能
        if violation_type:
            # 从映射关系中获取该违规类型对应的所有数据库字段名
            # 例如 'phone' -> ['phone', 'phone_usage']
            violation_fields = self.violation_mapping.get(violation_type, {}).get('fields', [])

            if violation_fields:
                q_objects = Q()
                for field in violation_fields:
                    # 为每个可能的字段创建一个查询条件，检查其在JSON中的值是否大于0
                    # Django的 __gt 查询可以作用于JSONField内部
                    q_objects |= Q(**{f'violation_data__violations__{field}__gt': 0})

                # 将所有OR条件应用到查询中
                queryset = queryset.filter(q_objects)

        return queryset

    def _generate_listing_analysis(self, queryset, time_range_info: Dict, original_query: str) -> Dict[str, Any]:
        """[格式统一 & Bug修复]"""
        time_desc = time_range_info['description']
        query_lower = original_query.lower()
        records_with_violations = [r for r in queryset if r.total_violations > 0]

        if not records_with_violations:
            reply = f"✅ **查询结果**\n\n_{time_desc}_\n\n在指定时间范围内，未发现任何有效违规记录。"
            return {'success': True, 'reply': reply, 'analysis_type': 'listing_empty'}

        target_is_camera = '摄像头' in query_lower or 'cam' in query_lower

        if target_is_camera:
            active_cameras = sorted(list(set(r.camera_id for r in records_with_violations)))
            reply = f"📋 **违规摄像头列表**\n\n_{time_desc}_\n\n在指定时间范围内，以下 **{len(active_cameras)}** 个摄像头发生了违规：\n\n"
            for cam_id in active_cameras:
                reply += f"- **{cam_id}**\n"
            return {'success': True, 'reply': reply, 'analysis_type': 'listing_cameras'}
        else:  # 默认列出违规类型
            violation_stats = self._get_violation_breakdown(records_with_violations)
            active_types = sorted(violation_stats.keys())
            reply = f"📋 **违规类型列表**\n\n_{time_desc}_\n\n在指定时间范围内，发生了以下 **{len(active_types)}** 种类型的违规：\n\n"
            for v_type in active_types:
                reply += f"- **{self._get_display_name(v_type)}** ({violation_stats[v_type]}次)\n"
            return {'success': True, 'reply': reply, 'analysis_type': 'listing_violation_types'}

    def _generate_statistical_analysis(self, queryset, time_range_info: Dict, camera_filter: Optional[str],
                                       violation_type: Optional[str]) -> Dict[str, Any]:
        """
        [格式统一] 生成统计分析。
        如果指定了violation_type，则提供该类型的详细分析；
        否则，提供一个通用的整体情况摘要。
        """
        time_desc = time_range_info['description']
        records = list(queryset)

        # 1. 构建标准化的回复头部
        reply = f"📊 **数据统计摘要**\n\n_{time_desc}_\n\n"

        # 2. 处理没有数据的情况
        if not records:
            reply += "在指定时间范围内未找到相关数据。"
            return {
                'success': True,
                'reply': reply,
                'analysis_type': 'statistical_empty',
                'data_summary': {}
            }

        # 3. 计算核心统计数据
        total_records = len(records)
        total_violations = sum(record.total_violations for record in records)
        unique_cameras = len(set(record.camera_id for record in records))

        # 4. 根据是否存在特定违规类型筛选，选择不同的分析路径
        if violation_type:
            # --- 路径A: 对特定违规类型进行深度分析 ---
            specific_count = self._count_specific_violations(records, violation_type)
            violation_display = self.violation_mapping.get(violation_type, {}).get('display', violation_type)
            camera_desc = f"{camera_filter}摄像头" if camera_filter else f"{unique_cameras}个摄像头"

            reply += f"**专项分析: {violation_display} ({camera_desc})**\n"
            reply += f"- **违规次数**: {specific_count} 次\n"
            if total_violations > 0:
                percentage = (specific_count / total_violations) * 100
                reply += f"- **占总违规**: {percentage:.1f}%\n"

            # 评估与建议
            if specific_count == 0:
                reply += "- **评估**: ✅ 表现优秀，该类型违规为零。\n"
            elif specific_count <= 5 and total_records > 0:
                reply += "- **评估**: 🟢 情况良好，违规可控。\n"
            elif specific_count <= 15 and total_records > 0:
                reply += "- **评估**: 🟡 需要关注，存在一定数量的违规。\n"
            else:
                reply += "- **评估**: 🔴 重点问题，该类型违规较为频繁，需立即采取措施。\n"
        else:
            # --- 路径B: 提供通用情况的整体摘要 ---
            camera_desc = f"{camera_filter}摄像头" if camera_filter else f"全部监控区域"
            reply += f"**整体情况概览 ({camera_desc})**\n"
            reply += f"- **检测记录**: {total_records} 条\n"
            reply += f"- **违规总数**: {total_violations} 次\n"
            if not camera_filter:
                reply += f"- **涉及摄像头**: {unique_cameras} 个\n"

            # 违规类型分布
            violation_stats = self._get_violation_breakdown(records)
            if violation_stats:
                reply += f"\n**主要违规类型分布**\n"
                sorted_violations = sorted(violation_stats.items(), key=lambda x: x[1], reverse=True)
                for v_type, count in sorted_violations[:3]:  # 最多显示前3名
                    display_name = self._get_display_name(v_type)
                    percentage = (count / total_violations * 100) if total_violations > 0 else 0
                    reply += f"- **{display_name}**: {count}次 (占{percentage:.1f}%)\n"

        return {
            'success': True,
            'reply': reply,
            'analysis_type': 'statistical',
            'data_summary': {
                'total_records': total_records,
                'total_violations': total_violations,
                'unique_cameras': unique_cameras
            }
        }

    def _generate_risk_analysis(self, queryset, time_range_desc: str,
                                camera_filter: str, violation_type: str) -> Dict[str, Any]:
        """生成风险分析"""
        records = list(queryset)

        if not records:
            return {
                'success': True,
                'reply': f"在 {time_range_desc} 内未找到数据进行风险评估。",
                'analysis_type': 'risk'
            }

        # 计算风险分数
        risk_score, risk_breakdown = self._calculate_risk_score(records)

        # 确定风险等级
        if risk_score >= 80:
            risk_level = "🔴 高风险"
            risk_desc = "存在严重安全隐患，需立即采取措施"
        elif risk_score >= 60:
            risk_level = "🟡 中风险"
            risk_desc = "存在一定安全风险，需要及时关注"
        elif risk_score >= 40:
            risk_level = "🟢 低-中风险"
            risk_desc = "存在轻微问题，建议持续关注"
        elif risk_score >= 20:
            risk_level = "🟢 低风险"
            risk_desc = "整体情况良好，存在少量改进空间"
        else:
            risk_level = "✅ 极低风险"
            risk_desc = "安全状况优秀"

        camera_desc = f"{camera_filter}摄像头" if camera_filter else "监控区域"

        reply = f"🛡️ **{time_range_desc} 风险评估报告**\n\n"
        reply += f"**{camera_desc} 风险等级：{risk_level}**\n"
        reply += f"**风险总分：{risk_score:.1f}/100**\n\n"
        reply += f"评估结果：{risk_desc}\n\n"

        # 风险因子分析
        if risk_breakdown:
            reply += "**主要风险因子**\n"
            sorted_risks = sorted(risk_breakdown.items(), key=lambda x: x[1], reverse=True)

            for risk_type, contribution in sorted_risks[:3]:
                if contribution > 0:
                    display_name = self._get_display_name(risk_type)
                    reply += f"• {display_name}：贡献{contribution:.1f}分\n"

        # 改进建议
        reply += f"\n**改进建议**\n"
        if risk_score > 60:
            reply += "• 加强重点区域监管\n• 定期安全培训\n• 完善管理制度"
        elif risk_score > 20:
            reply += "• 保持现有管理水平\n• 持续监控关键指标"
        else:
            reply += "• 继续保持优秀表现\n• 可作为管理标杆"

        return {
            'success': True,
            'reply': reply,
            'analysis_type': 'risk',
            'risk_data': {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'risk_breakdown': risk_breakdown
            }
        }

    def _generate_ranking_analysis(self, queryset, time_range_info: Dict, violation_type: Optional[str],
                                   camera_filter: Optional[str], query: str) -> Dict[str, Any]:
        """[格式统一] 生成排序分析报告"""
        time_desc = time_range_info['description']
        records = list(queryset)

        if not records:
            reply = f"🏆 **排序分析**\n\n_{time_desc}_\n\n在指定时间范围内未找到数据进行排序分析。"
            return {'success': True, 'reply': reply, 'analysis_type': 'ranking_empty'}

        # ... (原有的智能判断排序维度逻辑保持不变)
        ranking_dimension = 'by_type' if camera_filter else 'by_camera'
        if not camera_filter and not violation_type:
            ranking_dimension = 'by_camera' if '摄像头' in query else 'by_type'

        if ranking_dimension == 'by_type':
            title_camera_desc = f" 在 {camera_filter} " if camera_filter else ""
            reply = f"🏆 **违规类型排序**\n\n_{time_desc}{title_camera_desc}_\n\n"
            type_stats = self._get_violation_breakdown(records)
            if not type_stats:
                reply += "未发现可供排序的违规类型数据。"
                return {'success': True, 'reply': reply, 'analysis_type': 'ranking_by_type'}

            # ... (原有排序和结论生成逻辑)
            total_violations = sum(type_stats.values())
            sorted_items = sorted(type_stats.items(), key=lambda x: x[1], reverse=True)
            reply += "**违规类型排行榜**\n"
            for i, (vtype, count) in enumerate(sorted_items[:5], 1):
                display_name = self._get_display_name(vtype)
                percentage = (count / total_violations * 100) if total_violations > 0 else 0
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📍"
                reply += f"{emoji} {display_name}：{count}次 ({percentage:.1f}%)\n"

        else:  # ranking_dimension == 'by_camera'
            violation_display = self.violation_mapping.get(violation_type, {}).get('display',
                                                                                   violation_type) if violation_type else "总体"
            reply = f"🏆 **{violation_display}违规摄像头排序**\n\n_{time_desc}_\n\n"
            camera_stats = defaultdict(int)
            # ... (原有摄像头统计逻辑)
            for record in records:
                count = self._get_specific_violation_count(record,
                                                           violation_type) if violation_type else record.total_violations
                if count > 0:
                    camera_stats[record.camera_id] += count

            if not camera_stats:
                reply += "未发现相关违规数据。"
                return {'success': True, 'reply': reply, 'analysis_type': 'ranking_by_camera'}
            # ... (原有排序和结论生成逻辑)
            total_violations = sum(camera_stats.values())
            sorted_items = sorted(camera_stats.items(), key=lambda x: x[1], reverse=True)
            reply += "**违规摄像头排行榜**\n"
            for i, (camera_id, count) in enumerate(sorted_items[:5], 1):
                percentage = (count / total_violations * 100) if total_violations > 0 else 0
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📍"
                reply += f"{emoji} {camera_id}：{count}次 ({percentage:.1f}%)\n"

        return {'success': True, 'reply': reply, 'analysis_type': 'ranking'}

    def _calculate_enhanced_risk_score(self, records: List[ViolationRecord]) -> Tuple[float, Dict[str, str]]:
        """计算多维度风险分数和生成分析点"""
        if not records:
            return 0.0, {}

        total_violations = sum(r.total_violations for r in records)
        if total_violations == 0:
            return 0.0, {}

        # 维度1: 违规类型严重性 (基础分，占40%)
        violation_stats = self._get_violation_breakdown(records)
        severity_score = 0
        for v_type, count in violation_stats.items():
            severity_score += self.risk_weights.get(v_type.split('_')[0], 1) * count
        normalized_severity = min((severity_score / total_violations) * 4, 40)

        # 维度2: 违规集中度 (时间+空间，占30%)
        # 按小时和摄像头分组
        concentration = defaultdict(int)
        for r in records:
            key = (r.detection_timestamp.strftime('%Y-%m-%d %H'), r.camera_id)
            concentration[key] += r.total_violations

        max_concentration = max(concentration.values()) if concentration else 0
        concentration_score = min((max_concentration / 10) * 30, 30)

        # 维度3: 高危时段作案 (夜间/凌晨，占30%)
        night_violations = sum(
            r.total_violations for r in records if r.detection_timestamp.hour >= 22 or r.detection_timestamp.hour <= 5)
        night_ratio = night_violations / total_violations
        night_score = min(night_ratio * 60, 30)

        total_score = normalized_severity + concentration_score + night_score

        # 生成分析点
        points = {
            "严重性评估": f"高危类型（如吸烟、鼠患）占比较高，基础风险分为 {normalized_severity:.1f}/40。",
            "集中度评估": f"风险高度集中，在单一小时及摄像头内最高并发 {max_concentration} 次违规，集中度风险为 {concentration_score:.1f}/30。",
            "高危时段": f"夜间及凌晨时段（22:00-05:00）发生 {night_violations} 次违规，占总数 {night_ratio:.1%}，时段风险为 {night_score:.1f}/30。"
        }
        return total_score, points

    def _generate_enhanced_risk_analysis(self, queryset, time_range_info: Dict) -> Dict[str, Any]:
        """生成多维度风险评估报告"""
        time_desc = time_range_info['description']
        records = list(queryset)

        reply = f"🛡️ **多维度风险评估报告**\n\n_{time_desc}_\n\n"

        if not records:
            reply += "在指定时间范围内未找到数据进行风险评估。"
            return {'success': True, 'reply': reply, 'analysis_type': 'enhanced_risk_empty'}

        risk_score, points = self._calculate_enhanced_risk_score(records)

        if risk_score >= 75:
            risk_level, risk_desc = "🔴 极高风险", "存在重大安全隐患，需立即全面整改"
        elif risk_score >= 50:
            risk_level, risk_desc = "🟠 高风险", "风险点多且集中，须重点关注并介入"
        elif risk_score >= 25:
            risk_level, risk_desc = "🟡 中等风险", "存在明显违规行为，需要加强日常管理"
        else:
            risk_level, risk_desc = "🟢 低风险", "整体可控，但仍有改进空间"

        reply += f"**综合风险等级: {risk_level} (得分: {risk_score:.1f}/100)**\n\n"
        reply += f"**核心结论**: {risk_desc}。\n\n"
        reply += f"**主要风险维度分析**:\n"
        if risk_score > 50:
            reply += f"- **集中爆发**: {points['集中度评估']}\n"
            reply += f"- **管理漏洞**: {points['高危时段']}\n"
        reply += f"- **违规构成**: {points['严重性评估']}\n"

        return {'success': True, 'reply': reply, 'analysis_type': 'enhanced_risk'}

    def _generate_enhanced_trend_analysis(self, queryset, time_range_info: Dict) -> Dict[str, Any]:
        """生成带有周期性洞察和趋势判断的分析报告"""
        time_desc = time_range_info['description']
        records = list(queryset)

        reply = f"📈 **智能化趋势洞察**\n\n_{time_desc}_\n\n"

        if not records:
            reply += "在指定时间范围内未找到足够数据进行趋势分析。"
            return {'success': True, 'reply': reply, 'analysis_type': 'enhanced_trend_empty'}

        # ... (原有的周期性和趋势判断逻辑保持不变)
        day_of_week_stats = defaultdict(int)
        for r in records:
            day_of_week_stats[r.detection_timestamp.weekday()] += r.total_violations

        periodicity_insight = "数据量不足以分析周内规律。"
        if day_of_week_stats:
            sorted_days = sorted(day_of_week_stats.items(), key=lambda item: item[1], reverse=True)
            days_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            top_day_name = days_map[sorted_days[0][0]]
            periodicity_insight = f"从周期上看，**{top_day_name}** 是违规最高发的日子，可能与周末前的管理松懈或业务高峰有关。"

        start_time = time_range_info['start_time']
        end_time = time_range_info['end_time']
        mid_point = start_time + (end_time - start_time) / 2

        first_half_violations = sum(r.total_violations for r in records if r.detection_timestamp < mid_point)
        second_half_violations = sum(r.total_violations for r in records if r.detection_timestamp >= mid_point)

        trend_insight = "📊 **稳定趋势**: 整体违规数量保持平稳。"
        if first_half_violations > 0:
            change_rate = ((second_half_violations - first_half_violations) / first_half_violations) * 100
            if change_rate > 10:
                trend_insight = f"📈 **恶化趋势**: 后半段违规数比前半段**上升 {change_rate:.0f}%**。"
            elif change_rate < -10:
                trend_insight = f"📉 **改善趋势**: 后半段违规数比前半段**下降 {abs(change_rate):.0f}%**。"

        reply += f"**核心趋势**: {trend_insight}\n"
        reply += f"**周期规律**: {periodicity_insight}\n"

        return {'success': True, 'reply': reply, 'analysis_type': 'enhanced_trend'}

    def _generate_root_cause_analysis(self, queryset, time_range_info: Dict, query: str) -> Dict[str, Any]:
        """根据违规模式，推断可能的管理根源"""
        time_desc = time_range_info['description']
        records = list(queryset)

        reply = f"🤔 **根本原因推断报告**\n\n_{time_desc}_\n\n"

        if not records:
            reply += "数据不足，无法进行原因分析。"
            return {'success': True, 'reply': reply, 'analysis_type': 'root_cause_empty'}

        # ... (原有的原因推断逻辑保持不变)
        violation_stats = self._get_violation_breakdown(records)
        top_violation_type, _ = sorted(violation_stats.items(), key=lambda item: item[1], reverse=True)[0]
        top_violation_name = self._get_display_name(top_violation_type)

        hour_stats = defaultdict(int)
        for r in records:
            if self._get_specific_violation_count(r, top_violation_type.split('_')[0]) > 0:
                hour_stats[r.detection_timestamp.hour] += 1
        top_hour, _ = sorted(hour_stats.items(), key=lambda item: item[1], reverse=True)[0]

        suggestion = "常规性疏忽，建议加强全员安全意识培训。"
        # ... (具体建议逻辑)

        reply += f"**主要问题**: 在所有违规中，**{top_violation_name}** 最为突出。\n"
        reply += f"**高发时段**: 该问题主要集中在 **{top_hour}:00** 附近。\n\n"
        reply += f"**可能原因与建议**: {suggestion}"

        return {'success': True, 'reply': reply, 'analysis_type': 'root_cause'}

    def _generate_comparison_analysis(self, queryset, time_range_info: Dict, original_query: str) -> Dict[str, Any]:
        """[重构] 对比分析的智能路由"""
        query_lower = original_query.lower()

        dual_periods = self._parse_dual_time_ranges(query_lower)
        if dual_periods:
            return self._perform_dual_time_comparison(queryset, dual_periods['period_A'], dual_periods['period_B'])

        camera_matches = re.findall(r'cam[_\-]?\d+|d\d+', query_lower, re.IGNORECASE)
        if len(camera_matches) >= 2:
            cam_a_raw, cam_b_raw = camera_matches[0], camera_matches[1]
            return self._perform_camera_comparison(queryset, self._normalize_camera_id(cam_a_raw),
                                                   self._normalize_camera_id(cam_b_raw), time_range_info)

        if any(keyword in query_lower for keyword in ['对比', '和', '与', 'vs']):
            return self._perform_time_comparison(queryset, time_range_info)

        reply = f"🤔 **对比分析**\n\n_{time_range_info['description']}_\n\n抱歉，我暂时无法理解您的对比维度。"
        return {'success': True, 'reply': reply, 'analysis_type': 'comparison_failed'}

    def _get_time_period_by_keyword(self, keyword: str) -> Optional[Dict]:
        """将时间关键词转换为精确时间范围的工具函数"""
        now = timezone.now()
        keyword_map = {
            '今天': {'start': now.replace(hour=0, minute=0, second=0), 'end': now, 'desc': '今天'},
            '昨天': {'start': (now - timedelta(days=1)).replace(hour=0, minute=0, second=0),
                     'end': (now - timedelta(days=1)).replace(hour=23, minute=59, second=59), 'desc': '昨天'},
            '本周': {'start': (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0), 'end': now,
                     'desc': '本周'},
            '上周': {'start': (now - timedelta(days=now.weekday() + 7)).replace(hour=0, minute=0, second=0),
                     'end': (now - timedelta(days=now.weekday() + 1)).replace(hour=23, minute=59, second=59),
                     'desc': '上周'},
            '本月': {'start': now.replace(day=1, hour=0, minute=0, second=0), 'end': now, 'desc': '本月'},
            '上个月': {'start': (now.replace(day=1) - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0),
                       'end': (now.replace(day=1) - timedelta(days=1)).replace(hour=23, minute=59, second=59),
                       'desc': '上个月'}
        }
        return keyword_map.get(keyword)

    def _parse_dual_time_ranges(self, query: str) -> Optional[Dict]:
        """[重构] 使用中央字典来解析两个时间段"""
        # 从中央字典获取所有支持的关键词
        time_keywords = list(self.TIME_KEYWORD_MAP.keys())

        pattern = re.compile(f"({'|'.join(time_keywords)}).*(和|与|vs|对比).*({'|'.join(time_keywords)})",
                             re.IGNORECASE)
        match = pattern.search(query)

        if not match:
            return None

        keyword_A, _, keyword_B = match.groups()
        # 直接从中央字典查询时间范围
        period_A = self.TIME_KEYWORD_MAP.get(keyword_A)
        period_B = self.TIME_KEYWORD_MAP.get(keyword_B)

        if period_A and period_B:
            return {'period_A': period_A, 'period_B': period_B}
        return None

    def _perform_dual_time_comparison(self, queryset, period_A: Dict, period_B: Dict) -> Dict[str, Any]:
        """[新增] 执行两个独立时间段的对比并生成报告"""
        qs_A = queryset.filter(detection_timestamp__range=(period_A['start'], period_A['end']))
        stats_A = self._get_stats_from_queryset(qs_A)
        qs_B = queryset.filter(detection_timestamp__range=(period_B['start'], period_B['end']))
        stats_B = self._get_stats_from_queryset(qs_B)

        desc_A = period_A['desc']
        desc_B = period_B['desc']

        reply = f"📅 **双重时间对比分析**\n\n_{desc_A} vs {desc_B}_\n\n"
        reply += f"| 指标 | **{desc_A}** | **{desc_B}** |\n"
        reply += f"|:---|:---:|:---:|\n"
        reply += f"| **违规总数** | **{stats_A['violations']}** 次 | **{stats_B['violations']}** 次 |\n"
        reply += f"| 检测记录 | {stats_A['records']} 条 | {stats_B['records']} 条 |\n\n"
        reply += "📊 **分析结论**\n"

        violations_change = stats_A['violations'] - stats_B['violations']
        if violations_change > 0:
            change_rate_str = f"(多 {(violations_change / stats_B['violations'] * 100):.1f}%)" if stats_B[
                                                                                                      'violations'] > 0 else ""
            reply += f"**{desc_A}** 的违规次数比 **{desc_B}** **多 {violations_change} 次** {change_rate_str}。"
        elif violations_change < 0:
            change_rate_str = f"(少 {(abs(violations_change) / stats_B['violations'] * 100):.1f}%)" if stats_B[
                                                                                                           'violations'] > 0 else ""
            reply += f"**{desc_A}** 的违规次数比 **{desc_B}** **少 {abs(violations_change)} 次** {change_rate_str}。"
        else:
            reply += f"**{desc_A}** 与 **{desc_B}** 的违规情况持平。"

        return {'success': True, 'reply': reply, 'analysis_type': 'dual_time_comparison'}

    def _parse_camera_filter(self, camera_filters: List[str]) -> Optional[str]:
        """解析摄像头过滤条件"""
        for camera_filter in camera_filters:
            if camera_filter.startswith('camera_id:'):
                return camera_filter.split(':', 1)[1]
        return None

    def _generate_distribution_analysis(self, queryset, time_range_info: Dict, camera_filter: Optional[str],
                                        violation_type: Optional[str]) -> Dict[str, Any]:
        """[格式统一] 生成时间分布分析"""
        time_desc = time_range_info['description']
        records = list(queryset)

        violation_desc = self.violation_mapping[violation_type]['display'] if violation_type else "违规"
        reply = f"🕒 **{violation_desc}时间分布分析**\n\n_{time_desc}_\n\n"

        if not records:
            reply += "在指定时间范围内未找到数据进行分布分析。"
            return {'success': True, 'reply': reply, 'analysis_type': 'distribution_empty'}

        # ... (原有的时间分布统计逻辑)
        hour_stats = defaultdict(int)
        for record in records:
            hour = record.detection_timestamp.hour
            count = self._get_specific_violation_count(record,
                                                       violation_type) if violation_type else record.total_violations
            hour_stats[hour] += count

        if not hour_stats:
            reply += "未发现相关违规的时间分布数据。"
            return {'success': True, 'reply': reply, 'analysis_type': 'distribution'}

        sorted_hours = sorted(hour_stats.items(), key=lambda x: x[1], reverse=True)
        peak_hours = sorted_hours[:3]

        reply += "**高发时段**\n"
        for hour, count in peak_hours:
            if count > 0:
                time_period = self._get_time_period(hour)
                reply += f"- {hour:02d}:00-{hour + 1:02d}:00 ({time_period})：{count}次\n"

        return {'success': True, 'reply': reply, 'analysis_type': 'distribution'}

    def _calculate_risk_score(self, records: List) -> Tuple[float, Dict[str, float]]:
        """计算风险分数"""
        total_violations = sum(record.total_violations for record in records)
        total_records = len(records)

        if total_violations == 0:
            return 0.0, {}

        # 违规密度分数 (0-60分)
        violation_density = total_violations / total_records
        density_score = min(violation_density * 5, 60)

        # 严重性加权分数 (0-40分)
        violation_stats = self._get_violation_breakdown(records)
        weighted_severity = 0
        risk_breakdown = {}

        for vtype, count in violation_stats.items():
            violation_percentage = count / total_violations
            severity_weight = self.risk_weights.get(vtype.split('_')[0], 1)

            contribution = violation_percentage * severity_weight * 4
            weighted_severity += contribution
            risk_breakdown[vtype] = contribution

        total_risk = min(density_score + weighted_severity, 100)

        return total_risk, risk_breakdown

    def _count_specific_violations(self, records: List, violation_type: str) -> int:
        """统计特定类型违规次数"""
        total_count = 0
        target_fields = self.violation_mapping[violation_type]['fields']

        for record in records:
            try:
                violations = record.violation_data.get('violations', {})
                for field in target_fields:
                    if field in violations:
                        count = violations[field]
                        if isinstance(count, (int, float)) and count > 0:
                            total_count += count
            except:
                continue

        return total_count

    def _get_specific_violation_count(self, record, violation_type: str) -> int:
        """获取单个记录的特定违规次数"""
        target_fields = self.violation_mapping[violation_type]['fields']
        count = 0

        try:
            violations = record.violation_data.get('violations', {})
            for field in target_fields:
                if field in violations:
                    field_count = violations[field]
                    if isinstance(field_count, (int, float)) and field_count > 0:
                        count += field_count
        except:
            pass

        return count

    def _get_violation_breakdown(self, records: List) -> Dict[str, int]:
        """获取违规类型分解"""
        violation_stats = defaultdict(int)

        for record in records:
            try:
                violations = record.violation_data.get('violations', {})
                for vtype, count in violations.items():
                    if isinstance(count, (int, float)) and count > 0:
                        violation_stats[vtype] += count
            except:
                continue

        return dict(violation_stats)

    def _get_display_name(self, vtype: str) -> str:
        """获取显示名称"""
        for violation_type, config in self.violation_mapping.items():
            if vtype in config['fields'] or vtype == violation_type:
                return config['display']
        return vtype

    def _get_time_period(self, hour: int) -> str:
        """获取时段描述"""
        if 6 <= hour < 12:
            return "上午"
        elif 12 <= hour < 18:
            return "下午"
        elif 18 <= hour < 24:
            return "晚上"
        else:
            return "夜间"

    def _normalize_camera_id(self, raw_id: str) -> str:
        """将各种格式的摄像头ID输入标准化为数据库格式（例如 cam_11）。"""

        # 移除所有非字母和数字的字符，并转为小写
        # 例如 "CAM-11" -> "cam11", "d 28" -> "d28"
        clean_id = re.sub(r'[^a-z0-9]', '', raw_id.lower())

        # 规则1：如果是以 'cam' 开头
        if clean_id.startswith('cam'):
            # 提取数字部分
            num_part = re.search(r'\d+$', clean_id)
            if num_part:
                return f"cam_{num_part.group(0)}"

        # 规则2：如果是以 'd' 开头
        if clean_id.startswith('d'):
            num_part = re.search(r'\d+$', clean_id)
            if num_part:
                # 根据您的数据库格式，这里可能需要调整
                # 假设 d11 对应数据库中的 D11 或 cam_11
                # 我们统一输出为小写下划线格式，并在查询时忽略大小写
                return f"cam_{num_part.group(0)}"

        # 如果没有匹配到已知规则，返回清理过的ID，尝试直接查询
        return clean_id

    def _get_stats_from_queryset(self, qs):
        """從 queryset 中提取核心統計數據"""
        stats = qs.aggregate(
            total_violations=Sum('total_violations'),
            total_records=Count('id')
        )
        return {
            'violations': stats.get('total_violations') or 0,
            'records': stats.get('total_records') or 0
        }

    def _perform_camera_comparison(self, queryset, cam_a, cam_b, time_range_info):
        """
        执行两个摄像头之间的对比，并生成表格化报告。
        """
        time_desc = time_range_info.get('description', '指定时间范围内')

        # 1. 分别查询两个摄像头的数据
        qs_a = queryset.filter(camera_id__iexact=cam_a)
        qs_b = queryset.filter(camera_id__iexact=cam_b)

        stats_a = self._get_stats_from_queryset(qs_a)
        stats_b = self._get_stats_from_queryset(qs_b)

        # 2. 准备表格和结论所需的数据
        violation_diff = stats_a['violations'] - stats_b['violations']
        records_diff_val = stats_a['records'] - stats_b['records']

        # 为了美观，给正数差异加上"+"号
        violation_diff_str = f"+{violation_diff}" if violation_diff > 0 else str(violation_diff)
        records_diff_str = f"+{records_diff_val}" if records_diff_val > 0 else str(records_diff_val)

        # 3. 判断优劣，用于结论生成
        winner_cam, loser_cam, winner_stats, loser_stats = (cam_b, cam_a, stats_b, stats_a) if violation_diff > 0 else (
        cam_a, cam_b, stats_a, stats_b)

        # 4. 构造新的回复字符串
        title_cam_a = cam_a.upper().replace('_', '')
        title_cam_b = cam_b.upper().replace('_', '')

        reply = f"📸 **摄像头对比分析**\n\n_{time_desc}_\n\n"
        reply += f"| 指标 | **{cam_a.upper().replace('_', '')}** | **{cam_b.upper().replace('_', '')}** |\n"
        reply += f"|:---|:---:|:---:|\n"
        reply += f"| **违规总数** | **{stats_a['violations']}** 次 | **{stats_b['violations']}** 次 |\n"
        reply += f"| 检测记录 | {stats_a['records']} 条 | {stats_b['records']} 条 |\n\n"
        reply += "📊 **分析结论**\n"
        if stats_a['violations'] != stats_b['violations']:
            percentage_change = (abs(violation_diff) / loser_stats['violations'] * 100) if loser_stats[
                                                                                               'violations'] > 0 else 0
            winner_title = winner_cam.upper().replace('_', '')
            loser_title = loser_cam.upper().replace('_', '')

            reply += f"- **表现更优**: 在本次对比中，**{winner_title}** 的整体表现更佳。\n"
            reply += f"- **关键差异**: 其违规总数比 {loser_title} **减少了 {abs(violation_diff)} 次** (↓{percentage_change:.1f}%)。\n"
            reply += f"- **管理建议**: 建议优先审查 **{loser_title}** 的监控区域，分析其违规高发的原因并采取相应措施。"
        else:
            reply += "- **表现相当**: 两个摄像头的违规数据完全一致，管理水平持平。"

        return {'success': True, 'reply': reply, 'analysis_type': 'comparison_camera'}

    def _perform_time_comparison(self, queryset, time_range_info: Dict) -> Dict[str, Any]:
        """执行“向后看”的单周期时间对比分析"""
        # --- 1. 计算周期 (逻辑不变) ---
        current_start = time_range_info.get('start_time')
        current_end = time_range_info.get('end_time')
        duration = current_end - current_start
        previous_end = current_start - timedelta(seconds=1)
        previous_start = previous_end - duration

        # --- 2. 查询数据 (逻辑不变) ---
        qs_current = queryset.filter(detection_timestamp__range=(current_start, current_end))
        stats_current = self._get_stats_from_queryset(qs_current)
        base_queryset = ViolationRecord.objects.filter(id__in=queryset.values_list('id', flat=True))
        qs_previous = base_queryset.filter(detection_timestamp__range=(previous_start, previous_end))
        stats_previous = self._get_stats_from_queryset(qs_previous)

        # =================================================================
        # [ 核心修复 ] 优化回复的标题、标签和结论，消除语言歧义
        # =================================================================

        # --- 3. 准备更清晰的描述 ---
        current_desc = time_range_info['description']  # 例如 "上个月"
        period_current_dates = f"{current_start.strftime('%m/%d')}-{current_end.strftime('%m/%d')}"
        period_previous_dates = f"{previous_start.strftime('%m/%d')}-{previous_end.strftime('%m/%d')}"

        # --- 4. 构建新的、无歧义的回复 ---
        reply = f"📅 **单周期对比分析**\n\n_{f'查询周期: {current_desc}'}_\n\n"

        # 废弃“本期/上期”，改用更明确的“分析周期/对比周期”
        reply += f"| 指标 | **分析周期 ({period_current_dates})** | **对比周期 ({period_previous_dates})** |\n"
        reply += f"|:---|:---:|:---:|\n"
        reply += f"| **违规总数** | **{stats_current['violations']}** 次 | **{stats_previous['violations']}** 次 |\n"
        reply += "\n**分析结论**\n"

        violations_change = stats_current['violations'] - stats_previous['violations']

        # 在结论中直接点明用户查询的周期，避免混淆
        if violations_change > 0:
            if stats_previous['violations'] > 0:
                change_rate = (violations_change / stats_previous['violations'] * 100)
                reply += f"您查询的 **{current_desc}** ({stats_current['violations']}次) 与其上一周期({stats_previous['violations']}次)相比，违规次数 **增加了 {violations_change} 次** (增长 {change_rate:.1f}%)，情况有所恶化。"
            else:
                reply += f"您查询的 **{current_desc}** ({stats_current['violations']}次) 与其上一周期(无违规)相比，**新增了 {violations_change} 次** 违规，情况有所恶化。"
        elif violations_change < 0:
            change_rate = (abs(violations_change) / stats_previous['violations'] * 100)
            reply += f"您查询的 **{current_desc}** ({stats_current['violations']}次) 与其上一周期({stats_previous['violations']}次)相比，违规次数 **减少了 {abs(violations_change)} 次** (下降 {abs(change_rate):.1f}%)，情况有所改善。"
        else:
            reply += f"您查询的 **{current_desc}** 与其上一周期相比，违规情况持平。"

        return {'success': True, 'reply': reply, 'analysis_type': 'comparison_time'}

    def _generate_trend_analysis(self, queryset, time_range_info: Dict) -> Dict[str, Any]:
        """
        生成趨勢與時間分布分析報告。
        """
        time_desc = time_range_info.get('description', '指定时间范围內')
        records = list(queryset)

        if not records:
            return {
                'success': True,
                'reply': f"在 {time_desc} 內未找到足够的资料进行趋势分析。",
                'analysis_type': 'trend'
            }

        total_violations = sum(r.total_violations for r in records)
        start_date = time_range_info.get('start_time')
        end_date = time_range_info.get('end_time')
        duration_days = (end_date - start_date).days if start_date and end_date else 0

        # --- 決定分析的時間顆粒度 ---
        # 如果時間範圍小於等於2天，則按小時分析；否則按天分析
        if duration_days <= 2:
            # 按小時分布
            stats = queryset.annotate(
                hour=TruncHour('detection_timestamp')
            ).values('hour').annotate(
                count=Sum('total_violations')
            ).order_by('hour')

            unit = "小时"
            peak_times = sorted(stats, key=lambda x: x['count'], reverse=True)[:3]
            reply_body = self._format_hourly_trend(stats, peak_times, total_violations)

        else:
            # 按天分布
            stats = queryset.annotate(
                date=TruncDay('detection_timestamp')
            ).values('date').annotate(
                count=Sum('total_violations')
            ).order_by('date')

            unit = "天"
            peak_times = sorted(stats, key=lambda x: x['count'], reverse=True)[:3]
            reply_body = self._format_daily_trend(stats, peak_times, total_violations)

        reply = f"📈 **{time_desc} 趋势与时间分布分析**\n\n{reply_body}"

        return {
            'success': True,
            'reply': reply,
            'analysis_type': 'trend',
            'trend_data': {
                'unit': unit,
                'stats': list(stats)
            }
        }

    def _format_hourly_trend(self, stats, peak_hours, total_violations) -> str:
        """格式化小時趨勢的文字回覆"""
        if not stats:
            return "未发现违规的小时分布规律。"

        reply = f"**高风险时段分析**\n"
        for item in peak_hours:
            hour = item['hour'].strftime('%H:00')
            count = item['count']
            percentage = (count / total_violations * 100) if total_violations > 0 else 0
            reply += f"• **{hour}**：发生 **{count}** 次违规 (占比 {percentage:.1f}%)\n"

        reply += "\n**管理建议**\n"
        peak_hour_int = peak_hours[0]['hour'].hour
        if 11 <= peak_hour_int <= 13:
            reply += "午餐时间（11:00-13:00）是违规高发期，建议加强该时段的巡查和管理。"
        elif 17 <= peak_hour_int <= 19:
            reply += "晚餐時间（17:00-19:00）是违规高发期，建议加强该时段的巡查和管理。"
        else:
            reply += f"违规主要集中在 {peak_hours[0]['hour'].strftime('%H:00')} 左右，请关注此时段的厨房情况。"

        return reply

    def _format_daily_trend(self, stats, peak_days, total_violations) -> str:
        """格式化每日趨勢的文字回覆"""
        if not stats:
            return "未发现违规的每日分布规律。"

        reply = f"**高风险日期分析**\n"
        for item in peak_days:
            date = item['date'].strftime('%Y-%m-%d')
            count = item['count']
            percentage = (count / total_violations * 100) if total_violations > 0 else 0
            reply += f"• **{date}**：发生 **{count}** 次违规 (占比 {percentage:.1f}%)\n"

        if len(stats) > 1:
            change_rate = ((stats[len(stats) - 1]['count'] - stats[0]['count']) / stats[0]['count'] * 100) if stats[0][
                                                                                                                  'count'] > 0 else 0
            reply += f"\n**整体趋势**\n"
            if change_rate > 10:
                reply += f"与初期相比，违规次數呈现 **明确上升趋势** (增长 {change_rate:.1f}%)，需要警惕。"
            elif change_rate < -10:
                reply += f"与初期相比，违规次數呈现 **明确下降趋势** (减少 {abs(change_rate):.1f}%)，管理措施有效。"
            else:
                reply += "整体违规次数保持在稳定水平。"

        return reply