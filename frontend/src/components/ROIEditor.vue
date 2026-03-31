<template>
  <div class="roi-editor" ref="container">
    <div class="canvas-wrapper">
      <img 
        ref="imageRef" 
        :src="snapshotUrl" 
        class="background-image" 
        @load="onImageLoad" 
        draggable="false"
      />
      <canvas
        ref="canvas"
        @click="handleClick"
        @mousemove="handleMouseMove"
        @contextmenu.prevent="cancelOrFinish"
      ></canvas>
    </div>
    
    <div class="editor-ui-layer">
      <div v-if="!snapshotUrl" class="loading-badge">
        <i class="fas fa-spinner fa-spin"></i> 等待快照...
      </div>
      
      <div v-else class="controls-bar">
        <div class="instruction">
          {{ instructionText }}
        </div>
        
        <button 
          v-if="isClosed && currentPoints.length > 0" 
          @click="confirmSave" 
          class="save-btn"
        >
          <i class="fas fa-save"></i> 确认保存 ROI
        </button>
        
        <button 
          v-if="currentPoints.length > 0" 
          @click="resetDrawing" 
          class="reset-btn"
        >
          <i class="fas fa-undo"></i> 重绘
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ROIEditor',
  props: {
    snapshotUrl: String,
    modelValue: { type: Array, default: () => [] }
  },
  emits: ['update:modelValue', 'change', 'roi-saved'],
  data() {
    return {
      currentPoints: [], // 当前绘制的点集
      isClosed: false,   // 是否已闭合
      mousePos: null,    // 鼠标实时位置
      hoverStart: false, // 鼠标是否悬停在起点（用于闭合提示）
      canvasContext: null,
      imgMetrics: { scale: 1, offsetX: 0, offsetY: 0, naturalW: 1920, naturalH: 1080 }
    }
  },
  computed: {
    instructionText() {
      if (this.isClosed) return "形状已闭合，请点击保存按钮";
      if (this.currentPoints.length === 0) return "点击画面开始绘制 ROI 区域";
      if (this.currentPoints.length < 3) return "继续点击添加点 (至少3个点)";
      return "点击起点闭合形状，或右键完成";
    }
  },
  watch: {
    snapshotUrl() {
      this.resetDrawing(); // 新图片，重置
    },
    // 如果父组件传入了已保存的数据，回显出来
    modelValue: {
      handler(val) {
        if (val && val.length > 0 && this.currentPoints.length === 0) {
           // 只有当本地没在画的时候才回显，避免冲突
           // 这里仅作展示，不进入编辑状态
           this.redraw();
        }
      },
      deep: true
    }
  },
  mounted() {
    window.addEventListener('resize', this.handleResize);
    setTimeout(() => this.initCanvas(), 100);
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize);
  },
  methods: {
    initCanvas() {
      const canvas = this.$refs.canvas;
      const container = this.$refs.container;
      if (!canvas || !container) return;
      
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
      this.canvasContext = canvas.getContext('2d');
      if (this.$refs.imageRef?.complete) {
        this.updateImageMetrics();
        this.redraw();
      }
    },
    onImageLoad() {
      this.updateImageMetrics();
      this.redraw();
    },
    handleResize() {
      this.initCanvas();
      this.updateImageMetrics();
      this.redraw();
    },
    updateImageMetrics() {
      const img = this.$refs.imageRef;
      const container = this.$refs.container;
      if (!img || !container) return;
      const contW = container.clientWidth;
      const contH = container.clientHeight;
      const natW = img.naturalWidth || 1920;
      const natH = img.naturalHeight || 1080;
      this.imgMetrics.naturalW = natW;
      this.imgMetrics.naturalH = natH;
      const contRatio = contW / contH;
      const imgRatio = natW / natH;
      if (contRatio > imgRatio) {
        this.imgMetrics.renderH = contH;
        this.imgMetrics.renderW = contH * imgRatio;
        this.imgMetrics.scale = contH / natH;
        this.imgMetrics.offsetX = (contW - this.imgMetrics.renderW) / 2;
        this.imgMetrics.offsetY = 0;
      } else {
        this.imgMetrics.renderW = contW;
        this.imgMetrics.renderH = contW / imgRatio;
        this.imgMetrics.scale = contW / natW;
        this.imgMetrics.offsetX = 0;
        this.imgMetrics.offsetY = (contH - this.imgMetrics.renderH) / 2;
      }
    },
    
    // 坐标转换
    getRealPos(clientX, clientY) {
      const canvas = this.$refs.canvas;
      const rect = canvas.getBoundingClientRect();
      const canvasX = (clientX - rect.left) * (canvas.width / rect.width);
      const canvasY = (clientY - rect.top) * (canvas.height / rect.height);
      let realX = (canvasX - this.imgMetrics.offsetX) / this.imgMetrics.scale;
      let realY = (canvasY - this.imgMetrics.offsetY) / this.imgMetrics.scale;
      realX = Math.max(0, Math.min(realX, this.imgMetrics.naturalW));
      realY = Math.max(0, Math.min(realY, this.imgMetrics.naturalH));
      return { x: Math.round(realX), y: Math.round(realY) };
    },
    toCanvasPos(realX, realY) {
      return {
        x: (realX * this.imgMetrics.scale) + this.imgMetrics.offsetX,
        y: (realY * this.imgMetrics.scale) + this.imgMetrics.offsetY
      };
    },

    // === 交互逻辑 ===

    handleClick(e) {
      if (this.isClosed) return; // 已闭合，禁止加点

      const pos = this.getRealPos(e.clientX, e.clientY);
      
      // 1. 检查是否点击了起点（闭合操作）
      if (this.currentPoints.length >= 3 && this.isNearStart(pos)) {
        this.finishPath();
        return;
      }

      // 2. 添加新点
      this.currentPoints.push([pos.x, pos.y]);
      this.redraw();
    },

    handleMouseMove(e) {
      if (this.isClosed) return;
      const pos = this.getRealPos(e.clientX, e.clientY);
      this.mousePos = pos;
      
      // 检查是否靠近起点
      this.hoverStart = (this.currentPoints.length >= 3 && this.isNearStart(pos));
      
      this.redraw();
    },

    cancelOrFinish(e) {
      // 右键：如果点够多就闭合，否则取消
      if (this.currentPoints.length >= 3) {
        this.finishPath();
      } else {
        this.resetDrawing();
      }
    },

    isNearStart(currentRealPos) {
      if (this.currentPoints.length === 0) return false;
      const startReal = this.currentPoints[0];
      // 转换回屏幕像素计算距离，这样体验更一致
      const p1 = this.toCanvasPos(currentRealPos.x, currentRealPos.y);
      const p2 = this.toCanvasPos(startReal[0], startReal[1]);
      const dist = Math.sqrt(Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2));
      return dist < 15; // 15像素吸附半径
    },

    finishPath() {
      this.isClosed = true;
      this.mousePos = null;
      this.hoverStart = false;
      this.redraw();
      // 这里不自动保存，等待用户点击保存按钮
    },

    resetDrawing() {
      this.currentPoints = [];
      this.isClosed = false;
      this.mousePos = null;
      this.redraw();
      // 通知父组件清空
      this.$emit('update:modelValue', []);
      this.$emit('change', []);
    },

    confirmSave() {
      if (!this.isClosed || this.currentPoints.length < 3) return;
      
      // [修复] 增加对图片尺寸的防御性检查
      const w = this.imgMetrics.naturalW || 1920;
      const h = this.imgMetrics.naturalH || 1080;

      const normalizedPoints = this.currentPoints.map(p => {
          // 确保精度，保留4位小数
          let x = Number((p[0] / w).toFixed(4));
          let y = Number((p[1] / h).toFixed(4));
          
          // 严格限制在 0-1 之间
          return [
              Math.max(0, Math.min(1, x)),
              Math.max(0, Math.min(1, y))
          ];
      });

      const polyData = [{
        name: `ROI-${Date.now()}`,
        points: JSON.parse(JSON.stringify(this.currentPoints)), 
        normalizedPoints: normalizedPoints, 
        active: true
      }];

      this.$emit('update:modelValue', polyData);
      this.$emit('change', polyData);
      this.$emit('roi-saved', polyData[0]); 
    },

    redraw() {
      const ctx = this.canvasContext;
      const canvas = this.$refs.canvas;
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // --- 绘制已保存的数据 (父组件传入的) ---
      // 如果我们正在画，就不画已保存的，避免重叠干扰
      if (this.currentPoints.length === 0 && this.modelValue.length > 0) {
        this.modelValue.forEach(poly => this.drawPolygon(ctx, poly.points, '#00FF00', false));
        return;
      }

      // --- 绘制当前正在画的数据 ---
      if (this.currentPoints.length > 0) {
        // 画线和填充
        this.drawPolygon(ctx, this.currentPoints, this.isClosed ? '#00FF00' : '#FFFF00', !this.isClosed);
        
        // 画点
        this.currentPoints.forEach((p, index) => {
          const pt = this.toCanvasPos(p[0], p[1]);
          ctx.beginPath();
          // 起点特殊显示
          if (index === 0) {
            ctx.fillStyle = this.hoverStart ? '#FF0000' : '#00FF00'; // 吸附时变红
            ctx.arc(pt.x, pt.y, 6, 0, Math.PI * 2); // 起点大一点
          } else {
            ctx.fillStyle = '#FFFF00';
            ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2);
          }
          ctx.fill();
        });

        // 画跟随鼠标的橡皮筋线
        if (!this.isClosed && this.mousePos && this.currentPoints.length > 0) {
          const last = this.currentPoints[this.currentPoints.length - 1];
          const p1 = this.toCanvasPos(last[0], last[1]);
          const p2 = this.toCanvasPos(this.mousePos.x, this.mousePos.y);
          
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = '#FFFF00';
          ctx.setLineDash([5, 5]); // 虚线
          ctx.stroke();
          ctx.setLineDash([]);
        }
      }
    },

    drawPolygon(ctx, points, color, isOpen) {
        if (!points || points.length < 2) return;
        ctx.beginPath();
        const start = this.toCanvasPos(points[0][0], points[0][1]);
        ctx.moveTo(start.x, start.y);
        for (let i = 1; i < points.length; i++) {
          const p = this.toCanvasPos(points[i][0], points[i][1]);
          ctx.lineTo(p.x, p.y);
        }
        if (!isOpen) ctx.closePath();
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();
        
        if (!isOpen) {
            ctx.fillStyle = color === '#00FF00' ? 'rgba(0, 255, 0, 0.2)' : 'rgba(255, 255, 0, 0.2)';
            ctx.fill();
        }
    }
  }
}
</script>

<style scoped>
.roi-editor { position: relative; width: 100%; height: 100%; background: #111; user-select: none; }
.canvas-wrapper { position: relative; width: 100%; height: 100%; }
.background-image { width: 100%; height: 100%; object-fit: contain; display: block; }
canvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; cursor: crosshair; }

.editor-ui-layer {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;
}
.loading-badge {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  background: rgba(0,0,0,0.7); color: white; padding: 10px 20px; border-radius: 6px;
}
.controls-bar {
  position: absolute; top: 10px; left: 10px; right: 10px;
  display: flex; gap: 10px; align-items: center; pointer-events: auto;
}
.instruction {
  background: rgba(0, 0, 0, 0.6); color: #fff; padding: 6px 12px; border-radius: 4px; font-size: 14px;
}
.save-btn {
  background: #28a745; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer;
}
.save-btn:hover { background: #218838; }
.reset-btn {
  background: #dc3545; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer;
}
.reset-btn:hover { background: #c82333; }
</style>