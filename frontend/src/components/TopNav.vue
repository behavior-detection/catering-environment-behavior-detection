<template>
  <nav>
    <!--
    <img src="/logo.png" alt="Logo" />
    -->
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
  padding: 10px;
  border-bottom: 7px solid #e6f4ff;
  box-shadow: 0 6px 5px -5px #e6f4ff; /* 向下扩展的阴影，颜色同边框 */
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
  color: #1890FF; /* 蓝色 */
  text-decoration: underline;
  text-underline-offset: 10px; /* 控制下划线距离文字的距离，值越大越远 */
}
</style>
