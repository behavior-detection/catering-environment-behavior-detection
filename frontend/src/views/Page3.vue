<template>
  <div class="page3">
    <FeedbackReport />
  </div>
</template>

<script>
import FeedbackReport from '../components/FeedbackReport.vue'

export default {
  name: 'Page3',
  components: {
    FeedbackReport
  }
}
</script>

<style scoped>
.page3 {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  background: #f5f7fa;
}
</style>