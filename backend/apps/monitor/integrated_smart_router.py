# apps/monitor/integrated_smart_router.py

import logging
import re
from typing import Dict, List, Any, Optional
from django.utils import timezone
from .enhanced_basic_processor import StructuredQueryProcessor
from .models import ViolationRecord
from django.db.models import Sum, Count, Q
from collections import defaultdict
from datetime import datetime, timedelta
from .janus_pro_service import LanguageModelService

logger = logging.getLogger(__name__)


class IntelligentQueryRouter:
    """智能查询路由器 - 基于结构分析的聪明路由"""

    def __init__(self):
        self.structured_processor = StructuredQueryProcessor()
        self.model_service = LanguageModelService()
        self.TEMPLATE_INTENTS = [
            "get_statistics",
            "get_ranking",
            "get_risk_assessment",
            "get_comparison",
            "get_distribution",
            "get_trend",
            "get_listing",
            "get_root_cause"
        ]

    def get_routing_statistics(self):
        return {'janus_pro_available': self.model_service.is_model_available()}

    def route_and_process(self, query: str, context: Dict = None, custom_time_range: Dict = None) -> Dict[str, Any]:
        """
        主路由和处理入口，实现“模板优先”逻辑。
        """
        # --- 第一步：尝试LLM NLU进行快速意图分析 ---
        nlu_result = self.model_service.get_nlu_analysis(query)

        # --- 第二步：路由决策 ---
        if nlu_result and nlu_result.get("intent") in self.TEMPLATE_INTENTS:
            logger.info(f"NLU Intent '{nlu_result.get('intent')}' matches template. Routing to Structured Processor.")
            return self._process_template_query(query, custom_time_range)
        else:
            # 场景2：意图不匹配模板（如系统介绍、闲聊）或NLU失败。
            # 交给第二次LLM调用进行完整的生成式回答。
            intent = nlu_result.get("intent") if nlu_result else "nlu_failed"
            logger.info(f"NLU Intent '{intent}' requires full generation. Routing to LLM RAG.")

            # RAG流程：为第二次LLM调用准备数据库上下文
            entities = nlu_result.get("entities", {}) if nlu_result else {}
            db_context_str = ""
            if entities:
                db_data = self._fetch_data_from_entities(entities)
                if db_data and db_data.get("total_records", 0) > 0:
                    db_context_str = self._format_data_as_context(db_data)

            # 返回一个字典，让视图知道需要进行流式处理
            return {
                "is_stream": True,
                "query": query,
                "db_context": db_context_str
            }

    def _fetch_data_from_entities(self, entities: Dict) -> Optional[Dict]:
        """
        根据NLU实体获取数据。由Python负责所有业务逻辑和计算。
        """
        logger.info(f"Fetching data from DB based on entities: {entities}")
        queryset = ViolationRecord.objects.all()

        # 1. 时间标准化与过滤 (由Python可靠的解析器完成)
        time_range_text = entities.get('time_range_text')
        time_range_info = None
        if time_range_text:
            logger.info(f"Normalizing time text '{time_range_text}' using Python logic.")
            # 调用 StructuredQueryProcessor 中强大且可靠的时间解析引擎
            time_range_info = self.structured_processor._parse_time_range_v2(time_range_text, [])

        time_desc = "所有时间"
        if time_range_info:
            time_desc = time_range_info.get('description', time_range_text)
            if 'start_time' in time_range_info and 'end_time' in time_range_info:
                queryset = queryset.filter(
                    detection_timestamp__gte=time_range_info['start_time'],
                    detection_timestamp__lte=time_range_info['end_time']
                )

        # 2. 摄像头过滤
        camera_ids = entities.get('camera_id')
        if camera_ids and isinstance(camera_ids, list):
            queryset = queryset.filter(camera_id__in=camera_ids)

        # 3. 违规类型过滤 (针对JSONField的查询)
        violation_types = entities.get('violation_type')
        if violation_types and isinstance(violation_types, list):
            q_objects = Q()
            for v_type in violation_types:
                # 构建查询，检查 violation_data->'violations'->'mask' 这个路径是否存在且不为null
                q_objects |= Q(**{f'violation_data__violations__{v_type}__isnull': False})
            queryset = queryset.filter(q_objects)

        # 4. 执行查询并处理空结果
        records = list(queryset)
        if not records:
            return {"total_records": 0}

        # 5. 数据聚合
        total_records = len(records)
        total_violations = sum(r.total_violations for r in records)

        # 按违规类型聚合
        violation_stats = defaultdict(int)
        for record in records:
            v_data = record.violation_data.get('violations', {})
            for v_type, count in v_data.items():
                # 如果查询中指定了违规类型，则只统计指定的类型
                if not violation_types or v_type in violation_types:
                    violation_stats[v_type] += count

        # 按摄像头聚合 (仅在未指定摄像头时进行)
        camera_stats = defaultdict(int)
        if not camera_ids:
            for record in records:
                camera_stats[record.camera_id] += record.total_violations

        # 6. 返回结构化的聚合数据
        return {
            "total_records": total_records,
            "total_violations": total_violations,
            "time_range_desc": time_desc,
            "camera_filter": camera_ids,
            "violation_filter": violation_types,
            "violation_stats": dict(sorted(violation_stats.items(), key=lambda item: item[1], reverse=True)),
            "camera_stats": dict(sorted(camera_stats.items(), key=lambda item: item[1], reverse=True)),
        }

    def _process_template_query(self, query: str, custom_time_range: Dict = None) -> Dict[str, Any]:
        """
        使用完全独立的 StructuredQueryProcessor 处理模板化查询。
        """
        try:
            result = self.structured_processor.process_structured_query(query, structure=None, custom_time_range=custom_time_range)

            if result.get('success'):
                logger.info("Template-based processor was successful.")
                result['processor_used'] = 'template_based_on_llm_nlu'
                return result
            else:
                raise ValueError("Template processor failed to generate a reply.")
        except Exception as e:
            logger.error(f"Template processor failed: {e}. Falling back to LLM.", exc_info=True)
            # 如果模板处理器失败，降级到完整的LLM生成
            return {
                "is_stream": True,
                "query": query,
                "db_context": ""  # 上下文为空，因为模板化查询通常是结构化的
            }


    def _format_data_as_context(self, data: Dict[str, Any]) -> str:
        """RAG步骤2: 将检索到的数据格式化为供LLM阅读的文本"""

        context_lines = [
            "这是为您从数据库中检索到的实时摘要信息：",
            f"- 时间范围: {data['time_range_desc']}",
            f"- 筛选摄像头: {data['camera_filter'] if data['camera_filter'] else '全部'}",
            f"- 总检测记录数: {data['total_records']}条",
            f"- 总违规次数: {data['total_violations']}次"
        ]

        if data['violation_stats']:
            context_lines.append("\n违规类型分布:")
            for v_type, count in list(data['violation_stats'].items())[:5]:  # 最多显示5种
                percentage = (count / data['total_violations'] * 100) if data['total_violations'] > 0 else 0
                context_lines.append(f"  - {v_type}: {count}次 (占比 {percentage:.1f}%)")

        if data['camera_stats']:
            context_lines.append("\n摄像头违规分布:")
            for cam_id, count in list(data['camera_stats'].items())[:5]:  # 最多显示5个
                percentage = (count / data['total_violations'] * 100) if data['total_violations'] > 0 else 0
                context_lines.append(f"  - {cam_id}: {count}次 (占比 {percentage:.1f}%)")

        context_lines.append("\n请基于以上数据，结合用户的原始问题进行分析和回答。")

        return "\n".join(context_lines)

    def _handle_processing_error(self, query: str, error: str) -> Dict[str, Any]:
        """处理错误情况"""
        return {
            'success': False,
            'reply': '抱歉，处理您的查询时遇到了问题，请稍后再试。',
            'error': error,
            'processor_used': 'error_handler',
            'query': query,
            'timestamp': timezone.now().isoformat()
        }

    def get_routing_statistics(self) -> Dict[str, Any]:
        """提供系统状态"""
        return {'janus_pro_available': self.model_service.is_model_available()}