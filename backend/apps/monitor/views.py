# apps/monitor/views.py
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from datetime import datetime, timedelta
import json
import re
import logging
import time
import os
import uuid
from django.conf import settings
import redis
import hashlib
from asgiref.sync import sync_to_async
from collections import defaultdict

from .models import DeviceWarehouse, WarehouseFile, ViolationRecord, AIAnalysisReport, AIQueryHistory, SystemConfig, PermissionRequest
from .services import JanusAIService, SystemMonitor, ViolationDataProcessor, AIQueryProcessor
from apps.login.api.models import Manager, Visitor
from .janus_pro_service import LanguageModelService
from typing import Dict, List, Any
from .integrated_smart_router import IntelligentQueryRouter
from .apps import get_shared_router
from django.http import StreamingHttpResponse
from .enhanced_basic_processor import ViolationAnalyzer

logger = logging.getLogger(__name__)

# ====================== 辅助函数（放在最前面）======================

def get_redis_client():
    """获取 Redis 客户端连接"""
    try:
        client = redis.StrictRedis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=getattr(settings, 'REDIS_DB', 0),
            decode_responses=True
        )
        # 测试连接
        client.ping()
        logger.info("Redis 连接成功")
        return client
    except Exception as e:
        logger.error(f"Redis 连接失败: {str(e)}")
        return None

# ====================== 设备仓库管理相关 API ======================

@csrf_exempt
@require_http_methods(["GET"])
def get_warehouses(request):
    """获取设备仓库列表 - 包含类型信息"""
    try:
        eid = request.GET.get('eid')

        if not eid:
            return JsonResponse({
                'success': False,
                'message': '缺少 EID 参数'
            }, status=400)

        warehouses = DeviceWarehouse.objects.filter(eid=eid).order_by('-created_at')

        warehouse_data = []
        for warehouse in warehouses:
            file_count = WarehouseFile.objects.filter(warehouse=warehouse).count()
            warehouse_data.append({
                'id': warehouse.id,
                'name': warehouse.name,
                'eid': warehouse.eid,
                'warehouse_type': warehouse.warehouse_type,
                'warehouse_type_display': warehouse.get_warehouse_type_display(),
                'file_count': file_count,
                'created_at': warehouse.created_at.isoformat(),
                'updated_at': warehouse.updated_at.isoformat()
            })

        logger.info(f"获取仓库列表成功,EID: {eid}, 数量: {len(warehouse_data)}")

        return JsonResponse({
            'success': True,
            'warehouses': warehouse_data,
            'count': len(warehouse_data)
        })

    except Exception as e:
        logger.error(f"获取仓库列表失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'获取仓库列表失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_warehouse(request):
    """创建新的设备仓库 - 支持类型选择"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        eid = data.get('eid', '').strip()
        warehouse_type = data.get('warehouse_type', 'json')  # 新增

        if not name:
            return JsonResponse({
                'success': False,
                'message': '仓库名称不能为空'
            }, status=400)

        if not eid:
            return JsonResponse({
                'success': False,
                'message': '缺少 EID 参数'
            }, status=400)

        # 验证仓库类型
        if warehouse_type not in ['json', 'mp4']:
            return JsonResponse({
                'success': False,
                'message': '无效的仓库类型,必须是 json 或 mp4'
            }, status=400)

        # 检查同一 EID 下是否已存在同名仓库
        existing = DeviceWarehouse.objects.filter(name=name, eid=eid).first()
        if existing:
            return JsonResponse({
                'success': False,
                'message': f'仓库"{name}"已存在'
            }, status=400)

        # 创建新仓库
        warehouse = DeviceWarehouse.objects.create(
            name=name,
            eid=eid,
            warehouse_type=warehouse_type
        )

        logger.info(f"创建仓库成功: {warehouse.name} (ID: {warehouse.id}, EID: {eid}, Type: {warehouse_type})")

        return JsonResponse({
            'success': True,
            'warehouse': {
                'id': warehouse.id,
                'name': warehouse.name,
                'eid': warehouse.eid,
                'warehouse_type': warehouse.warehouse_type,
                'warehouse_type_display': warehouse.get_warehouse_type_display(),
                'file_count': 0,
                'created_at': warehouse.created_at.isoformat(),
                'updated_at': warehouse.updated_at.isoformat()
            },
            'message': f'仓库"{name}"创建成功'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"创建仓库失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'创建仓库失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_warehouse_detail(request, warehouse_id):
    """获取仓库详细信息"""
    try:
        eid = request.GET.get('eid')

        if not eid:
            return JsonResponse({
                'success': False,
                'message': '缺少 EID 参数'
            }, status=400)

        warehouse = DeviceWarehouse.objects.filter(id=warehouse_id, eid=eid).first()

        if not warehouse:
            return JsonResponse({
                'success': False,
                'message': '仓库不存在或无权限访问'
            }, status=404)

        # 获取文件统计信息
        file_count = WarehouseFile.objects.filter(warehouse=warehouse).count()
        total_size = WarehouseFile.objects.filter(warehouse=warehouse).aggregate(
            total=Sum('file_size')
        )['total'] or 0

        warehouse_detail = {
            'id': warehouse.id,
            'name': warehouse.name,
            'eid': warehouse.eid,
            'file_count': file_count,
            'total_size': total_size,
            'created_at': warehouse.created_at.isoformat(),
            'updated_at': warehouse.updated_at.isoformat()
        }

        return JsonResponse({
            'success': True,
            'warehouse': warehouse_detail
        })

    except Exception as e:
        logger.error(f"获取仓库详情失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取仓库详情失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_warehouse(request, warehouse_id):
    """删除设备仓库"""
    try:
        data = json.loads(request.body) if request.body else {}
        # 防御：body可能是纯字符串而非dict（前端直接传EID字符串时）
        if not isinstance(data, dict):
            data = {}
        eid = data.get('eid') or request.GET.get('eid')

        if not eid:
            return JsonResponse({
                'success': False,
                'message': '缺少 EID 参数'
            }, status=400)

        warehouse = DeviceWarehouse.objects.filter(id=warehouse_id, eid=eid).first()

        if not warehouse:
            return JsonResponse({
                'success': False,
                'message': '仓库不存在或无权限访问'
            }, status=404)

        warehouse_name = warehouse.name

        # 删除相关文件（物理文件和数据库记录）
        files = WarehouseFile.objects.filter(warehouse=warehouse)
        deleted_files_count = 0

        for file_record in files:
            try:
                # 删除物理文件
                if os.path.exists(file_record.file_path):
                    os.remove(file_record.file_path)
                deleted_files_count += 1
            except Exception as e:
                logger.warning(f"删除文件失败: {file_record.file_path}, 错误: {e}")

        # 删除数据库记录
        files.delete()
        warehouse.delete()

        logger.info(f"删除仓库成功: {warehouse_name} (ID: {warehouse_id}), 删除文件: {deleted_files_count} 个")

        return JsonResponse({
            'success': True,
            'message': f'仓库"{warehouse_name}"及其 {deleted_files_count} 个文件删除成功'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"删除仓库失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'删除仓库失败: {str(e)}'
        }, status=500)


# ====================== 文件管理相关 API ======================

@csrf_exempt
@require_http_methods(["GET"])
def get_warehouse_files(request, warehouse_id):
    """
    获取仓库文件列表
    支持JSON和MP4文件
    """
    try:
        eid = request.GET.get('eid')

        if not eid:
            return JsonResponse({
                'success': False,
                'message': '缺少 EID 参数'
            }, status=400)

        warehouse = DeviceWarehouse.objects.filter(id=warehouse_id, eid=eid).first()

        if not warehouse:
            return JsonResponse({
                'success': False,
                'message': '仓库不存在或无权限访问'
            }, status=404)

        # 获取文件列表
        files = WarehouseFile.objects.filter(warehouse=warehouse).order_by('-created_at')

        file_data = []
        for file_record in files:
            file_item = {
                'id': file_record.id,
                'file_name': file_record.file_name,
                'file_path': file_record.file_path,
                'file_type': file_record.file_type,  # 'json' 或 'mp4'
                'upload_date': file_record.upload_date.isoformat(),
                'file_size': file_record.file_size,
                'status': file_record.status,
                'created_at': file_record.created_at.isoformat()
            }

            # 为MP4文件添加URL
            if file_record.file_type == 'mp4':
                file_item['stream_url'] = f'/api/monitor/files/{file_record.id}/content/?eid={eid}&stream=true'
                file_item['download_url'] = f'/api/monitor/files/{file_record.id}/content/?eid={eid}&download=true'

            file_data.append(file_item)

        logger.info(
            f"获取仓库文件列表成功，仓库ID: {warehouse_id}, "
            f"文件数量: {len(file_data)}, "
            f"JSON: {sum(1 for f in file_data if f['file_type'] == 'json')}, "
            f"MP4: {sum(1 for f in file_data if f['file_type'] == 'mp4')}"
        )

        return JsonResponse({
            'success': True,
            'files': file_data,
            'count': len(file_data),
            'file_types': {
                'json': sum(1 for f in file_data if f['file_type'] == 'json'),
                'mp4': sum(1 for f in file_data if f['file_type'] == 'mp4')
            },
            'warehouse': {
                'id': warehouse.id,
                'name': warehouse.name,
                'warehouse_type': warehouse.warehouse_type
            }
        })

    except Exception as e:
        logger.error(f"获取仓库文件列表失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取文件列表失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def upload_files(request):
    """上传文件到仓库 - 根据仓库类型验证文件"""
    try:
        warehouse_id = request.POST.get('warehouseId')
        eid = request.POST.get('eid')
        upload_date_str = request.POST.get('uploadDate')

        if not all([warehouse_id, eid, upload_date_str]):
            return JsonResponse({
                'success': False,
                'message': '缺少必需参数: warehouseId, eid, uploadDate'
            }, status=400)

        # 验证仓库权限
        warehouse = DeviceWarehouse.objects.filter(id=warehouse_id, eid=eid).first()
        if not warehouse:
            return JsonResponse({
                'success': False,
                'message': '仓库不存在或无权限访问'
            }, status=404)

        # 解析上传日期
        try:
            upload_date = datetime.strptime(upload_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': '日期格式错误,应为 YYYY-MM-DD'
            }, status=400)

        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files:
            return JsonResponse({
                'success': False,
                'message': '没有选择文件'
            }, status=400)

        # 创建存储目录
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'warehouses', str(warehouse_id), upload_date_str)
        os.makedirs(upload_dir, exist_ok=True)

        saved_files = []
        failed_files = []

        for uploaded_file in uploaded_files:
            try:
                # 根据仓库类型验证文件格式
                file_extension = os.path.splitext(uploaded_file.name)[1].lower()

                if warehouse.warehouse_type == 'json':
                    if file_extension != '.json':
                        failed_files.append({
                            'name': uploaded_file.name,
                            'error': '此仓库只接受 JSON 格式文件'
                        })
                        continue

                    # 验证 JSON 格式
                    try:
                        file_content = uploaded_file.read()
                        json.loads(file_content.decode('utf-8'))
                        uploaded_file.seek(0)
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        failed_files.append({
                            'name': uploaded_file.name,
                            'error': f'JSON 格式错误: {str(e)}'
                        })
                        continue

                elif warehouse.warehouse_type == 'mp4':
                    if file_extension != '.mp4':
                        failed_files.append({
                            'name': uploaded_file.name,
                            'error': '此仓库只接受 MP4 格式文件'
                        })
                        continue

                # 生成唯一文件名
                unique_filename = f"{uuid.uuid4().hex}{file_extension}"
                file_path = os.path.join(upload_dir, unique_filename)

                # 保存文件
                with open(file_path, 'wb') as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)

                # 创建数据库记录
                file_record = WarehouseFile.objects.create(
                    warehouse=warehouse,
                    file_name=uploaded_file.name,
                    file_path=file_path,
                    upload_date=upload_date,
                    eid=eid,
                    file_size=uploaded_file.size,
                    file_type=warehouse.warehouse_type,
                    status='uploaded'
                )

                saved_files.append({
                    'id': file_record.id,
                    'name': file_record.file_name,
                    'size': file_record.file_size,
                    'type': file_record.file_type,
                    'upload_date': upload_date_str
                })

                logger.info(f"文件上传成功: {uploaded_file.name} -> {file_path}")

            except Exception as e:
                logger.error(f"上传文件失败: {uploaded_file.name}, 错误: {str(e)}")
                failed_files.append({
                    'name': uploaded_file.name,
                    'error': str(e)
                })

        # 构建响应
        response_data = {
            'success': True,
            'files': saved_files,
            'uploaded_count': len(saved_files),
            'message': f'成功上传 {len(saved_files)} 个文件'
        }

        if failed_files:
            response_data['failed_files'] = failed_files
            response_data['failed_count'] = len(failed_files)
            response_data['message'] += f',{len(failed_files)} 个文件失败'

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'文件上传失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_file_content(request, file_id):
    """获取文件内容或下载文件 - 最终修复版"""
    try:
        eid = request.GET.get('eid')
        download = request.GET.get('download', 'false').lower() == 'true'
        stream = request.GET.get('stream', 'false').lower() == 'true'

        logger.info(f"=== 文件内容请求 START === ID: {file_id}, EID: {eid}, download: {download}, stream: {stream}")

        if not eid:
            return JsonResponse({
                'success': False,
                'message': '缺少 EID 参数'
            }, status=400)

        file_record = WarehouseFile.objects.filter(id=file_id, eid=eid).first()

        if not file_record:
            return JsonResponse({
                'success': False,
                'message': '文件不存在或无权限访问'
            }, status=404)

        logger.info(f"文件记录: name={file_record.file_name}, type_db='{file_record.file_type}'")

        # 处理文件路径
        actual_path = file_record.file_path if os.path.isabs(file_record.file_path) else os.path.join(
            settings.MEDIA_ROOT, file_record.file_path)

        if not os.path.exists(actual_path):
            logger.error(f"文件不存在: {actual_path}")
            return JsonResponse({
                'success': False,
                'message': '文件物理路径不存在'
            }, status=404)

        logger.info(f"文件物理路径: {actual_path}")

        # 🔧 核心修复：通过文件头判断类型
        is_mp4_file = False

        try:
            with open(actual_path, 'rb') as f:
                header = f.read(12)
                logger.info(f"文件头: {header[:8].hex()}")

                if len(header) >= 8 and header[4:8] == b'ftyp':
                    is_mp4_file = True
                    logger.info(f"✓ 检测到MP4文件头")
                else:
                    logger.info(f"✓ 非MP4文件")

        except Exception as e:
            logger.error(f"读取文件头失败: {e}")
            # 回退到扩展名判断
            file_extension = os.path.splitext(file_record.file_name)[1].lower()
            is_mp4_file = (file_extension == '.mp4')
            logger.info(f"回退判断: 扩展名={file_extension}, is_mp4={is_mp4_file}")

        # ⭐ 关键：根据检测结果强制分发处理
        if is_mp4_file:
            logger.info(f"=> 路由到 MP4 处理器")
            return handle_mp4_file(actual_path, file_record, download, stream, request)
        else:
            logger.info(f"=> 路由到 JSON 处理器")
            return handle_json_file(actual_path, file_record, download)

    except Exception as e:
        logger.error(f"获取文件内容失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'获取文件内容失败: {str(e)}'
        }, status=500)


def handle_json_file(file_path, file_record, download):
    """处理JSON文件 - 带二进制保护"""
    logger.info(f"[JSON处理器] 开始处理: {file_path}")

    try:
        # 🔧 二进制文件保护
        with open(file_path, 'rb') as f:
            header = f.read(12)

            # 检测MP4
            if len(header) >= 8 and header[4:8] == b'ftyp':
                logger.error(f"[JSON处理器] 错误: 这是MP4文件!")
                return JsonResponse({
                    'success': False,
                    'message': '该文件是视频文件(MP4),无法以JSON格式查看。请使用视频播放功能。',
                    'file_type_mismatch': True,
                    'actual_type': 'mp4',
                    'suggestion': '请联系管理员更新文件类型标记'
                }, status=400)

            # 检测二进制
            text_chars = set(range(32, 127)) | {9, 10, 13}
            binary_count = sum(1 for byte in header if byte not in text_chars)

            if binary_count > 6:
                logger.error(f"[JSON处理器] 二进制文件检测: {binary_count}/12 非文本字节")
                return JsonResponse({
                    'success': False,
                    'message': '该文件是二进制格式,无法以文本方式查看',
                    'file_type_mismatch': True,
                    'suggestion': '该文件可能不是JSON格式'
                }, status=400)

        # 下载模式
        if download:
            logger.info(f"[JSON处理器] 下载模式")
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/json')
                response['Content-Disposition'] = f'attachment; filename="{file_record.file_name}"'
                return response

        # 读取JSON
        logger.info(f"[JSON处理器] 尝试解析JSON")
        content = None
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312']
        last_error = None

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = json.load(f)
                logger.info(f"[JSON处理器] 成功使用 {encoding} 编码")
                break
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                last_error = e
                continue

        if content is None:
            logger.error(f"[JSON处理器] 所有编码失败: {last_error}")
            return JsonResponse({
                'success': False,
                'message': f'无法读取JSON内容。错误: {str(last_error)}',
                'encodings_tried': encodings
            }, status=400)

        logger.info(f"[JSON处理器] 成功返回JSON内容")
        return JsonResponse({
            'success': True,
            'file_type': 'json',
            'content': content,
            'file_info': {
                'name': file_record.file_name,
                'size': file_record.file_size,
                'upload_date': file_record.upload_date.isoformat(),
                'created_at': file_record.created_at.isoformat()
            }
        })

    except Exception as e:
        logger.error(f"[JSON处理器] 处理失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'处理文件失败: {str(e)}'
        }, status=500)


def handle_mp4_file(file_path, file_record, download, stream, request):
    """处理MP4视频文件"""
    logger.info(f"[MP4处理器] 开始处理: {file_path}")

    try:
        # 验证确实是MP4
        with open(file_path, 'rb') as f:
            header = f.read(12)
            if len(header) < 8 or header[4:8] != b'ftyp':
                logger.error(f"[MP4处理器] MP4格式验证失败")
                return JsonResponse({
                    'success': False,
                    'message': '文件格式验证失败:不是有效的MP4视频文件',
                    'file_type_mismatch': True
                }, status=400)

        file_size = os.path.getsize(file_path)
        logger.info(f"[MP4处理器] 文件大小: {file_size} bytes")

        # 下载模式
        if download:
            logger.info(f"[MP4处理器] 下载模式")
            from django.http import FileResponse
            response = FileResponse(
                open(file_path, 'rb'),
                content_type='video/mp4'
            )
            response['Content-Disposition'] = f'attachment; filename="{file_record.file_name}"'
            response['Content-Length'] = file_size
            return response

        # 流式播放
        if stream:
            logger.info(f"[MP4处理器] 流式播放模式")
            import re
            range_header = request.META.get('HTTP_RANGE', '').strip()
            range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)

            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                length = end - start + 1

                logger.info(f"[MP4处理器] Range请求: {start}-{end}/{file_size}")

                with open(file_path, 'rb') as f:
                    f.seek(start)
                    data = f.read(length)

                from django.http import HttpResponse
                response = HttpResponse(data, content_type='video/mp4', status=206)
                response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                response['Content-Length'] = length
                response['Accept-Ranges'] = 'bytes'
                return response
            else:
                from django.http import FileResponse
                response = FileResponse(
                    open(file_path, 'rb'),
                    content_type='video/mp4'
                )
                response['Content-Length'] = file_size
                response['Accept-Ranges'] = 'bytes'
                return response

        # 默认返回文件信息
        logger.info(f"[MP4处理器] 返回文件信息")
        return JsonResponse({
            'success': True,
            'file_type': 'mp4',
            'file_info': {
                'id': file_record.id,
                'name': file_record.file_name,
                'size': file_record.file_size,
                'upload_date': file_record.upload_date.isoformat(),
                'created_at': file_record.created_at.isoformat(),
                'file_type': 'mp4'
            },
            'stream_url': f'/api/monitor/files/{file_record.id}/content/?eid={file_record.eid}&stream=true',
            'download_url': f'/api/monitor/files/{file_record.id}/content/?eid={file_record.eid}&download=true'
        })

    except Exception as e:
        logger.error(f"[MP4处理器] 处理失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'处理视频文件失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_files_by_date(request):
    """
    根据日期获取文件列表（供visitor使用access_token访问）
    支持JSON和MP4文件
    """
    try:
        access_token = request.GET.get('access_token')

        if not access_token:
            return JsonResponse({
                'success': False,
                'message': '缺少access_token参数'
            }, status=400)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        token_key = f'access:token:{access_token}'
        token_data = redis_client.get(token_key)

        if not token_data:
            return JsonResponse({
                'success': False,
                'message': 'access_token无效或已过期',
                'valid': False
            }, status=403)

        token_info = json.loads(token_data)

        if token_info.get('access_type') != 'time':
            return JsonResponse({
                'success': False,
                'message': '此token不是时间类型权限'
            }, status=403)

        target_date = token_info.get('access_value')
        eid = token_info.get('eid')

        if not target_date or not eid:
            return JsonResponse({
                'success': False,
                'message': 'token信息不完整'
            }, status=400)

        try:
            from datetime import datetime as dt
            date_obj = dt.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': '日期格式错误'
            }, status=400)

        # 获取该EID下该日期的所有文件（包括JSON和MP4）
        warehouses = DeviceWarehouse.objects.filter(eid=eid)
        files = WarehouseFile.objects.filter(
            warehouse__in=warehouses,
            upload_date=date_obj
        ).order_by('-created_at')

        if not files.exists():
            return JsonResponse({
                'success': True,
                'files': [],
                'count': 0,
                'message': f'未找到日期 {target_date} 的文件',
                'date': target_date
            })

        # 构建文件列表
        file_list = []
        for file_record in files:
            file_item = {
                'id': file_record.id,
                'file_name': file_record.file_name,
                'file_path': file_record.file_path,
                'file_type': file_record.file_type,  # 'json' 或 'mp4'
                'upload_date': file_record.upload_date.isoformat(),
                'file_size': file_record.file_size,
                'warehouse_name': file_record.warehouse.name,
                'warehouse_id': file_record.warehouse.id,
                'warehouse_type': file_record.warehouse.warehouse_type,
                'created_at': file_record.created_at.isoformat()
            }

            # 为MP4文件添加流式播放和下载URL
            if file_record.file_type == 'mp4':
                file_item['stream_url'] = f'/api/monitor/files/{file_record.id}/content/?eid={eid}&stream=true'
                file_item['download_url'] = f'/api/monitor/files/{file_record.id}/content/?eid={eid}&download=true'

            file_list.append(file_item)

        logger.info(
            f"Visitor通过token访问日期文件: "
            f"visitor={token_info.get('visitor_name')}, "
            f"date={target_date}, files={len(file_list)}, "
            f"json_count={sum(1 for f in file_list if f['file_type'] == 'json')}, "
            f"mp4_count={sum(1 for f in file_list if f['file_type'] == 'mp4')}"
        )

        return JsonResponse({
            'success': True,
            'files': file_list,
            'count': len(file_list),
            'date': target_date,
            'file_types': {
                'json': sum(1 for f in file_list if f['file_type'] == 'json'),
                'mp4': sum(1 for f in file_list if f['file_type'] == 'mp4')
            },
            'token_info': {
                'visitor_name': token_info.get('visitor_name'),
                'eid': token_info.get('eid'),
                'approved_by': token_info.get('approved_by')
            }
        })

    except Exception as e:
        logger.error(f"获取日期文件失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'获取文件失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_file(request, file_id):
    """删除文件"""
    try:
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}

        if isinstance(data, dict):
            eid = data.get('eid') or request.GET.get('eid')
        else:
            eid = request.GET.get('eid')

        if not eid:
            return JsonResponse({
                'success': False,
                'message': '缺少 EID 参数'
            }, status=400)

        file_record = WarehouseFile.objects.filter(id=file_id, eid=eid).first()

        if not file_record:
            return JsonResponse({
                'success': False,
                'message': '文件不存在或无权限访问'
            }, status=404)

        file_name = file_record.file_name

        db_path = file_record.file_path.replace('\\', '/')
        if os.path.isabs(db_path):
            # 如果依然是绝对路径（如Windows残留），尝试只取文件名部分
            actual_path = os.path.join(settings.MEDIA_ROOT, 'warehouses', str(file_record.warehouse.id), os.path.basename(db_path))
        else:
            # 正常情况下：MEDIA_ROOT + 数据库存的相对路径
            actual_path = os.path.join(settings.MEDIA_ROOT, db_path)

        # 删除物理文件
        try:
            if os.path.exists(actual_path):
                os.remove(actual_path)
                logger.info(f"物理文件删除成功: {actual_path}")
            else:
                logger.warning(f"物理文件不存在，仅删除数据库记录: {actual_path}")
        except Exception as e:
            logger.error(f"删除物理文件异常: {str(e)}")

        # 删除数据库记录
        file_record.delete()

        return JsonResponse({'success': True, 'message': f'文件"{file_name}"删除成功'})

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'删除文件失败: {str(e)}'
        }, status=500)


# ====================== AI 查询相关 API ======================

async def ai_query(request):
    """AI自然语言查询接口 - 异步版（防止 Daphne kill 长时阻塞请求）"""
    # 手动校验请求方法（@require_http_methods 不支持 async view）
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        time_range_hours = data.get('time_range_hours', 24)
        eid = data.get('eid', '')

        if not query:
            return JsonResponse({
                'success': False,
                'message': '查询内容不能为空'
            }, status=400)

        if not eid:
            return JsonResponse({
                'success': False,
                'message': 'AI查询需要提供EID参数'
            }, status=400)

        start_time = time.time()
        logger.info(f"开始AI查询(async): query='{query}', eid={eid}, time_range={time_range_hours}")

        # ✅ 关键修复：用 sync_to_async 把阻塞的 Janus 请求放入线程池
        # thread_sensitive=False 表示可以在任意线程执行，不绑定主线程
        # 这样 Daphne 不会因为事件循环阻塞而 kill 这个请求
        def _run_query():
            processor = AIQueryProcessor()
            return processor.process_natural_language_query(query, time_range_hours, eid)

        run_query_async = sync_to_async(_run_query, thread_sensitive=False)
        result = await run_query_async()

        processing_time = time.time() - start_time
        logger.info(f"AI查询完成，耗时: {processing_time:.2f}秒")

        result['processing_time_seconds'] = round(processing_time, 2)
        result['query_timestamp'] = timezone.now().isoformat()

        # 保存查询历史（DB 操作也要用 sync_to_async）
        def _save_history():
            try:
                AIQueryHistory.objects.create(
                    query=query,
                    time_range_hours=time_range_hours,
                    query_all_data=(time_range_hours == 0),
                    response_data=result,
                    success=result.get('success', True),
                    error_message=result.get('message', '') if not result.get('success') else '',
                    processing_time=processing_time
                )
            except Exception as e:
                logger.warning(f"保存查询历史失败: {e}")

        await sync_to_async(_save_history, thread_sensitive=True)()

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"AI查询失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'AI查询失败: {str(e)}',
            'error_details': str(e)
        }, status=500)


# ✅ 直接设置属性而非用 @csrf_exempt 装饰器
# 部分 Django 版本的 csrf_exempt 会把 async def 包进同步 wrapper，
# 导致调用时返回未 await 的协程而非 HttpResponse
ai_query.csrf_exempt = True


@csrf_exempt
@require_http_methods(["GET"])
def ai_query_history(request):
    """获取 AI 查询历史"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))

        history_queryset = AIQueryHistory.objects.all().order_by('-created_at')
        paginator = Paginator(history_queryset, page_size)

        if page > paginator.num_pages:
            page = 1

        history_page = paginator.page(page)

        history_data = []
        for item in history_page:
            history_data.append({
                'id': item.id,
                'query': item.query,
                'time_range_hours': item.time_range_hours,
                'success': item.success,
                'error_message': item.error_message,
                'processing_time': item.processing_time,
                'created_at': item.created_at.isoformat()
            })

        return JsonResponse({
            'success': True,
            'history': history_data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': history_page.has_next(),
                'has_previous': history_page.has_previous()
            }
        })

    except Exception as e:
        logger.error(f"获取AI查询历史失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取查询历史失败: {str(e)}'
        }, status=500)


# ====================== 系统状态相关 API ======================

@csrf_exempt
@require_http_methods(["GET"])
def system_status(request):
    """获取系统状态"""
    try:
        monitor = SystemMonitor()
        status = monitor.get_system_status()

        return JsonResponse({
            'success': True,
            'status': status
        })

    except Exception as e:
        logger.error(f"获取系统状态失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取系统状态失败: {str(e)}'
        }, status=500)


# ====================== 违规数据相关 API (保留原有实现) ======================

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
def get_violations_by_eid(request):
    """根据 EID 获取违规数据（修复版本 - 支持中文日期格式）"""
    eid = request.GET.get('eid')
    time_range = request.GET.get('range', '24h')

    if not eid:
        return JsonResponse({
            'success': False,
            'message': '缺少 EID 参数'
        }, status=400)

    try:
        logger.info(f"根据 EID 获取违规数据: eid={eid}, range={time_range}")

        # 获取该 EID 下所有仓库的文件
        warehouses = DeviceWarehouse.objects.filter(eid=eid)

        if not warehouses.exists():
            logger.warning(f"未找到 EID {eid} 对应的仓库")
            return JsonResponse({
                'success': True,
                'data': get_empty_analytics_response(time_range),
                'message': f'未找到 EID {eid} 对应的数据',
                'debug_info': {
                    'eid': eid,
                    'warehouses_found': 0
                }
            })

        # 获取所有文件（不基于文件上传时间筛选）
        files = WarehouseFile.objects.filter(warehouse__in=warehouses)

        all_violations = []
        file_count = 0
        processed_file_count = 0
        time_parse_errors = 0

        for file_record in files:
            file_count += 1
            try:
                # 读取 JSON 文件
                if os.path.exists(file_record.file_path):
                    with open(file_record.file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        processed_file_count += 1

                        # 如果是数组，处理每个元素
                        if isinstance(data, list):
                            for item in data:
                                # 标准化违规记录
                                normalized_item = normalize_violation_record_chinese_date(item)
                                if normalized_item:
                                    normalized_item['_eid'] = eid
                                    normalized_item['_file_id'] = file_record.id
                                    normalized_item['_file_path'] = file_record.file_path
                                    all_violations.append(normalized_item)
                                else:
                                    time_parse_errors += 1
                        else:
                            # 单个对象
                            normalized_item = normalize_violation_record_chinese_date(data)
                            if normalized_item:
                                normalized_item['_eid'] = eid
                                normalized_item['_file_id'] = file_record.id
                                normalized_item['_file_path'] = file_record.file_path
                                all_violations.append(normalized_item)
                            else:
                                time_parse_errors += 1

            except Exception as e:
                logger.warning(f"读取文件失败 {file_record.file_path}: {e}")
                continue

        # 基于JSON中的timestamp进行时间筛选
        filtered_violations = filter_violations_by_json_timestamp(all_violations, time_range)

        # 聚合数据
        processed_data = aggregate_violations_data_chinese(filtered_violations, time_range)

        logger.info(
            f"EID {eid} 数据处理完成: {file_count} 个文件, {processed_file_count} 个成功处理, "
            f"{len(all_violations)} 条原始记录, {len(filtered_violations)} 条筛选后记录, "
            f"{time_parse_errors} 个时间解析错误")

        return JsonResponse({
            'success': True,
            'data': processed_data,
            'eid': eid,
            'debug_info': {
                'file_count': file_count,
                'processed_file_count': processed_file_count,
                'raw_records': len(all_violations),
                'filtered_records': len(filtered_violations),
                'time_parse_errors': time_parse_errors,
                'warehouses_count': warehouses.count(),
                'time_range': time_range
            }
        })

    except Exception as e:
        logger.error(f"根据 EID 获取违规数据失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'获取数据失败: {str(e)}',
            'error_details': str(e)
        }, status=500)


def normalize_violation_record_chinese_date(record):
    """标准化违规记录数据格式 - 支持中文日期格式"""
    try:
        if not isinstance(record, dict):
            logger.warning(f"记录不是字典格式: {type(record)}")
            return None

        # 获取时间戳 - 你的JSON格式中字段名是timestamp
        timestamp = record.get('timestamp')
        if not timestamp:
            logger.warning(f"记录缺少timestamp字段: {record}")
            return None

        # 解析中文日期格式
        normalized_timestamp = parse_chinese_datetime(timestamp)
        if not normalized_timestamp:
            logger.error(f"无法解析时间格式: {timestamp}")
            return None

        # 获取违规数据 - 根据你的JSON结构
        violations = record.get('violations', {})
        total_violations = int(record.get('total_violations', 0))

        # 构建标准化记录
        normalized_record = {
            'id': f"json_{record.get('camera_id', 'unknown')}_{int(time.time() * 1000000)}",
            'camera_id': str(record.get('camera_id', 'unknown')),
            'detection_timestamp': normalized_timestamp,
            'timestamp': normalized_timestamp,
            'total_violations': total_violations,
            'violations': violations,
            'formatted_violations': violations,  # 直接使用violations字段
            'class_numbers': record.get('class_numbers', {}),  # 保留class_numbers
            'image_path': '',
            'created_at': normalized_timestamp,
            '_original_timestamp': str(timestamp),
            '_original_format': 'chinese_date'
        }

        return normalized_record

    except Exception as e:
        logger.error(f"标准化记录失败: {e}, record: {record}")
        return None


def parse_chinese_datetime(timestamp_str):
    """解析多种时间格式，兼容中文日期、ISO格式、HH:MM:SS、MM:SS"""
    try:
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

        logger.warning(f"无法识别的时间格式: {timestamp_str}")
        return None

    except Exception as e:
        logger.error(f"时间解析失败: {e}, timestamp: {timestamp_str}")
        return None


def filter_violations_by_json_timestamp(violations, time_range):
    """基于JSON中的timestamp字段进行时间筛选"""
    try:
        if time_range == 'all':
            return violations

        # 计算时间范围
        hours_map = {'1h': 1, '24h': 24, '7d': 168, '30d': 720}
        hours = hours_map.get(time_range, 24)
        cutoff_time = timezone.now() - timedelta(hours=hours)

        filtered_violations = []

        for violation in violations:
            timestamp_str = violation.get('detection_timestamp') or violation.get('timestamp')

            if timestamp_str:
                try:
                    # 解析ISO格式的时间戳
                    violation_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

                    # 确保时区信息
                    if violation_time.tzinfo is None:
                        violation_time = violation_time.replace(tzinfo=timezone.utc)

                    # 时间筛选
                    if violation_time >= cutoff_time:
                        filtered_violations.append(violation)

                except Exception as e:
                    logger.warning(f"时间筛选解析失败: {e}, timestamp: {timestamp_str}")
                    # 如果时间解析失败，仍然包含该记录
                    filtered_violations.append(violation)
            else:
                # 没有时间字段，包含该记录
                filtered_violations.append(violation)

        logger.info(f"时间筛选: 原始{len(violations)}条 -> 筛选后{len(filtered_violations)}条 (范围: {time_range})")
        return filtered_violations

    except Exception as e:
        logger.error(f"时间筛选失败: {e}")
        return violations


def aggregate_violations_data_chinese(violations, time_range):
    """聚合违规数据 - 适配中文数据格式"""
    try:
        total_violations = 0
        violations_by_type = {}
        violations_by_camera = {}
        violations_by_hour = {}
        violations_by_date = {}
        recent_records = []

        # 违规类型中文映射
        violation_type_mapping = {
            'mask': '未佩戴口罩',
            'hat': '未佩戴工作帽',
            'phone': '使用手机',
            'cigarette': '吸烟行为',
            'mouse': '鼠患问题',
            'uniform': '工作服违规',
            'person': '人员检测'
        }

        for violation in violations:
            # 统计总数
            v_count = int(violation.get('total_violations', 0))
            total_violations += v_count

            # 按类型统计 - 从violations字段获取
            formatted_violations = violation.get('violations', {})
            for vtype, count in formatted_violations.items():
                if isinstance(count, (int, float)) and count > 0:
                    violations_by_type[vtype] = violations_by_type.get(vtype, 0) + int(count)

            # 按摄像头统计
            camera_id = violation.get('camera_id', 'unknown')
            violations_by_camera[camera_id] = violations_by_camera.get(camera_id, 0) + v_count

            # 按小时和日期统计
            timestamp = violation.get('detection_timestamp') or violation.get('timestamp')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

                    # 按小时统计
                    hour = dt.hour
                    violations_by_hour[hour] = violations_by_hour.get(hour, 0) + v_count

                    # 按日期统计
                    date_str = dt.date().isoformat()
                    violations_by_date[date_str] = violations_by_date.get(date_str, 0) + v_count

                except Exception as e:
                    logger.warning(f"时间统计失败: {e}")

            # 收集最近记录
            recent_records.append({
                'id': violation.get('id'),
                'camera_id': camera_id,
                'detection_timestamp': timestamp,
                'timestamp': timestamp,
                'total_violations': v_count,
                'formatted_violations': formatted_violations,
                'class_numbers': violation.get('class_numbers', {}),
                'created_at': violation.get('created_at', timestamp),
                '_original_timestamp': violation.get('_original_timestamp')
            })

        # 按时间排序最近记录并限制数量
        recent_records.sort(
            key=lambda x: x.get('detection_timestamp') or x.get('timestamp', ''),
            reverse=True
        )
        recent_records = recent_records[:20]  # 只保留最新20条

        result = {
            'summary': {
                'total_violations': total_violations,
                'total_records': len(violations),
                'active_cameras': len(violations_by_camera),
                'time_description': get_time_description(time_range)
            },
            'violations_by_type': violations_by_type,
            'violations_by_camera': violations_by_camera,
            'violations_by_hour': violations_by_hour,
            'violations_by_date': violations_by_date,
            'recent_records': recent_records,
            'violation_type_mapping': violation_type_mapping
        }

        return result

    except Exception as e:
        logger.error(f"数据聚合失败: {e}")
        return get_empty_analytics_response(time_range)


def get_empty_analytics_response(time_range):
    """获取空的分析响应数据"""
    return {
        'summary': {
            'total_violations': 0,
            'total_records': 0,
            'active_cameras': 0,
            'time_description': get_time_description(time_range)
        },
        'violations_by_type': {},
        'violations_by_camera': {},
        'violations_by_hour': {},
        'violations_by_date': {},
        'recent_records': []
    }


def get_time_description(time_range):
    """获取时间范围描述"""
    time_mapping = {
        '1h': '最近1小时',
        '24h': '最近24小时',
        '7d': '最近7天',
        '30d': '最近30天',
        'all': '所有历史数据'
    }
    return time_mapping.get(time_range, '最近24小时')


@csrf_exempt
@require_http_methods(["GET"])
def get_unified_violations_data(request):
    """统一的违规数据获取接口 - 支持数据库和文件数据"""
    try:
        eid = request.GET.get('eid')
        time_range = request.GET.get('range', '24h')
        source = request.GET.get('source', 'both')  # 'database', 'files', 'both'

        logger.info(f"统一违规数据查询: eid={eid}, range={time_range}, source={source}")

        result = {
            'success': True,
            'data': {
                'summary': {
                    'total_violations': 0,
                    'total_records': 0,
                    'active_cameras': 0,
                    'time_description': get_time_description(time_range)
                },
                'violations_by_type': {},
                'violations_by_camera': {},
                'violations_by_hour': {},
                'recent_records': []
            }
        }

        # 从数据库获取数据
        if source in ['database', 'both']:
            db_data = get_database_violations(eid, time_range)
            result['data'] = merge_violation_data(result['data'], db_data)

        # 从仓库文件获取数据（优先使用这个，因为你的数据在JSON文件中）
        if source in ['files', 'both'] and eid:
            files_data = get_warehouse_files_violations_chinese(eid, time_range)
            result['data'] = merge_violation_data(result['data'], files_data)

        logger.info(f"统一违规数据查询完成: {result['data']['summary']['total_records']} 条记录")

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"获取统一违规数据失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取数据失败: {str(e)}'
        }, status=500)


def get_database_violations(eid, time_range):
    """从数据库获取违规数据"""
    try:
        hours = parse_time_range(time_range)
        records = list(ViolationRecord.get_violations_by_time_range(hours))

        analyzer = ViolationAnalyzer()
        return analyzer.analyze_records(records, time_range, hours == 0)
    except Exception as e:
        logger.error(f"获取数据库违规数据失败: {str(e)}")
        return {}


def get_warehouse_files_violations_chinese(eid, time_range):
    """从仓库文件获取违规数据 - 支持中文日期"""
    try:
        if not eid:
            return {}

        # 获取该 EID 的所有仓库文件
        warehouses = DeviceWarehouse.objects.filter(eid=eid)
        files = WarehouseFile.objects.filter(warehouse__in=warehouses)

        # 处理 JSON 文件数据
        all_violations = []
        for file_record in files:
            try:
                if os.path.exists(file_record.file_path):
                    with open(file_record.file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                        if isinstance(data, list):
                            for item in data:
                                normalized_item = normalize_violation_record_chinese_date(item)
                                if normalized_item:
                                    all_violations.append(normalized_item)
                        else:
                            normalized_item = normalize_violation_record_chinese_date(data)
                            if normalized_item:
                                all_violations.append(normalized_item)
            except Exception as e:
                logger.warning(f"读取文件失败 {file_record.file_path}: {e}")
                continue

        # 基于JSON中的timestamp进行时间筛选
        filtered_violations = filter_violations_by_json_timestamp(all_violations, time_range)

        # 聚合数据
        return aggregate_violations_data_chinese(filtered_violations, time_range)

    except Exception as e:
        logger.error(f"获取仓库文件违规数据失败: {str(e)}")
        return {}


def merge_violation_data(data1, data2):
    """合并两个违规数据集"""
    if not data2:
        return data1

    # 合并汇总数据
    if 'summary' in data2:
        data1['summary']['total_violations'] = (
                data1['summary'].get('total_violations', 0) +
                data2['summary'].get('total_violations', 0)
        )
        data1['summary']['total_records'] = (
                data1['summary'].get('total_records', 0) +
                data2['summary'].get('total_records', 0)
        )

        # 更新活跃摄像头数量
        all_cameras = set()
        all_cameras.update(data1.get('violations_by_camera', {}).keys())
        all_cameras.update(data2.get('violations_by_camera', {}).keys())
        data1['summary']['active_cameras'] = len(all_cameras)

    # 合并违规类型统计
    for vtype, count in data2.get('violations_by_type', {}).items():
        data1['violations_by_type'][vtype] = (
                data1['violations_by_type'].get(vtype, 0) + count
        )

    # 合并摄像头统计
    for camera, count in data2.get('violations_by_camera', {}).items():
        data1['violations_by_camera'][camera] = (
                data1['violations_by_camera'].get(camera, 0) + count
        )

    # 合并按小时统计
    for hour, count in data2.get('violations_by_hour', {}).items():
        data1['violations_by_hour'][hour] = (
                data1['violations_by_hour'].get(hour, 0) + count
        )

    # 合并最近记录
    data1['recent_records'].extend(data2.get('recent_records', []))

    # 按时间排序并仅保留最新 20 条
    data1['recent_records'] = sorted(
        data1['recent_records'],
        key=lambda x: x.get('detection_timestamp') or x.get('timestamp', ''),
        reverse=True
    )[:20]

    return data1



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




@csrf_exempt
@require_http_methods(["GET"])
def analyze_violation_record(request, record_id):
    """获取单条违规记录的详细分析 API"""
    try:
        record = ViolationRecord.objects.get(pk=record_id)
        analysis_data = {
            'id': record.id,
            'camera_id': record.camera_id,
            'timestamp': record.detection_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'total_violations': record.total_violations,
            'violations': record.formatted_violations,
            'image_path': record.image_path,
            'analysis_notes': f"记录 {record.id} 发生在摄像头 {record.camera_id}，共检测到 {record.total_violations} 次违规。",
            'created_at': record.created_at.isoformat(),
        }
        return JsonResponse({'success': True, 'data': analysis_data})
    except ViolationRecord.DoesNotExist:
        return JsonResponse({'success': False, 'message': '记录不存在'}, status=404)
    except Exception as e:
        logger.error(f"分析记录 ID {record_id} 失败: {str(e)}")
        return JsonResponse({'success': False, 'message': f'分析失败: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def system_health(request):
    """系统健康检查 API"""
    try:
        violation_count = ViolationRecord.objects.count()
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


# 其他视图函数的存根（可根据需要进一步实现）
@csrf_exempt
def save_violation_record(request):
    """保存违规记录"""
    return JsonResponse({'success': True, 'message': '功能待实现'})


@csrf_exempt
def batch_upload_violations(request):
    """批量上传违规数据"""
    return JsonResponse({'success': True, 'message': '功能待实现'})


@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def update_warehouse_name(request, warehouse_id):
    """更新仓库名称"""
    try:
        data = json.loads(request.body)
        new_name = data.get('name', '').strip()
        eid = data.get('eid', '').strip()

        if not new_name:
            return JsonResponse({
                'success': False,
                'message': '仓库名称不能为空'
            }, status=400)

        if not eid:
            return JsonResponse({
                'success': False,
                'message': '缺少 EID 参数'
            }, status=400)

        warehouse = DeviceWarehouse.objects.filter(id=warehouse_id, eid=eid).first()
        if not warehouse:
            return JsonResponse({
                'success': False,
                'message': '仓库不存在或无权限访问'
            }, status=404)

        # 检查同一 EID 下是否已存在同名仓库
        existing = DeviceWarehouse.objects.filter(
            name=new_name, eid=eid
        ).exclude(id=warehouse_id).first()

        if existing:
            return JsonResponse({
                'success': False,
                'message': f'仓库名称"{new_name}"已存在'
            }, status=400)

        old_name = warehouse.name
        warehouse.name = new_name
        warehouse.save()

        logger.info(f"仓库名称更新成功: {old_name} -> {new_name} (ID: {warehouse_id})")

        return JsonResponse({
            'success': True,
            'warehouse': {
                'id': warehouse.id,
                'name': warehouse.name,
                'eid': warehouse.eid,
                'created_at': warehouse.created_at.isoformat(),
                'updated_at': warehouse.updated_at.isoformat()
            },
            'message': f'仓库名称已更新为"{new_name}"'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"更新仓库名称失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'更新仓库名称失败: {str(e)}'
        }, status=500)


# =========================================权限申请相关API=================================

@csrf_exempt
@require_http_methods(["POST"])
def submit_permission_request(request):
    """提交权限申请 - 双写 MySQL（持久化）+ Redis（通知队列）"""
    try:
        data = json.loads(request.body)

        visitor_name   = data.get('visitor_name', '').strip()
        eid            = data.get('eid', '').strip()
        apply_type     = data.get('apply_type', 'time')
        specific_value = data.get('specific_category', '')
        duration_days  = int(data.get('duration_days') or 1)
        reason         = data.get('reason', '')

        if not visitor_name or not eid:
            return JsonResponse({'success': False, 'message': '缺少必要参数'}, status=400)

        request_id = str(uuid.uuid4())

        # ✅ 写入 MySQL（持久化，重启不丢失）
        perm = PermissionRequest.objects.create(
            request_id    = request_id,
            visitor_name  = visitor_name,
            eid           = eid,
            request_type  = apply_type,
            specific_value= specific_value,
            duration_days = duration_days,
            reason        = reason,
            status        = 'pending',
        )

        # ✅ 同步写 Redis（实时通知，允许失败）
        redis_client = get_redis_client()
        if redis_client:
            request_data = perm.to_dict()
            redis_client.setex(
                f'perm:req:{request_id}',
                7 * 24 * 3600,
                json.dumps(request_data, ensure_ascii=False)
            )
            redis_client.sadd(f'perm:pending:{eid}', request_id)
            managers = Manager.objects.filter(eid=eid, rep='yes')
            for manager in managers:
                notification_key = f'manager_notifications:{manager.name}'
                notification = {
                    'type': 'permission_request',
                    'id': request_id,
                    'data': request_data,
                    'message': f'新的权限申请：{visitor_name}申请访问{eid}的数据'
                }
                redis_client.lpush(notification_key, json.dumps(notification, ensure_ascii=False))

        logger.info(f"权限申请已持久化: request_id={request_id}, visitor={visitor_name}, eid={eid}")

        return JsonResponse({
            'success': True,
            'request_id': request_id,
            'message': '权限申请已提交，请等待管理员审批'
        })

    except Exception as e:
        logger.error(f"提交权限申请失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'提交失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def check_file_exists(request):
    """检查特定日期是否有文件"""
    try:
        eid = request.GET.get('eid')
        date = request.GET.get('date')

        if not eid or not date:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        # 如果您还没有创建FileIndex模型，可以先用warehouse_files表
        # 或者创建一个简单的检查
        from .models import WarehouseFile

        file_exists = WarehouseFile.objects.filter(
            eid=eid,
            upload_date=date
        ).exists()

        return JsonResponse({
            'success': True,
            'exists': file_exists
        })

    except Exception as e:
        logger.error(f"检查文件存在失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def approve_permission_request(request):
    """Manager审批权限申请 - 结果持久化到 MySQL，令牌同步写 Redis"""
    try:
        data = json.loads(request.body)
        request_id   = data.get('request_id')
        decision     = data.get('decision')
        manager_name = data.get('manager_name', '')

        if not request_id or decision not in ('approve', 'reject'):
            return JsonResponse({'success': False, 'message': '缺少必要参数'}, status=400)

        # ✅ 从 MySQL 读取申请记录
        try:
            perm = PermissionRequest.objects.get(request_id=request_id)
        except PermissionRequest.DoesNotExist:
            return JsonResponse({'success': False, 'message': '申请不存在'}, status=404)

        if perm.status != 'pending':
            return JsonResponse({'success': False, 'message': f'该申请已被处理（当前状态: {perm.status}）'}, status=400)

        now = timezone.now()
        access_token = None

        if decision == 'approve':
            access_token = hashlib.md5(
                f"{request_id}_{manager_name}_{now.isoformat()}".encode()
            ).hexdigest()
            expires_at = now + timedelta(days=perm.duration_days)

            perm.status       = 'approved'
            perm.access_token = access_token
            perm.approved_by  = manager_name
            perm.approved_at  = now
            perm.expires_at   = expires_at
            perm.save()

            redis_client = get_redis_client()
            if redis_client:
                token_data = {
                    'visitor_name': perm.visitor_name,
                    'eid':          perm.eid,
                    'access_type':  perm.request_type,
                    'access_value': perm.specific_value,
                    'approved_by':  manager_name,
                    'created_at':   now.isoformat(),
                    'expires_at':   expires_at.isoformat(),
                }
                redis_client.setex(
                    f'access:token:{access_token}',
                    perm.duration_days * 24 * 3600,
                    json.dumps(token_data, ensure_ascii=False)
                )
                redis_client.setex(
                    f'perm:req:{request_id}',
                    7 * 24 * 3600,
                    json.dumps(perm.to_dict(), ensure_ascii=False)
                )
                redis_client.srem(f'perm:pending:{perm.eid}', request_id)

            message = f'权限申请已批准，访问令牌：{access_token}'
        else:
            perm.status      = 'rejected'
            perm.rejected_by = manager_name
            perm.rejected_at = now
            perm.save()

            redis_client = get_redis_client()
            if redis_client:
                redis_client.setex(
                    f'perm:req:{request_id}',
                    7 * 24 * 3600,
                    json.dumps(perm.to_dict(), ensure_ascii=False)
                )
                redis_client.srem(f'perm:pending:{perm.eid}', request_id)

            message = '权限申请已拒绝'

        logger.info(f"审批完成: request_id={request_id}, decision={decision}, manager={manager_name}")

        return JsonResponse({
            'success': True,
            'access_token': access_token,
            'message': message
        })

    except Exception as e:
        logger.error(f"审批权限申请失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'审批失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_warehouses_by_eid(request):
    """根据EID获取仓库列表（供权限申请使用）"""
    try:
        eid = request.GET.get('eid')

        if not eid:
            return JsonResponse({
                'success': False,
                'message': '缺少 EID 参数'
            }, status=400)

        # 获取仓库对象（不是 values）
        warehouses = DeviceWarehouse.objects.filter(eid=eid).order_by('-created_at')

        # 构建包含文件数量的仓库列表
        warehouse_list = []
        for warehouse in warehouses:
            file_count = WarehouseFile.objects.filter(warehouse=warehouse).count()
            warehouse_list.append({
                'id': warehouse.id,
                'name': warehouse.name,
                'file_count': file_count  # 添加文件计数
            })

        logger.info(f"根据EID获取仓库列表: eid={eid}, 数量={len(warehouse_list)}")

        return JsonResponse({
            'success': True,
            'warehouses': warehouse_list,
            'count': len(warehouse_list)
        })

    except Exception as e:
        logger.error(f"获取仓库列表失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取仓库列表失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_permission_requests(request):
    """获取权限申请列表（Manager查看）- 从 MySQL 读取"""
    try:
        eid    = request.GET.get('eid')
        status = request.GET.get('status', 'all')

        if not eid:
            return JsonResponse({'success': False, 'message': '缺少 EID 参数'}, status=400)

        qs = PermissionRequest.objects.filter(eid=eid)
        if status != 'all':
            qs = qs.filter(status=status)

        all_requests = [p.to_dict() for p in qs.order_by('-created_at')]

        stats = {
            'total':    PermissionRequest.objects.filter(eid=eid).count(),
            'pending':  PermissionRequest.objects.filter(eid=eid, status='pending').count(),
            'approved': PermissionRequest.objects.filter(eid=eid, status='approved').count(),
            'rejected': PermissionRequest.objects.filter(eid=eid, status='rejected').count(),
        }

        logger.info(f"获取权限申请列表成功(MySQL): eid={eid}, 总数={len(all_requests)}")

        return JsonResponse({
            'success': True,
            'requests': all_requests,
            'stats': stats,
            'count': len(all_requests)
        })

    except Exception as e:
        logger.error(f"获取权限申请列表失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'获取申请列表失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_my_permission_requests(request):
    """Visitor查询自己的权限申请状态 - 从 MySQL 读取（重启不丢失）"""
    try:
        visitor_name = request.GET.get('visitor_name', '').strip()
        status       = request.GET.get('status', 'all')

        if not visitor_name:
            return JsonResponse({'success': False, 'message': '缺少必要参数：visitor_name'}, status=400)

        qs = PermissionRequest.objects.filter(visitor_name=visitor_name)
        if status != 'all':
            qs = qs.filter(status=status)

        my_requests = [p.to_dict() for p in qs.order_by('-created_at')]

        stats = {
            'total':    PermissionRequest.objects.filter(visitor_name=visitor_name).count(),
            'pending':  PermissionRequest.objects.filter(visitor_name=visitor_name, status='pending').count(),
            'approved': PermissionRequest.objects.filter(visitor_name=visitor_name, status='approved').count(),
            'rejected': PermissionRequest.objects.filter(visitor_name=visitor_name, status='rejected').count(),
        }

        logger.info(
            f"Visitor查询申请成功(MySQL): visitor={visitor_name}, "
            f"总数={stats['total']}, 待审批={stats['pending']}, "
            f"已批准={stats['approved']}, 已拒绝={stats['rejected']}"
        )

        return JsonResponse({
            'success': True,
            'requests': my_requests,
            'stats': stats,
            'count': len(my_requests)
        })

    except Exception as e:
        logger.error(f"查询申请状态失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'查询失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_access_token(request):
    """
    验证Visitor的access_token是否有效
    ✨ 修复：只需要access_token，不需要visitor_name和eid
    """
    try:
        data = json.loads(request.body)
        access_token = data.get('access_token')

        if not access_token:
            return JsonResponse({
                'success': False,
                'message': '请提供访问码'
            }, status=400)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        # 从Redis获取token信息
        token_key = f'access:token:{access_token}'
        token_data = redis_client.get(token_key)

        if not token_data:
            return JsonResponse({
                'success': False,
                'message': 'access_token无效或已过期',
                'valid': False
            }, status=200)

        # 解析token数据
        token_info = json.loads(token_data)

        # Token有效，返回权限信息
        return JsonResponse({
            'success': True,
            'valid': True,
            'message': 'token验证成功',
            'token_info': {
                'visitor_name': token_info.get('visitor_name'),
                'eid': token_info.get('eid'),
                'access_type': token_info.get('access_type'),
                'access_value': token_info.get('access_value'),
                'approved_by': token_info.get('approved_by'),
                'created_at': token_info.get('created_at')
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"验证access_token失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'验证失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_online_status(request):
    """
    获取指定用户的在线状态
    用于前端显示Manager是否在线
    """
    try:
        user_id = request.GET.get('user_id')
        user_type = request.GET.get('user_type')  # 'manager' 或 'visitor'
        eid = request.GET.get('eid')

        if not all([user_id, user_type, eid]):
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        # 检查在线状态
        online_key = f'online:{eid}:{user_type}:{user_id}'
        is_online = redis_client.exists(online_key)

        if is_online:
            user_data = redis_client.get(online_key)
            user_info = json.loads(user_data) if user_data else {}

            return JsonResponse({
                'success': True,
                'online': True,
                'user_info': user_info
            })
        else:
            return JsonResponse({
                'success': True,
                'online': False
            })

    except Exception as e:
        logger.error(f"获取在线状态失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取在线状态失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_all_online_users(request):
    """
    获取指定EID下的所有在线用户
    """
    try:
        eid = request.GET.get('eid')

        if not eid:
            return JsonResponse({
                'success': False,
                'message': '缺少EID参数'
            }, status=400)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        online_users = []
        pattern = f'online:{eid}:*'

        # 扫描所有在线用户
        for key in redis_client.scan_iter(match=pattern):
            user_data = redis_client.get(key)
            if user_data:
                user_info = json.loads(user_data)
                online_users.append(user_info)

        # 按用户类型分组
        managers = [u for u in online_users if u.get('user_type') == 'manager']
        visitors = [u for u in online_users if u.get('user_type') == 'visitor']

        return JsonResponse({
            'success': True,
            'online_users': online_users,
            'managers': managers,
            'visitors': visitors,
            'total': len(online_users)
        })

    except Exception as e:
        logger.error(f"获取在线用户列表失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取在线用户列表失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_available_dates(request):
    """
    获取指定EID下有文件的所有日期列表(供申请时选择)
    """
    try:
        eid = request.GET.get('eid')

        if not eid:
            return JsonResponse({
                'success': False,
                'message': '缺少EID参数'
            }, status=400)

        # 获取该EID下的所有仓库
        warehouses = DeviceWarehouse.objects.filter(eid=eid)

        if not warehouses.exists():
            return JsonResponse({
                'success': True,
                'dates': [],
                'message': f'未找到EID {eid} 对应的仓库'
            })

        # 获取所有文件的upload_date并去重
        dates = WarehouseFile.objects.filter(
            warehouse__in=warehouses
        ).values_list('upload_date', flat=True).distinct().order_by('-upload_date')

        # 转换为字符串列表
        date_list = []
        for date in dates:
            date_list.append({
                'date': date.isoformat(),
                'display': date.strftime('%Y年%m月%d日')
            })

        logger.info(f"获取EID {eid} 的可用日期: {len(date_list)} 个")

        return JsonResponse({
            'success': True,
            'dates': date_list,
            'count': len(date_list)
        })

    except Exception as e:
        logger.error(f"获取可用日期失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'获取日期失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_visitor_authorized_data(request):
    """
    Visitor通过access_token获取授权数据的分析结果
    """
    try:
        access_token = request.GET.get('access_token')
        time_range = request.GET.get('range', '24h')

        if not access_token:
            return JsonResponse({
                'success': False,
                'message': '缺少access_token参数'
            }, status=400)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        # 验证token
        token_key = f'access:token:{access_token}'
        token_data = redis_client.get(token_key)

        if not token_data:
            return JsonResponse({
                'success': False,
                'message': 'access_token无效或已过期',
                'valid': False
            }, status=403)

        token_info = json.loads(token_data)
        eid = token_info.get('eid')
        access_type = token_info.get('access_type')
        access_value = token_info.get('access_value')

        logger.info(
            f"Visitor数据访问: visitor={token_info.get('visitor_name')}, type={access_type}, value={access_value}")

        # 根据授权类型获取文件
        all_violations = []

        if access_type == 'time':
            # 时间类型：获取指定日期的所有文件
            try:
                from datetime import datetime as dt
                date_obj = dt.strptime(access_value, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': '日期格式错误'
                }, status=400)

            warehouses = DeviceWarehouse.objects.filter(eid=eid)
            files = WarehouseFile.objects.filter(
                warehouse__in=warehouses,
                upload_date=date_obj
            )

        elif access_type == 'warehouse':
            # 仓库类型：获取指定仓库的所有文件
            try:
                warehouse_id = int(access_value)
                warehouse = DeviceWarehouse.objects.filter(
                    id=warehouse_id,
                    eid=eid
                ).first()

                if not warehouse:
                    return JsonResponse({
                        'success': False,
                        'message': '仓库不存在或无权访问'
                    }, status=404)

                files = WarehouseFile.objects.filter(warehouse=warehouse)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': '仓库ID格式错误'
                }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'message': '未知的授权类型'
            }, status=400)

        # 处理文件数据
        file_count = 0
        processed_count = 0

        for file_record in files:
            file_count += 1
            try:
                if os.path.exists(file_record.file_path):
                    with open(file_record.file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        processed_count += 1

                        if isinstance(data, list):
                            for item in data:
                                normalized_item = normalize_violation_record_chinese_date(item)
                                if normalized_item:
                                    normalized_item['_eid'] = eid
                                    normalized_item['_file_id'] = file_record.id
                                    all_violations.append(normalized_item)
                        else:
                            normalized_item = normalize_violation_record_chinese_date(data)
                            if normalized_item:
                                normalized_item['_eid'] = eid
                                normalized_item['_file_id'] = file_record.id
                                all_violations.append(normalized_item)
            except Exception as e:
                logger.warning(f"处理文件失败 {file_record.file_path}: {e}")
                continue

        # 基于时间范围筛选
        filtered_violations = filter_violations_by_json_timestamp(all_violations, time_range)

        # 聚合数据
        processed_data = aggregate_violations_data_chinese(filtered_violations, time_range)

        logger.info(
            f"Visitor数据访问完成: {file_count}个文件, "
            f"{len(all_violations)}条原始记录, {len(filtered_violations)}条筛选后记录"
        )

        return JsonResponse({
            'success': True,
            'data': processed_data,
            'visitor_info': {
                'visitor_name': token_info.get('visitor_name'),
                'access_type': access_type,
                'access_value': access_value,
                'approved_by': token_info.get('approved_by')
            },
            'debug_info': {
                'file_count': file_count,
                'processed_file_count': processed_count,
                'raw_records': len(all_violations),
                'filtered_records': len(filtered_violations)
            }
        })

    except Exception as e:
        logger.error(f"Visitor数据访问失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'获取数据失败: {str(e)}'
        }, status=500)


async def visitor_ai_query(request):
    """
    Visitor通过access_token进行AI查询 - 异步版（防止 Daphne kill 长时阻塞请求）
    只能查询授权范围内的数据
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        access_token = data.get('access_token')
        query = data.get('query', '').strip()
        time_range_hours = data.get('time_range_hours', 24)

        if not access_token:
            return JsonResponse({'success': False, 'message': '缺少access_token参数'}, status=400)
        if not query:
            return JsonResponse({'success': False, 'message': '查询内容不能为空'}, status=400)

        # ── 同步部分：token验证 + 数据库查询 + 文件读取 ──
        def _prepare_data():
            redis_client = get_redis_client()
            if not redis_client:
                raise RuntimeError('Redis服务不可用')

            token_data = redis_client.get(f'access:token:{access_token}')
            if not token_data:
                raise PermissionError('access_token无效或已过期')

            token_info  = json.loads(token_data)
            eid         = token_info.get('eid')
            access_type = token_info.get('access_type')
            access_value= token_info.get('access_value')

            if access_type == 'time':
                from datetime import datetime as dt
                date_obj   = dt.strptime(access_value, '%Y-%m-%d').date()
                warehouses = DeviceWarehouse.objects.filter(eid=eid)
                files      = list(WarehouseFile.objects.filter(
                    warehouse__in=warehouses, upload_date=date_obj))
            elif access_type == 'warehouse':
                warehouse_id = int(access_value)
                warehouse    = DeviceWarehouse.objects.filter(id=warehouse_id, eid=eid).first()
                if not warehouse:
                    raise LookupError('仓库不存在或无权访问')
                files = list(WarehouseFile.objects.filter(warehouse=warehouse))
            else:
                raise ValueError('未知的授权类型')

            all_violations = []
            file_count = processed_count = 0
            for file_record in files:
                file_count += 1
                try:
                    if os.path.exists(file_record.file_path):
                        with open(file_record.file_path, 'r', encoding='utf-8') as f:
                            file_data = json.load(f)
                            processed_count += 1
                            items = file_data if isinstance(file_data, list) else [file_data]
                            for item in items:
                                normalized = normalize_violation_record_chinese_date(item)
                                if normalized:
                                    normalized['_eid'] = eid
                                    normalized['_file_id'] = file_record.id
                                    all_violations.append(normalized)
                except Exception as e:
                    logger.warning(f"处理文件失败 {file_record.file_path}: {e}")

            time_range_map = {1: '1h', 24: '24h', 48: '48h', 168: '7d', 720: '30d', 0: 'all'}
            time_range_str = time_range_map.get(int(time_range_hours), '24h')
            filtered = filter_violations_by_json_timestamp(all_violations, time_range_str)

            return token_info, filtered, file_count, processed_count, len(all_violations)

        try:
            token_info, filtered_violations, file_count, processed_count, raw_count =                 await sync_to_async(_prepare_data, thread_sensitive=True)()
        except PermissionError as e:
            return JsonResponse({'success': False, 'message': str(e), 'valid': False}, status=403)
        except (LookupError, ValueError, RuntimeError) as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

        logger.info(
            f"Visitor AI查询: visitor={token_info.get('visitor_name')}, "
            f"query={query}, records={len(filtered_violations)}"
        )

        # ── 异步部分：调用 Janus（耗时最长） ──
        def _run_ai():
            processor = AIQueryProcessor()
            return processor.process_natural_language_query_with_data(
                query=query,
                violations_data=filtered_violations,
                time_range_hours=int(time_range_hours)
            )

        analysis_result = await sync_to_async(_run_ai, thread_sensitive=False)()

        analysis_result['visitor_info'] = {
            'visitor_name': token_info.get('visitor_name'),
            'access_type':  token_info.get('access_type'),
            'access_value': token_info.get('access_value'),
            'approved_by':  token_info.get('approved_by'),
        }
        analysis_result['debug_info'] = {
            'file_count':          file_count,
            'processed_file_count':processed_count,
            'raw_records':         raw_count,
            'filtered_records':    len(filtered_violations),
        }

        logger.info(f"Visitor AI查询完成: {file_count}个文件, {len(filtered_violations)}条记录")
        return JsonResponse(analysis_result)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '请求数据格式错误'}, status=400)
    except Exception as e:
        logger.error(f"Visitor AI查询失败: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'AI查询失败: {str(e)}'}, status=500)


# csrf_exempt 直接设属性，避免装饰器把 async def 包成同步 wrapper
visitor_ai_query.csrf_exempt = True


@csrf_exempt
@require_http_methods(["POST"])
def admin_generate_token(request):
    """
    Admin直接生成访问令牌
    无需审批流程,直接创建可用的访问令牌
    """
    try:
        data = json.loads(request.body)
        eid = data.get('eid', '').strip()
        access_type = data.get('access_type')  # 'time' or 'warehouse'
        access_value = data.get('access_value')
        duration_days = data.get('duration_days', 1)

        # 参数验证
        if not all([eid, access_type, access_value, duration_days]):
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        # 验证访问类型
        if access_type not in ['time', 'warehouse']:
            return JsonResponse({
                'success': False,
                'message': '无效的访问类型,必须是 time 或 warehouse'
            }, status=400)

        # 验证访问值
        if access_type == 'time':
            # 验证日期格式
            try:
                from datetime import datetime as dt
                dt.strptime(access_value, '%Y-%m-%d')
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': '日期格式错误,应为 YYYY-MM-DD'
                }, status=400)
        elif access_type == 'warehouse':
            # 验证仓库是否存在
            try:
                warehouse_id = int(access_value)
                warehouse = DeviceWarehouse.objects.filter(
                    id=warehouse_id,
                    eid=eid
                ).first()

                if not warehouse:
                    return JsonResponse({
                        'success': False,
                        'message': '指定的仓库不存在或不属于该EID'
                    }, status=404)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': '仓库ID格式错误'
                }, status=400)

        # 连接Redis
        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        # 生成访问令牌
        token_string = f"admin_{eid}_{access_type}_{access_value}_{datetime.now().isoformat()}_{uuid.uuid4().hex}"
        access_token = hashlib.md5(token_string.encode()).hexdigest()

        # 构建令牌数据
        token_data = {
            'access_token': access_token,
            'visitor_name': 'ADMIN_GENERATED',  # 标记为管理员生成
            'eid': eid,
            'access_type': access_type,
            'access_value': access_value,
            'duration_days': int(duration_days),
            'approved_by': 'ADMIN',
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=int(duration_days))).isoformat(),
            'generated_by_admin': True  # 特殊标记
        }

        # 保存到Redis
        token_key = f'access:token:{access_token}'
        redis_client.setex(
            token_key,
            int(duration_days) * 24 * 3600,
            json.dumps(token_data, ensure_ascii=False)
        )

        # 同时保存到令牌列表(用于管理)
        admin_tokens_key = f'admin:tokens:{eid}'
        redis_client.sadd(admin_tokens_key, access_token)
        # 设置列表的过期时间(比最长的令牌多一点)
        redis_client.expire(admin_tokens_key, (int(duration_days) + 1) * 24 * 3600)

        logger.info(
            f"Admin生成访问令牌成功: eid={eid}, type={access_type}, "
            f"value={access_value}, duration={duration_days}天"
        )

        return JsonResponse({
            'success': True,
            'message': '访问令牌生成成功',
            'token_info': token_data
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"Admin生成令牌失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'生成令牌失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def admin_list_tokens(request):
    """
    获取所有Admin生成的令牌列表
    包括有效和已过期的令牌
    """
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        all_tokens = []

        # 扫描所有的访问令牌
        for key in redis_client.scan_iter(match='access:token:*'):
            try:
                token_data_str = redis_client.get(key)
                if token_data_str:
                    token_data = json.loads(token_data_str)

                    # 只返回Admin生成的令牌
                    if token_data.get('generated_by_admin') or token_data.get('approved_by') == 'ADMIN':
                        all_tokens.append(token_data)
            except Exception as e:
                logger.warning(f"解析令牌数据失败: {key}, 错误: {e}")
                continue

        # 按创建时间排序(最新的在前)
        all_tokens.sort(
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )

        # 统计信息
        now = datetime.now()
        stats = {
            'total': len(all_tokens),
            'active': sum(1 for t in all_tokens if datetime.fromisoformat(t.get('expires_at', '')) > now),
            'expired': sum(1 for t in all_tokens if datetime.fromisoformat(t.get('expires_at', '')) <= now),
            'time_type': sum(1 for t in all_tokens if t.get('access_type') == 'time'),
            'warehouse_type': sum(1 for t in all_tokens if t.get('access_type') == 'warehouse')
        }

        logger.info(f"Admin令牌列表查询成功: 总数={len(all_tokens)}")

        return JsonResponse({
            'success': True,
            'tokens': all_tokens,
            'stats': stats,
            'count': len(all_tokens)
        })

    except Exception as e:
        logger.error(f"获取Admin令牌列表失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'获取令牌列表失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def admin_delete_token(request):
    """
    删除指定的访问令牌
    """
    try:
        data = json.loads(request.body)
        access_token = data.get('access_token')

        if not access_token:
            return JsonResponse({
                'success': False,
                'message': '缺少访问令牌参数'
            }, status=400)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        # 删除令牌
        token_key = f'access:token:{access_token}'
        deleted = redis_client.delete(token_key)

        if deleted:
            logger.info(f"Admin删除令牌成功: {access_token}")
            return JsonResponse({
                'success': True,
                'message': '令牌已删除'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '令牌不存在或已被删除'
            }, status=404)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"删除令牌失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'删除令牌失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def admin_revoke_token(request):
    """
    撤销令牌(标记为无效但保留记录)
    """
    try:
        data = json.loads(request.body)
        access_token = data.get('access_token')

        if not access_token:
            return JsonResponse({
                'success': False,
                'message': '缺少访问令牌参数'
            }, status=400)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        token_key = f'access:token:{access_token}'
        token_data_str = redis_client.get(token_key)

        if not token_data_str:
            return JsonResponse({
                'success': False,
                'message': '令牌不存在'
            }, status=404)

        token_data = json.loads(token_data_str)

        # 标记为已撤销
        token_data['revoked'] = True
        token_data['revoked_at'] = datetime.now().isoformat()

        # 更新Redis中的数据(保持原有的TTL)
        ttl = redis_client.ttl(token_key)
        if ttl > 0:
            redis_client.setex(
                token_key,
                ttl,
                json.dumps(token_data, ensure_ascii=False)
            )

        logger.info(f"Admin撤销令牌成功: {access_token}")

        return JsonResponse({
            'success': True,
            'message': '令牌已撤销'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"撤销令牌失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'撤销令牌失败: {str(e)}'
        }, status=500)


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
