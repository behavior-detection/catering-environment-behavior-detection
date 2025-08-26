# backend/apps/monitor/views.py

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json
import requests
import logging
import time

# 确保导入了 SystemMonitor, ViolationDataProcessor
from .models import ViolationRecord, AIAnalysisReport, AIQueryHistory, SystemConfig
from .services import JanusAIService, ViolationAnalyzer, SystemMonitor, ViolationDataProcessor

logger = logging.getLogger(__name__)


def violations_dashboard(request):
    """违规数据监控仪表板页面"""
    return render(request, 'monitor/violations_dashboard.html')


@csrf_exempt
@require_http_methods(["GET"])
def violations_analytics(request):
    """获取违规数据分析API"""
    try:
        # 获取查询参数
        time_range = request.GET.get('range', '24h')
        query_all = request.GET.get('all', 'false').lower() == 'true'

        logger.info(f"违规数据分析请求: range={time_range}, query_all={query_all}")

        # 确定时间范围
        hours = 0 if query_all else parse_time_range(time_range)

        # 获取违规记录
        records = list(ViolationRecord.get_violations_by_time_range(hours)) # 使用 list() 转换

        # 构建响应数据
        response_data = build_analytics_response(records, time_range, query_all)

        logger.info(f"违规数据分析完成: {len(records)}条记录")

        return JsonResponse({
            'success': True,
            'data': response_data
        })

    except Exception as e:
        logger.error(f"违规数据分析失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'分析失败: {str(e)}'
        }, status=500)


# --- ↓↓↓ 新增的视图函数，用于处理分析按钮的请求 ↓↓↓ ---
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

# --- 其他视图函数保持不变 ---

@csrf_exempt
@require_http_methods(["POST"])
def ai_query(request):
    """AI智能查询API"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        time_range_hours = data.get('time_range_hours', 24)

        if not query:
            return JsonResponse({
                'success': False,
                'message': '缺少查询内容'
            }, status=400)

        logger.info(f"AI查询请求: {query} (时间范围: {time_range_hours}小时)")

        start_time = time.time()

        try:
            # 调用Janus AI服务
            ai_service = JanusAIService()
            result = ai_service.process_query(query, time_range_hours)

            processing_time = time.time() - start_time

            # 保存查询历史
            query_history = AIQueryHistory.objects.create(
                user=request.user if request.user.is_authenticated else None,
                query=query,
                time_range_hours=time_range_hours,
                query_all_data=(time_range_hours == 0),
                response_data=result,
                success=True,
                processing_time=processing_time
            )

            logger.info(f"AI查询成功: {query} (耗时: {processing_time:.2f}秒)")

            return JsonResponse(result)

        except Exception as ai_error:
            processing_time = time.time() - start_time

            # 保存失败的查询历史
            AIQueryHistory.objects.create(
                user=request.user if request.user.is_authenticated else None,
                query=query,
                time_range_hours=time_range_hours,
                query_all_data=(time_range_hours == 0),
                response_data={},
                success=False,
                error_message=str(ai_error),
                processing_time=processing_time
            )

            raise ai_error

    except Exception as e:
        logger.error(f"AI查询失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'AI查询失败: {str(e)}'
        }, status=500)


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
def system_health(request):
    """系统健康检查API"""
    try:
        # 检查数据库连接
        violation_count = ViolationRecord.objects.count()

        # 检查Janus AI服务
        ai_service = JanusAIService()
        janus_status = ai_service.check_health()

        return JsonResponse({
            'success': True,
            'message': '所有服务正常',
            'services': {
                'database': 'OK',
                'janus_ai_service': 'OK' if janus_status else 'ERROR',
                'violation_records': violation_count
            },
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'健康检查失败: {str(e)}',
            'services': {
                'database': 'ERROR',
                'janus_ai_service': 'ERROR'
            }
        }, status=503)


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
def system_status(request):
    """获取系统详细状态API"""
    try:
        monitor = SystemMonitor()
        status = monitor.get_system_status()

        return JsonResponse({
            'success': True,
            'status': status,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"获取系统状态失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取系统状态失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def batch_upload_violations(request):
    """批量上传违规数据API"""
    try:
        data = json.loads(request.body)

        if not isinstance(data, list):
            return JsonResponse({
                'success': False,
                'message': '数据格式错误，需要数组格式'
            }, status=400)

        processor = ViolationDataProcessor()
        success_count = 0
        error_count = 0
        errors = []

        for i, item in enumerate(data):
            try:
                processed_data = processor.process_yolo_data(item)
                processor.save_processed_data(processed_data)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"第{i + 1}条记录: {str(e)}")

        return JsonResponse({
            'success': True,
            'message': f'批量上传完成',
            'summary': {
                'total': len(data),
                'success': success_count,
                'errors': error_count,
                'error_details': errors[:10]  # 只返回前10个错误
            }
        })

    except Exception as e:
        logger.error(f"批量上传违规数据失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'批量上传失败: {str(e)}'
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


def build_analytics_response(records, time_range, query_all):
    """构建分析响应数据"""
    analyzer = ViolationAnalyzer()
    return analyzer.analyze_records(records, time_range, query_all)