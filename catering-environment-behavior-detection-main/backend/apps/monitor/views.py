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
import requests
import logging
import time
import os
import re
import uuid
from django.conf import settings
import redis
import hashlib
from asgiref.sync import sync_to_async

from .models import DeviceWarehouse, WarehouseFile, ViolationRecord, AIAnalysisReport, AIQueryHistory, SystemConfig, PermissionRequest
from .services import JanusAIService, ViolationAnalyzer, SystemMonitor, ViolationDataProcessor, AIQueryProcessor
from apps.login.api.models import Manager, Visitor

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

def violations_dashboard(request):
    """违规数据监控仪表板页面"""
    return render(request, 'monitor/violations_dashboard.html')


@csrf_exempt
@require_http_methods(["GET"])
def violations_analytics(request):
    """获取违规数据分析 API - 修复版本"""
    try:
        # 获取查询参数
        time_range = request.GET.get('range', '24h')
        query_all = request.GET.get('all', 'false').lower() == 'true'

        logger.info(f"违规数据分析请求: range={time_range}, query_all={query_all}")

        # 确定时间范围
        hours = 0 if query_all else parse_time_range(time_range)

        # 获取违规记录
        records = list(ViolationRecord.get_violations_by_time_range(hours))

        # 构建响应数据
        response_data = build_analytics_response(records, time_range, query_all)

        logger.info(f"违规数据分析完成: {len(records)} 条记录")

        return JsonResponse({
            'success': True,
            'data': response_data,
            'debug_info': {
                'records_count': len(records),
                'time_range': time_range,
                'hours': hours,
                'query_all': query_all
            }
        })

    except Exception as e:
        logger.error(f"违规数据分析失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'分析失败: {str(e)}',
            'error_details': str(e)
        }, status=500)


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
    """解析中文日期时间格式：2025年08月07日星期四16:23:15"""
    try:
        if not timestamp_str:
            return None

        # 处理中文日期格式
        # 格式：2025年08月07日星期四16:23:15
        # 使用正则表达式提取日期时间部分
        pattern = r'(\d{4})年(\d{2})月(\d{2})日[^0-9]*(\d{2}):(\d{2}):(\d{2})'
        match = re.match(pattern, timestamp_str.strip())

        if match:
            year, month, day, hour, minute, second = match.groups()

            # 构建datetime对象
            dt = datetime(
                year=int(year),
                month=int(month),
                day=int(day),
                hour=int(hour),
                minute=int(minute),
                second=int(second),
                tzinfo=timezone.utc  # 设置为UTC时区
            )

            return dt.isoformat()
        else:
            logger.warning(f"中文日期格式不匹配: {timestamp_str}")
            return None

    except Exception as e:
        logger.error(f"中文日期解析失败: {e}, timestamp: {timestamp_str}")
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
def violations_list(request):
    """违规记录列表"""
    return JsonResponse({'success': True, 'message': '功能待实现'})


@csrf_exempt
def violations_stats(request):
    """违规统计"""
    return JsonResponse({'success': True, 'message': '功能待实现'})


@csrf_exempt
def clear_violations(request):
    """清空违规记录"""
    return JsonResponse({'success': True, 'message': '功能待实现'})


@csrf_exempt
def batch_upload_violations(request):
    """批量上传违规数据"""
    return JsonResponse({'success': True, 'message': '功能待实现'})


@csrf_exempt
def export_violations_data(request):
    """导出违规数据"""
    return JsonResponse({'success': True, 'message': '功能待实现'})


@csrf_exempt
def get_violation_trends(request):
    """获取违规趋势"""
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
def get_files_by_date(request):
    """
    根据日期获取文件列表(供visitor使用access_token访问)
    """
    try:
        access_token = request.GET.get('access_token')

        if not access_token:
            return JsonResponse({
                'success': False,
                'message': '缺少access_token参数'
            }, status=400)

        # 验证token
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

        # 检查权限类型必须是time
        if token_info.get('access_type') != 'time':
            return JsonResponse({
                'success': False,
                'message': '此token不是时间类型权限'
            }, status=403)

        # 获取授权的日期
        target_date = token_info.get('access_value')  # 格式: YYYY-MM-DD
        eid = token_info.get('eid')

        if not target_date or not eid:
            return JsonResponse({
                'success': False,
                'message': 'token信息不完整'
            }, status=400)

        # 查询该日期的文件
        try:
            from datetime import datetime as dt
            date_obj = dt.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': '日期格式错误'
            }, status=400)

        # 获取该EID下该日期的所有文件
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
            file_list.append({
                'id': file_record.id,
                'file_name': file_record.file_name,
                'file_path': file_record.file_path,
                'upload_date': file_record.upload_date.isoformat(),
                'file_size': file_record.file_size,
                'warehouse_name': file_record.warehouse.name,
                'warehouse_id': file_record.warehouse.id,
                'created_at': file_record.created_at.isoformat()
            })

        logger.info(
            f"Visitor通过token访问日期文件: "
            f"visitor={token_info.get('visitor_name')}, "
            f"date={target_date}, files={len(file_list)}"
        )

        return JsonResponse({
            'success': True,
            'files': file_list,
            'count': len(file_list),
            'date': target_date,
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