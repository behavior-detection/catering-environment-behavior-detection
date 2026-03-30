<template>
  <nav>
    <div class="brand-title">餐饮环境行为检测管理系统</div>
    <div class="nav-items">
      <router-link to="/" exact-active-class="active-link">首页</router-link>
      <router-link to="/page2" active-class="active-link">我的设备</router-link>
      <router-link to="/page3" active-class="active-link">账号管理</router-link>   
    </div>
  </nav>
</template>



<script>
export default {
  name: 'TopNav'
}
</script>

<style scoped>
nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  border-bottom: 7px solid #e6f4ff;
  box-shadow: 0 6px 5px -5px #e6f4ff;
  flex-shrink: 0;
  background-color: #fff;
  z-index: 100;
}
.brand-title {
  font-size: 18px;
  font-weight: 600;
  color: #1890FF;
  letter-spacing: 2px;
  white-space: nowrap;
  font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", sans-serif;
}
a {
  margin-right: 20px;
  text-decoration: none;
  color: rgba(0, 0, 0, 0.65);
  font-weight: 500;
  padding-bottom: 5px;
}
.nav-items {
  display: flex;
  margin-left: auto;
  justify-content: flex-end;
}

/* 当前激活链接样式 */
.active-link {
  color: #1890FF;
  text-decoration: underline;
  text-underline-offset: 10px;
}

@media (max-width: 1024px) {
  .brand-title {
    font-size: 15px;
    letter-spacing: 1px;
  }

  a {
    margin-right: 14px;
    font-size: 14px;
  }
}

@media (max-width: 768px) {
  nav {
    padding: 8px 12px;
  }

  .brand-title {
    font-size: 13px;
    letter-spacing: 0.5px;
  }

  .nav-items {
    gap: 4px;
  }

  a {
    margin-right: 8px;
    font-size: 13px;
  }
}

@media (max-width: 480px) {
  .brand-title {
    font-size: 12px;
    letter-spacing: 0;
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  a {
    margin-right: 6px;
    font-size: 12px;
  }
}
</style>
