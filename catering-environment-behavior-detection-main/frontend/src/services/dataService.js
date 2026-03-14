// services/dataService.js
export class DataService {
  constructor() {
    this.baseURL = '/api/monitor';
  }

  // 统一的数据获取方法
  async getViolationsData(options = {}) {
    const params = new URLSearchParams({
      eid: options.eid || '',
      range: options.timeRange || '24h',
      source: options.source || 'both'
    });

    const response = await fetch(`${this.baseURL}/violations/unified/?${params}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  }

  // 获取仓库列表
  async getWarehouses(eid) {
    const params = new URLSearchParams({ eid: eid || '' });

    const response = await fetch(`${this.baseURL}/warehouses/?${params}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    return await response.json();
  }

  // 获取仓库文件
  async getWarehouseFiles(warehouseId, eid) {
    const params = new URLSearchParams({ eid: eid || '' });

    const response = await fetch(`${this.baseURL}/warehouses/${warehouseId}/files/?${params}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    return await response.json();
  }
}

export const dataService = new DataService();