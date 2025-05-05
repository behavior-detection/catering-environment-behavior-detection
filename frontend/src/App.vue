<template>
  <div id="app">
    <nav class="navbar is-dark" role="navigation" aria-label="main navigation">
      <div class="navbar-brand">
        <router-link class="navbar-item" to="/">
          <strong>YOLO Detection System</strong>
        </router-link>

        <a role="button" class="navbar-burger" aria-label="menu" aria-expanded="false"
           :class="{ 'is-active': isMenuActive }" @click="toggleMenu">
          <span aria-hidden="true"></span>
          <span aria-hidden="true"></span>
          <span aria-hidden="true"></span>
        </a>
      </div>

      <div class="navbar-menu" :class="{ 'is-active': isMenuActive }">
        <div class="navbar-start">
          <router-link class="navbar-item" to="/">
            Dashboard
          </router-link>

          <router-link class="navbar-item" to="/settings">
            Settings
          </router-link>

          <router-link class="navbar-item" to="/history">
            Violation History
          </router-link>
        </div>
      </div>
    </nav>

    <section class="section">
      <div class="container is-fluid">
        <router-view />
      </div>
    </section>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      isMenuActive: false
    }
  },
  methods: {
    toggleMenu() {
      this.isMenuActive = !this.isMenuActive
    }
  }
}
</script>

<style>
@import "https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css";

html, body {
  height: 100%;
  margin: 0;
  background-color: #f5f5f5;
}

#app {
  font-family: 'Avenir', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.section {
  flex: 1;
}

.card {
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 3px rgba(10, 10, 10, 0.1), 0 0 0 1px rgba(10, 10, 10, 0.1);
}

.card-header {
  box-shadow: 0 1px 2px rgba(10, 10, 10, 0.1);
}

.card-content {
  padding: 1.5rem;
}

.video-container {
  position: relative;
  height: 0;
  overflow: hidden;
  padding-bottom: 56.25%; /* 16:9 ratio */
}

.video-container img,
.video-container canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background-color: #000;
}

.canvas-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.status-indicator {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 5px;
}

.status-active {
  background-color: #48c774;
}

.status-inactive {
  background-color: #f14668;
}

.status-warning {
  background-color: #ffdd57;
}

.violation-panel {
  max-height: 600px;
  overflow-y: auto;
}

.violation-card {
  margin-bottom: 1rem;
  border-radius: 5px;
  transition: transform 0.2s;
}

.violation-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.snapshot-container {
  position: relative;
  cursor: pointer;
}

.snapshot-container img {
  width: 100%;
  border-radius: 4px;
}

.snapshot-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  border-radius: 4px;
}

.snapshot-container:hover .snapshot-overlay {
  opacity: 1;
}
</style>
