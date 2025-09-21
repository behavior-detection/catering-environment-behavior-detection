# backend/apps/monitor/views.py

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json
import re
import logging
import time
from collections import defaultdict

# 确保导入了 SystemMonitor, ViolationDataProcessor
from .models import ViolationRecord, AIAnalysisReport, AIQueryHistory, SystemConfig
from .janus_pro_service import LanguageModelService
from typing import Dict, List, Any
from .integrated_smart_router import IntelligentQueryRouter
from .apps import get_shared_router
from django.http import StreamingHttpResponse, JsonResponse
from .enhanced_basic_processor import ViolationAnalyzer # <--- 从这里导入 ViolationAnalyzer

logger = logging.getLogger(__name__)


class SmartQueryProcessor:
    """智能查询处理器 - 支持多维度筛选"""

    def __init__(self):
        # 违规类型映射
        self.violation_type_mapping = {
            # 中文 -> 数据库字段
            '口罩': ['mask', 'no_mask'],
            '口罩违规': ['mask', 'no_mask'],
            '未佩戴口罩': ['no_mask'],
            '工作帽': ['hat', 'no_hat'],
            '帽子': ['hat', 'no_hat'],
            '工作帽违规': ['hat', 'no_hat'],
            '未佩戴工作帽': ['no_hat'],
            '吸烟': ['smoking', 'cigarette'],
            '抽烟': ['smoking', 'cigarette'],
            '吸烟行为': ['smoking', 'cigarette'],
            '手机': ['phone', 'phone_usage'],
            '手机使用': ['phone', 'phone_usage'],
            '打电话': ['phone', 'phone_usage'],
            '鼠患': ['mouse', 'mouse_infestation'],
            '老鼠': ['mouse', 'mouse_infestation'],
            '工作服': ['uniform', 'uniform_violation'],
            '制服': ['uniform', 'uniform_violation'],
            '着装': ['uniform', 'uniform_violation'],
        }

        # 中文名称映射（用于显示）
        self.display_names = {
            'mask': '口罩违规',
            'no_mask': '未佩戴口罩',
            'hat': '工作帽违规',
            'no_hat': '未佩戴工作帽',
            'smoking': '吸烟行为',
            'cigarette': '吸烟',
            'phone': '手机使用',
            'phone_usage': '使用手机',
            'mouse': '鼠患问题',
            'mouse_infestation': '鼠患',
            'uniform': '工作服问题',
            'uniform_violation': '工作服违规'
        }

    def parse_query(self, query: str) -> dict:
        """解析查询，提取所有筛选条件"""
        query_lower = query.lower()

        filters = {
            'time_filter': self._extract_time_filter(query_lower),
            'camera_filter': self._extract_camera_filter(query_lower),
            'violation_type_filter': self._extract_violation_type_filter(query_lower),
            'query_intent': self._determine_query_intent(query_lower)
        }

        return filters

    def _extract_time_filter(self, query: str) -> dict:
        """提取时间筛选条件"""
        time_patterns = [
            # 过去X天
            (r'过去\s*(\d+)\s*天', lambda m: int(m.group(1)) * 24),
            (r'最近\s*(\d+)\s*天', lambda m: int(m.group(1)) * 24),
            (r'近\s*(\d+)\s*天', lambda m: int(m.group(1)) * 24),

            # 过去X小时
            (r'过去\s*(\d+)\s*小时', lambda m: int(m.group(1))),
            (r'最近\s*(\d+)\s*小时', lambda m: int(m.group(1))),

            # 过去X周
            (r'过去\s*(\d+)\s*周', lambda m: int(m.group(1)) * 7 * 24),
            (r'最近\s*(\d+)\s*周', lambda m: int(m.group(1)) * 7 * 24),

            # 过去X个月
            (r'过去\s*(\d+)\s*个?月', lambda m: int(m.group(1)) * 30 * 24),
            (r'最近\s*(\d+)\s*个?月', lambda m: int(m.group(1)) * 30 * 24),

            # 特定时间词汇
            (r'今天|当天', lambda m: 24),
            (r'昨天', lambda m: 48),
            (r'本周|这周', lambda m: 7 * 24),
            (r'上周', lambda m: 14 * 24),
            (r'本月|这个月', lambda m: 30 * 24),
            (r'上月|上个月', lambda m: 60 * 24),

            # 所有时间
            (r'所有时间|全部时间|历史|全部数据', lambda m: 0)
        ]

        for pattern, converter in time_patterns:
            match = re.search(pattern, query)
            if match:
                hours = converter(match)
                return {
                    'hours': hours,
                    'description': match.group(0),
                    'is_all_time': hours == 0
                }

        # 默认24小时
        return {'hours': 24, 'description': '最近24小时', 'is_all_time': False}

    def _extract_camera_filter(self, query: str) -> dict:
        """提取摄像头筛选条件"""
        patterns = [
            r'摄像头\s*cam[_-]?(\d+)',
            r'cam[_-]?(\d+)\s*摄像头',
            r'\bcam[_-]?(\d+)\b',
            r'摄像头\s*([a-z]\d+)',
            r'([a-z]\d+)\s*摄像头',
            r'\b([a-z]\d+)\b'
        ]

        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                extracted = match.group(1)
                # 转换为数据库格式
                if extracted.isdigit():
                    camera_id = f"cam_{extracted}"
                else:
                    camera_id = extracted.lower()

                return {
                    'camera_id': camera_id,
                    'original_text': match.group(0)
                }

        return None

    def _extract_violation_type_filter(self, query: str) -> dict:
        """提取违规类型筛选条件"""
        for chinese_name, db_fields in self.violation_type_mapping.items():
            if chinese_name in query:
                return {
                    'chinese_name': chinese_name,
                    'db_fields': db_fields,
                    'primary_field': db_fields[0]
                }

        return None

    def _determine_query_intent(self, query: str) -> str:
        """确定查询意图"""
        if '次数' in query or '多少次' in query:
            return 'count_query'
        elif '哪种' in query or '什么类型' in query or '类型' in query:
            return 'type_analysis'
        elif '哪个摄像头' in query or '摄像头.*最多' in query:
            return 'camera_ranking'
        elif '分析' in query or '统计' in query:
            return 'analysis'
        elif '趋势' in query or '变化' in query:
            return 'trend_analysis'
        else:
            return 'general_query'

    def process_query(self, query: str) -> str:
        """处理查询并返回结果"""
        filters = self.parse_query(query)

        try:
            from .models import ViolationRecord

            # 构建基础查询
            queryset = ViolationRecord.objects.all()

            # 应用时间筛选
            time_filter = filters['time_filter']
            if not time_filter['is_all_time']:
                time_threshold = timezone.now() - timedelta(hours=time_filter['hours'])
                queryset = queryset.filter(detection_timestamp__gte=time_threshold)

            # 应用摄像头筛选
            camera_filter = filters['camera_filter']
            if camera_filter:
                queryset = queryset.filter(camera_id=camera_filter['camera_id'])

            # 根据查询意图处理
            intent = filters['query_intent']
            violation_type_filter = filters['violation_type_filter']

            if intent == 'count_query' and violation_type_filter:
                return self._handle_count_query(
                    queryset, filters, violation_type_filter, camera_filter, time_filter
                )
            elif intent == 'type_analysis':
                return self._handle_type_analysis(queryset, filters, camera_filter, time_filter)
            elif intent == 'camera_ranking':
                return self._handle_camera_ranking(queryset, time_filter)
            else:
                return self._handle_general_query(queryset, filters, time_filter)

        except Exception as e:
            logger.error(f"查询处理失败: {e}")
            return f"处理查询时遇到错误: {str(e)}"

    def _handle_count_query(self, queryset, filters, violation_type_filter, camera_filter, time_filter):
        """处理计数查询"""
        records = list(queryset)
        if not records:
            return f"在{time_filter['description']}内未找到相关数据。"

        # 统计特定违规类型的次数
        target_fields = violation_type_filter['db_fields']
        total_count = 0

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

        # 生成答案
        camera_desc = f"{camera_filter['camera_id']}摄像头" if camera_filter else "所有摄像头"
        violation_name = violation_type_filter['chinese_name']

        answer = f"在{time_filter['description']}内，{camera_desc}的{violation_name}次数：{total_count}次"

        # 添加统计信息
        total_records = len(records)
        total_violations = sum(record.total_violations for record in records)
        if total_violations > 0:
            percentage = (total_count / total_violations * 100)
            answer += f"\n\n统计详情："
            answer += f"\n• 总记录数：{total_records}条"
            answer += f"\n• 总违规次数：{total_violations}次"
            answer += f"\n• {violation_name}占比：{percentage:.1f}%"

        return answer

    def _handle_type_analysis(self, queryset, filters, camera_filter, time_filter):
        """处理违规类型分析查询"""
        records = list(queryset)
        if not records:
            return f"在{time_filter['description']}内未找到相关数据。"

        # 统计所有违规类型
        violation_stats = defaultdict(int)
        total_violations = 0

        for record in records:
            try:
                violations = record.violation_data.get('violations', {})
                for vtype, count in violations.items():
                    if isinstance(count, (int, float)) and count > 0:
                        violation_stats[vtype] += count
                        total_violations += count
            except:
                continue

        if not violation_stats:
            return f"在{time_filter['description']}内未找到具体的违规类型数据。"

        # 排序并生成答案
        sorted_violations = sorted(violation_stats.items(), key=lambda x: x[1], reverse=True)

        camera_desc = f"{camera_filter['camera_id']}摄像头" if camera_filter else "所有摄像头"

        answer = f"在{time_filter['description']}内，{camera_desc}的违规类型分析：\n\n"

        # 显示最多的违规类型
        top_type, top_count = sorted_violations[0]
        top_name = self.display_names.get(top_type, top_type)
        percentage = (top_count / total_violations * 100) if total_violations > 0 else 0

        answer += f"违规最多的类型：{top_name}\n"
        answer += f"违规次数：{top_count}次（占{percentage:.1f}%）\n"

        # 显示其他类型
        if len(sorted_violations) > 1:
            answer += f"\n其他违规类型：\n"
            for vtype, count in sorted_violations[1:min(4, len(sorted_violations))]:
                name = self.display_names.get(vtype, vtype)
                pct = (count / total_violations * 100)
                answer += f"• {name}：{count}次（{pct:.1f}%）\n"

        answer += f"\n总违规次数：{total_violations}次"
        return answer

    def _handle_camera_ranking(self, queryset, time_filter):
        """处理摄像头排名查询"""
        from django.db.models import Sum

        camera_stats = queryset.values('camera_id').annotate(
            total=Sum('total_violations')
        ).filter(total__gt=0).order_by('-total')

        if not camera_stats:
            return f"在{time_filter['description']}内未找到摄像头违规数据。"

        total_all_violations = sum(item['total'] for item in camera_stats)
        top_camera = camera_stats[0]
        percentage = (top_camera['total'] / total_all_violations * 100) if total_all_violations > 0 else 0

        answer = f"在{time_filter['description']}内，摄像头违规排名：\n\n"
        answer += f"违规最多：{top_camera['camera_id']}摄像头\n"
        answer += f"违规次数：{top_camera['total']}次（占{percentage:.1f}%）\n"

        # 显示前5名
        if len(camera_stats) > 1:
            answer += f"\n完整排名：\n"
            for i, camera in enumerate(camera_stats[:5], 1):
                pct = (camera['total'] / total_all_violations * 100)
                answer += f"{i}. {camera['camera_id']}：{camera['total']}次（{pct:.1f}%）\n"

        return answer

    def _handle_general_query(self, queryset, filters, time_filter):
        """处理通用查询"""
        from django.db.models import Sum

        total_records = queryset.count()
        if total_records == 0:
            return f"在{time_filter['description']}内未找到相关数据。"

        total_violations = queryset.aggregate(Sum('total_violations'))['total_violations__sum'] or 0
        camera_count = queryset.values('camera_id').distinct().count()

        camera_filter = filters['camera_filter']
        if camera_filter:
            camera_desc = f"{camera_filter['camera_id']}摄像头"
        else:
            camera_desc = f"{camera_count}个摄像头"

        answer = f"在{time_filter['description']}内，{camera_desc}的统计情况：\n\n"
        answer += f"• 检测记录：{total_records}条\n"
        answer += f"• 违规次数：{total_violations}次\n"

        if not camera_filter and camera_count > 1:
            answer += f"• 涉及摄像头：{camera_count}个\n"

        return answer


class OptimizedAIQueryHandler:
    """优化的AI查询处理器 - 替换views.py中的相关函数"""

    def __init__(self):
        self.router = IntelligentQueryRouter()

    def handle_ai_query_request(self, request_data: Dict) -> Dict[str, Any]:
        """处理AI查询请求 - 替换views.py中的ai_query函数逻辑"""

        query = request_data.get('query', '').strip()
        context = request_data.get('context', {})

        if not query:
            return {
                'success': False,
                'message': '查询内容不能为空'
            }

        # 使用智能路由器处理
        result = self.router.route_and_process(query, context)

        # 添加时间戳
        result['timestamp'] = timezone.now().isoformat()

        return result

    def handle_chat_query_request(self, conversation_id: str, user_message: str,
                                  context: List[Dict] = None) -> Dict[str, Any]:
        """处理聊天查询请求 - 集成对话上下文"""

        # 分析对话上下文
        enhanced_context = self._analyze_conversation_context(context, user_message)

        # 使用智能路由处理
        result = self.router.route_and_process(user_message, enhanced_context)

        # 添加对话相关信息
        result['conversation_id'] = conversation_id
        result['context_info'] = enhanced_context

        return result

    def _analyze_conversation_context(self, context: List[Dict], current_message: str) -> Dict:
        """分析对话上下文"""
        if not context:
            return {}

        # 提取上下文中的关键信息
        context_info = {
            'previous_cameras': [],
            'previous_violations': [],
            'previous_time_ranges': [],
            'conversation_focus': None
        }

        # 分析最近几条消息
        for msg in context[-3:]:
            if msg.get('type') == 'user':
                msg_structure = self.router.structure_analyzer.analyze_query_structure(msg.get('content', ''))
                context_info['previous_cameras'].extend(msg_structure.camera_filters)
                context_info['previous_violations'].extend(msg_structure.violation_filters)
                context_info['previous_time_ranges'].extend(msg_structure.time_filters)

        # 去重
        context_info['previous_cameras'] = list(set(context_info['previous_cameras']))
        context_info['previous_violations'] = list(set(context_info['previous_violations']))
        context_info['previous_time_ranges'] = list(set(context_info['previous_time_ranges']))

        return context_info

def handle_general_query(message: str, time_range_hours: int) -> str:
    """处理通用查询"""
    try:
        from .models import ViolationRecord
        from django.db.models import Sum

        # 根据时间范围获取数据
        if time_range_hours == 0 or '所有时间' in message:
            records = ViolationRecord.objects.all()
            time_desc = "所有历史数据"
        else:
            time_threshold = timezone.now() - timedelta(hours=time_range_hours)
            records = ViolationRecord.objects.filter(detection_timestamp__gte=time_threshold)
            time_desc = f"最近{time_range_hours}小时"

        if not records.exists():
            return f"在{time_desc}中未找到违规数据。"

        # 检查是否询问摄像头排名
        if '哪个摄像头' in message or '摄像头.*最多' in message:
            # 统计各摄像头违规次数
            camera_stats = records.values('camera_id').annotate(
                total=Sum('total_violations')
            ).order_by('-total')

            if camera_stats:
                top_camera = camera_stats[0]
                total_all = sum(item['total'] for item in camera_stats)
                percentage = (top_camera['total'] / total_all * 100) if total_all > 0 else 0
                return f"在{time_desc}中，{top_camera['camera_id']}摄像头违规最多，共{top_camera['total']}次违规，占总违规的{percentage:.1f}%"

        # 通用统计回答
        total_records = records.count()
        total_violations = records.aggregate(Sum('total_violations'))['total_violations__sum'] or 0
        camera_count = records.values('camera_id').distinct().count()

        return f"在{time_desc}中，共有{total_records}条记录，{total_violations}次违规，涉及{camera_count}个摄像头。"

    except Exception as e:
        logger.error(f"处理通用查询失败: {e}")
        return f"处理查询时遇到错误: {str(e)}"


def violations_dashboard(request):
    """违规数据监控仪表板页面"""
    return render(request, 'monitor/violations_dashboard.html')


@csrf_exempt
@require_http_methods(["GET"])
def violations_analytics(request):
    """获取违规数据分析API (供 HistoricalData.vue 使用)"""
    try:
        time_range = request.GET.get('range', '24h')
        query_all = request.GET.get('all', 'false').lower() == 'true'
        hours = 0 if query_all else {'1h': 1, '24h': 24, '7d': 168, '30d': 720}.get(time_range, 24)

        records = list(ViolationRecord.get_violations_by_time_range(hours))

        # [核心修复] 实例化新的 ViolationAnalyzer
        analyzer = ViolationAnalyzer()
        response_data = analyzer.analyze_records(records, time_range, query_all)

        logger.info(f"违规数据分析完成: {len(records)}条记录")
        return JsonResponse({'success': True, 'data': response_data})

    except Exception as e:
        logger.error(f"违规数据分析失败: {str(e)}")
        return JsonResponse({'success': False, 'message': f'分析失败: {str(e)}'}, status=500)


# 辅助函数
def parse_time_range(time_range):
    """解析时间范围参数"""
    time_mapping = {
        '1h': 1,
        '24h': 24,
        '7d': 24 * 7,
        '30d': 24 * 30,
        'all': 0
    }
    return time_mapping.get(time_range, 24)


# --- 用于处理分析按钮的请求 ---
@csrf_exempt
@require_http_methods(["GET"])
def analyze_violation_record(request, record_id):
    """获取单条违规记录的详细分析API"""
    try:
        # 从数据库中获取指定ID的记录
        record = ViolationRecord.objects.get(pk=record_id)

        # 准备要返回的详细数据
        # 这里使用了您模型中的字段和属性，确保数据真实
        analysis_data = {
            'id': record.id,
            'camera_id': record.camera_id,
            'timestamp': record.detection_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'total_violations': record.total_violations,
            'violations': record.formatted_violations, # 使用模型中的 property 获取格式化的违规字典
            'image_path': record.image_path, # 使用模型中定义的 image_path 字段
            'analysis_notes': f"记录 {record.id} 发生在摄像头 {record.camera_id}，共检测到 {record.total_violations} 次违规。",
            'created_at': record.created_at.isoformat(),
        }

        return JsonResponse({'success': True, 'data': analysis_data})

    except ViolationRecord.DoesNotExist:
        return JsonResponse({'success': False, 'message': '记录不存在'}, status=404)
    except Exception as e:
        logger.error(f"分析记录ID {record_id} 失败: {str(e)}")
        return JsonResponse({'success': False, 'message': f'分析失败: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_violation_record(request):
    """保存违规记录API"""
    try:
        data = json.loads(request.body)

        camera_id = data.get('camera_id')
        detection_timestamp = data.get('detection_timestamp')
        violation_data = data.get('violation_data')
        total_violations = data.get('total_violations', 0)
        image_path = data.get('image_path')

        if not camera_id or not detection_timestamp:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        # 解析时间戳
        if isinstance(detection_timestamp, str):
            detection_timestamp = datetime.fromisoformat(
                detection_timestamp.replace('Z', '+00:00')
            )

        # 处理违规数据
        if isinstance(violation_data, str):
            violation_data = json.loads(violation_data)

        # 创建违规记录
        record = ViolationRecord.objects.create(
            camera_id=camera_id,
            detection_timestamp=detection_timestamp,
            violation_data=violation_data,
            image_path=image_path,
            total_violations=total_violations
        )

        logger.info(f"违规记录保存成功: ID={record.id}, 摄像头={camera_id}")

        return JsonResponse({
            'success': True,
            'message': '违规记录已保存',
            'record_id': record.id
        })

    except Exception as e:
        logger.error(f"保存违规记录失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'保存失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def violations_list(request):
    """获取违规记录列表API"""
    try:
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        camera_id = request.GET.get('camera_id')

        # 构建查询
        queryset = ViolationRecord.objects.all()

        if camera_id:
            queryset = queryset.filter(camera_id=camera_id)

        # 分页
        paginator = Paginator(queryset, limit)
        page_obj = paginator.get_page(page)

        # 序列化数据
        records = []
        for record in page_obj:
            records.append({
                'id': record.id,
                'camera_id': record.camera_id,
                'detection_timestamp': record.detection_timestamp.isoformat(),
                'violation_data': record.violation_data,
                'image_path': record.image_path,
                'total_violations': record.total_violations,
                'created_at': record.created_at.isoformat()
            })

        return JsonResponse({
            'success': True,
            'data': {
                'records': records,
                'pagination': {
                    'current_page': page,
                    'per_page': limit,
                    'total': paginator.count,
                    'total_pages': paginator.num_pages
                }
            }
        })

    except Exception as e:
        logger.error(f"获取违规记录列表失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'查询失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def violations_stats(request):
    """获取违规统计数据API"""
    try:
        time_range = request.GET.get('range', '24h')
        hours = parse_time_range(time_range)

        # 获取时间范围内的记录
        records = ViolationRecord.get_violations_by_time_range(hours)

        # 基础统计
        total_records = records.count()
        total_violations = records.aggregate(Sum('total_violations'))['total_violations__sum'] or 0
        active_cameras = records.values('camera_id').distinct().count()

        # 按摄像头统计
        camera_stats = records.values('camera_id').annotate(
            camera_records=Count('id'),
            camera_violations=Sum('total_violations')
        ).order_by('-camera_violations')

        return JsonResponse({
            'success': True,
            'data': {
                'time_range': time_range,
                'summary': {
                    'total_records': total_records,
                    'total_violations': total_violations,
                    'active_cameras': active_cameras,
                    'avg_violations_per_record': round(total_violations / total_records, 2) if total_records > 0 else 0
                },
                'camera_breakdown': list(camera_stats)
            }
        })

    except Exception as e:
        logger.error(f"获取违规统计失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'统计查询失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_violations(request):
    """清空违规数据API"""
    try:
        deleted_count = ViolationRecord.objects.count()
        ViolationRecord.objects.all().delete()

        logger.info(f"已清空 {deleted_count} 条违规记录")

        return JsonResponse({
            'success': True,
            'message': f'成功清空 {deleted_count} 条违规记录',
            'cleared_records': deleted_count,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"清空违规数据失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'清空数据失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def ai_query_history(request):
    """获取AI查询历史API"""
    try:
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))

        # 构建查询
        queryset = AIQueryHistory.objects.all()

        if request.user.is_authenticated:
            queryset = queryset.filter(user=request.user)

        # 分页
        paginator = Paginator(queryset, limit)
        page_obj = paginator.get_page(page)

        # 序列化数据
        history = []
        for record in page_obj:
            history.append({
                'id': record.id,
                'query': record.query,
                'time_range_hours': record.time_range_hours,
                'query_all_data': record.query_all_data,
                'success': record.success,
                'error_message': record.error_message,
                'processing_time': record.processing_time,
                'created_at': record.created_at.isoformat(),
                'response_summary': {
                    'has_result': bool(record.response_data),
                    'total_violations': record.response_data.get('data_summary', {}).get('total_violations',
                                                                                         0) if record.response_data else 0
                }
            })

        return JsonResponse({
            'success': True,
            'data': {
                'history': history,
                'pagination': {
                    'current_page': page,
                    'per_page': limit,
                    'total': paginator.count,
                    'total_pages': paginator.num_pages
                }
            }
        })

    except Exception as e:
        logger.error(f"获取AI查询历史失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'查询失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def export_violations_data(request):
    """导出违规数据API"""
    try:
        import csv
        from django.http import HttpResponse

        time_range = request.GET.get('range', '24h')
        format_type = request.GET.get('format', 'csv')  # csv, json

        hours = parse_time_range(time_range)
        records = ViolationRecord.get_violations_by_time_range(hours)

        if format_type == 'json':
            # JSON格式导出
            data = []
            for record in records:
                data.append({
                    'id': record.id,
                    'camera_id': record.camera_id,
                    'detection_timestamp': record.detection_timestamp.isoformat(),
                    'violation_data': record.violation_data,
                    'total_violations': record.total_violations,
                    'created_at': record.created_at.isoformat()
                })

            response = HttpResponse(
                json.dumps(data, ensure_ascii=False, indent=2),
                content_type='application/json; charset=utf-8'
            )
            response['Content-Disposition'] = f'attachment; filename="violations_data_{time_range}.json"'

        else:
            # CSV格式导出
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="violations_data_{time_range}.csv"'

            writer = csv.writer(response)
            writer.writerow(['ID', '摄像头ID', '检测时间', '违规次数', '违规类型', '创建时间'])

            for record in records:
                violations_str = ', '.join([
                    f"{k}:{v}" for k, v in record.formatted_violations.items()
                ]) if record.formatted_violations else '无'

                writer.writerow([
                    record.id,
                    record.camera_id,
                    record.detection_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    record.total_violations,
                    violations_str,
                    record.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])

        return response

    except Exception as e:
        logger.error(f"导出违规数据失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'导出失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_violation_trends(request):
    """获取违规趋势数据API"""
    try:
        days = int(request.GET.get('days', 7))

        # 获取指定天数的数据
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)

        # 按日期聚合数据
        daily_data = []
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            next_date = current_date + timedelta(days=1)

            day_records = ViolationRecord.objects.filter(
                detection_timestamp__date=current_date
            )

            total_violations = day_records.aggregate(
                Sum('total_violations')
            )['total_violations__sum'] or 0

            total_records = day_records.count()

            # 按类型统计
            violations_by_type = {}
            for record in day_records:
                for vtype, count in record.formatted_violations.items():
                    violations_by_type[vtype] = violations_by_type.get(vtype, 0) + count

            daily_data.append({
                'date': current_date.isoformat(),
                'total_violations': total_violations,
                'total_records': total_records,
                'violations_by_type': violations_by_type,
                'avg_violations_per_record': round(total_violations / total_records, 2) if total_records > 0 else 0
            })

        return JsonResponse({
            'success': True,
            'data': {
                'period': f'{days}天',
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'daily_trends': daily_data,
                'summary': {
                    'total_violations': sum(d['total_violations'] for d in daily_data),
                    'total_records': sum(d['total_records'] for d in daily_data),
                    'avg_daily_violations': round(sum(d['total_violations'] for d in daily_data) / days, 2)
                }
            }
        })

    except Exception as e:
        logger.error(f"获取违规趋势失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取趋势数据失败: {str(e)}'
        }, status=500)


def _filter_by_cameras(result: Dict, camera_ids: List[str]) -> Dict:
    """根据指定摄像头过滤结果"""
    # 这里可以实现按摄像头过滤的逻辑
    # 暂时返回原结果，可以根据需要进一步实现
    return result


def analyze_query_complexity(query: str) -> str:
    """分析查询复杂度"""
    query_lower = query.lower()

    # 复杂查询特征
    complex_features = [
        r'哪个.*最多|哪个.*最少',  # 排序比较查询
        r'比较.*违规率|违规率.*比较',  # 比率分析查询
        r'趋势.*分析|分析.*趋势',  # 趋势分析查询
        r'风险.*评估|评估.*风险',  # 风险评估查询
        r'最近.*天.*哪个',  # 复合时间+比较查询
        r'.*摄像头.*违规.*最多',  # 摄像头排序查询
    ]

    # 语义丰富特征
    semantic_features = [
        r'情况.*如何|如何.*情况',  # 情况分析
        r'(今天|昨天|本周|本月).*违规',  # 明确时间范围
        r'cam_\d+.*违规|违规.*cam_\d+',  # 特定摄像头查询
    ]

    complex_score = sum(1 for pattern in complex_features if re.search(pattern, query_lower))
    semantic_score = sum(1 for pattern in semantic_features if re.search(pattern, query_lower))

    if complex_score >= 1:
        return 'complex'
    elif semantic_score >= 1:
        return 'semantic_rich'
    else:
        return 'simple'


@csrf_exempt
@require_http_methods(["GET"])
def janus_pro_status(request):
    """
    获取Janus-Pro服务（大模型）状态。
    这是路由系统健康检查的一部分。
    """
    try:
        # 正确做法：通过全局路由器访问其包含的模型服务
        router = get_shared_router()
        model_service = router.model_service

        # 从模型服务中获取真实状态
        status_info = {
            'model_available': model_service.is_model_available(),
            'model_id': getattr(model_service, 'model_id', 'N/A'),
        }

        return JsonResponse({
            'success': True,
            'janus_pro_status': status_info,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"获取Janus-Pro状态失败: {e}")
        return JsonResponse({'success': False, 'message': f'获取状态失败: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def smart_ai_query(request):
    """
    统一的智能AI查询入口，现在完全由路由器驱动决策。
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        context = data.get('context', {})

        if not query:
            return JsonResponse({'success': False, 'message': '查询内容不能为空'}, status=400)

        custom_time_range = data.get('custom_time_range', None)
        logger.info(f"收到前端智能查詢: {query}, 自定义时间: {custom_time_range}")
        router = get_shared_router()

        # 调用路由器，它会返回一个决策结果
        decision = router.route_and_process(query, context, custom_time_range)

        if decision.get("is_stream"):
            # --- 场景1：需要LLM生成，返回流式响应 ---
            def event_stream():
                stream_generator = router.model_service.generate_full_response_stream(
                    decision["query"], decision["db_context"]
                )
                try:
                    for token in stream_generator:
                        yield f"data: {json.dumps({'token': token})}\n\n"
                    yield f"data: {json.dumps({'status': 'done'})}\n\n"
                except Exception as e:
                    logger.error(f"流式响应生成时出错: {e}")
                    yield f"data: {json.dumps({'error': '模型生成时发生错误'})}\n\n"

            response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
            response['Cache-Control'] = 'no-cache'
            return response
        else:
            # --- 场景2：模板已处理，直接返回JSON ---
            return JsonResponse(decision)

    except Exception as e:
        logger.error(f"智能查询处理失败: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'reply': '处理查询时发生错误。', 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def routing_system_status(request):
    """獲取路由系統狀態 - 供前端檢查模型可用性"""
    try:
        router = get_shared_router()
        # [修改] 呼叫新的 get_status 方法
        janus_pro_status_str = router.model_service.get_status()

        return JsonResponse({
            'success': True,
            'routing_status': {
                # 'janus_pro_available' 仍可保留，用於簡單判斷
                'janus_pro_available': janus_pro_status_str == 'LOADED',
                # [新增] 提供詳細的狀態字串
                'janus_pro_status': janus_pro_status_str,
                'basic_processor_available': True,
            }
        })
    except Exception as e:
        logger.error(f"获取路由系统状态失败: {e}")
        return JsonResponse({'success': False, 'message': f'获取状态失败: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def analyze_query_structure(request):
    """
    分析查询结构 - 开发调试用。
    注意：此函数在新架构下主要用于调试目的，展示旧的、基于非LLM的结构分析。
    核心路由逻辑已不再依赖它。
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()

        if not query:
            return JsonResponse({'success': False, 'message': '查询内容不能为空'}, status=400)

        # 正确做法：获取全局共享的路由器实例
        router = get_shared_router()

        # 使用路由器内部的结构分析器（如果需要的话）
        # 注意：这里的 structure_analyzer 是旧的逻辑，新的路由依赖LLM NLU
        structure = router.structured_processor.structure_analyzer.analyze_query_structure(query)

        return JsonResponse({
            'success': True,
            'query': query,
            'comment': 'This is a debug endpoint showing analysis from the rule-based structure analyzer.',
            'structure_analysis': {
                'is_structured': structure.is_structured,
                'confidence': structure.confidence,
                'time_filters': structure.time_filters,
                'camera_filters': structure.camera_filters,
                'violation_filters': structure.violation_filters,
                'analysis_types': structure.analysis_types,
                'metrics': structure.metrics
            },
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"分析查询结构失败: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'分析失败: {str(e)}'}, status=500)


# 兼容性函数 - 如果需要支持旧的API接口
@csrf_exempt
@require_http_methods(["POST"])
def enhanced_ai_query_with_smart_routing(request):
    """增强AI查询 - 兼容旧接口但使用新路由"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        time_range_hours = data.get('time_range_hours', 24)

        if not query:
            return JsonResponse({
                'success': False,
                'message': '查询内容不能为空'
            }, status=400)

        # 转换为新格式的上下文
        context = {
            'time_range_hours': time_range_hours,
            'legacy_api': True
        }

        # 调用智能路由处理
        return smart_ai_query_internal(query, context, request.user)

    except Exception as e:
        logger.error(f"兼容接口处理失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'reply': '抱歉，处理您的查询时遇到了问题，请稍后再试。',
            'error': str(e)
        }, status=500)


def smart_ai_query_internal(query: str, context: dict, user=None):
    """内部智能查询处理函数"""
    start_time = time.time()

    router = IntelligentQueryRouter()
    result = router.route_and_process(query, context)

    processing_time = time.time() - start_time

    # 格式化返回数据
    response_data = {
        'success': result.get('success', True),
        'reply': result.get('reply', '处理失败'),
        'routing_info': {
            'processor': result.get('processor_used', 'unknown'),
            'reason': result.get('routing_decision', {}).get('reason', ''),
            'confidence': result.get('routing_decision', {}).get('confidence', 0.0),
            'query_type': result.get('routing_decision', {}).get('factors', {}).get('query_type', 'unknown')
        },
        'processing_time': round(processing_time, 2),
        'timestamp': timezone.now().isoformat(),
        'analysis_method': result.get('processing_method', 'smart_routing')
    }

    return JsonResponse(response_data)


# 健康检查接口
@csrf_exempt
@require_http_methods(["GET"])
def smart_router_health(request):
    """智能路由器健康检查"""
    try:
        router = IntelligentQueryRouter()

        # 测试基本功能
        test_query = "测试查询"
        structure = router.structure_analyzer.analyze_query_structure(test_query)

        health_data = {
            'router_available': True,
            'structure_analyzer_available': structure is not None,
            'janus_pro_available': router.janus_service.is_model_available(),
            'basic_processor_available': True,
            'timestamp': timezone.now().isoformat()
        }

        overall_health = all([
            health_data['router_available'],
            health_data['structure_analyzer_available'],
            health_data['basic_processor_available']
        ])

        return JsonResponse({
            'success': True,
            'overall_health': 'healthy' if overall_health else 'degraded',
            'components': health_data
        })

    except Exception as e:
        logger.error(f"路由器健康检查失败: {e}")
        return JsonResponse({
            'success': False,
            'overall_health': 'error',
            'error': str(e)
        }, status=500)
