// NavLockManager.js - 全局导航锁定管理器
import { ElMessage } from 'element-plus'
export class NavLockManager {
  constructor() {
    this.lockedElements = new Map();
    this.isInitialized = false;
  }

  // 初始化管理器
  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    // 监听路由变化
    window.addEventListener('popstate', () => this.updateLocksByRoute());

    // 监听存储变化（跨标签页同步）
    window.addEventListener('storage', (e) => {
      if (e.key === 'userInfo' || e.key === 'adminInfo') {
        this.updateLocksByRoute();
      }
    });
  }

  // 根据当前路由和登录状态更新锁定
  updateLocksByRoute() {
    const currentPath = window.location.pathname;
    const isLoggedIn = sessionStorage.getItem('userInfo') || sessionStorage.getItem('adminInfo');

    if (currentPath === '/' || currentPath.includes('Page1')) {
      // 登录页面：锁定"我的设备"和"账号管理"
      this.unlockButtons(['首页', 'home']);
      this.lockButtons(['设备', '账号管理', 'account', 'device', '我的设备']);
    } else if (isLoggedIn && (currentPath.includes('Page2') || currentPath.includes('Page3'))) {
      // 已登录的功能页面：锁定"首页"，解锁其他
      this.unlockButtons(['设备', '账号管理', 'account', 'device', '我的设备']);
      this.lockButtons(['首页', 'home', '返回首页']);
    }
  }

  // 锁定指定关键词的按钮
  lockButtons(keywords) {
    const allNavLinks = document.querySelectorAll('a, button, .nav-link, .nav-item, [role="button"]');

    allNavLinks.forEach(element => {
      const text = (element.textContent || element.innerText || '').toLowerCase();

      // 检查是否包含任何关键词
      const shouldLock = keywords.some(keyword => text.includes(keyword.toLowerCase()));

      if (shouldLock && !this.lockedElements.has(element)) {
        this.lockElement(element);
      }
    });
  }

  // 解锁指定关键词的按钮
  unlockButtons(keywords) {
    this.lockedElements.forEach((lockInfo, element) => {
      const text = (element.textContent || element.innerText || '').toLowerCase();

      // 检查是否包含任何关键词
      const shouldUnlock = keywords.some(keyword => text.includes(keyword.toLowerCase()));

      if (shouldUnlock) {
        this.unlockElement(element);
      }
    });
  }

  // 锁定单个元素
  lockElement(element) {
    if (this.lockedElements.has(element)) return;

    // 保存原始状态
    const originalState = {
      pointerEvents: element.style.pointerEvents,
      opacity: element.style.opacity,
      color: element.style.color,
      cursor: element.style.cursor,
      textDecoration: element.style.textDecoration,
      backgroundColor: element.style.backgroundColor,
      transform: element.style.transform,
      boxShadow: element.style.boxShadow
    };

    // 创建阻止事件处理器
    const blockEvent = (e) => {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();

      // 根据当前页面显示不同提示
      const currentPath = window.location.pathname;
      if (currentPath === '/' || currentPath.includes('Page1')) {
        ElMessage.warning('请先完成登录才能使用此功能！');
      } else {
        ElMessage.warning('请先退出登录才能返回首页！');
      }
      return false;
    };

    // 保存锁定信息
    this.lockedElements.set(element, {
      originalState,
      blockEvent,
      lockTime: Date.now()
    });

    // 应用锁定样式
    element.style.setProperty('pointer-events', 'none', 'important');
    element.style.setProperty('opacity', '0.4', 'important');
    element.style.setProperty('color', '#ccc', 'important');
    element.style.setProperty('cursor', 'not-allowed', 'important');
    element.style.setProperty('text-decoration', 'none', 'important');
    element.style.setProperty('background-color', 'transparent', 'important');
    element.style.setProperty('transform', 'none', 'important');
    element.style.setProperty('box-shadow', 'none', 'important');

    // 添加事件监听器
    element.addEventListener('click', blockEvent, true);
    element.addEventListener('mousedown', blockEvent, true);
    element.addEventListener('mouseup', blockEvent, true);
    element.addEventListener('touchstart', blockEvent, true);
    element.addEventListener('touchend', blockEvent, true);

    // 添加锁定标记
    element.classList.add('nav-locked-element');

    // 已移除锁定图标的添加代码
  }

  // 解锁单个元素
  unlockElement(element) {
    const lockInfo = this.lockedElements.get(element);
    if (!lockInfo) return;

    const { originalState, blockEvent } = lockInfo;

    // 恢复原始样式
    Object.keys(originalState).forEach(prop => {
      element.style[prop] = originalState[prop] || '';
    });

    // 移除事件监听器
    element.removeEventListener('click', blockEvent, true);
    element.removeEventListener('mousedown', blockEvent, true);
    element.removeEventListener('mouseup', blockEvent, true);
    element.removeEventListener('touchstart', blockEvent, true);
    element.removeEventListener('touchend', blockEvent, true);

    // 移除锁定标记
    element.classList.remove('nav-locked-element');

    // 已移除锁定图标的移除代码

    // 从Map中删除
    this.lockedElements.delete(element);
  }

  // 清理所有锁定
  clearAllLocks() {
    this.lockedElements.forEach((_, element) => {
      this.unlockElement(element);
    });
  }

  // 销毁管理器
  destroy() {
    this.clearAllLocks();
    window.removeEventListener('popstate', () => this.updateLocksByRoute());
    window.removeEventListener('storage', () => this.updateLocksByRoute());
    this.isInitialized = false;
  }
}

// 创建单例实例
export const navLockManager = new NavLockManager();

// 自动初始化
if (typeof window !== 'undefined') {
  navLockManager.init();
}