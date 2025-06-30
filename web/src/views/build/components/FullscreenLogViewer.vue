<template>
  <div class="fullscreen-log-viewer">
    <div
      class="fullscreen-log-container"
      :class="{ 'fullscreen-mode': isFullscreen }"
    >
      <div class="log-header">
        <div class="log-title">{{ title }}</div>
        <div class="log-actions">
          <a-button
            type="text"
            :title="isFullscreen ? '退出全屏' : '全屏显示'"
            @click="toggleFullscreen"
          >
            <template #icon>
              <FullscreenExitOutlined v-if="isFullscreen" />
              <FullscreenOutlined v-else />
            </template>
          </a-button>
        </div>
      </div>
      <div class="log-body" ref="logBodyRef" @scroll="handleScroll">
        <pre v-if="logContent" v-html="formattedLog"></pre>
        <div v-else class="log-empty">暂无日志内容</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue';
import {
  FullscreenOutlined,
  FullscreenExitOutlined,
} from '@ant-design/icons-vue';

const props = defineProps({
  logContent: {
    type: String,
    required: true,
  },
  title: {
    type: String,
    default: '构建日志',
  },
  autoScroll: {
    type: Boolean,
    default: false
  }
});

const isFullscreen = ref(false);
const logBodyRef = ref(null);
const isUserScrolling = ref(false);
const scrollTimeout = ref(null);
const lastScrollTop = ref(0);

const formattedLog = computed(() => {
  if (!props.logContent) return '';

  let formatted = props.logContent
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  return formatted;
});

// 切换全屏模式
const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value;
};

// 监听ESC键，用于退出全屏
const handleKeyDown = (event) => {
  if (event.key === 'Escape' && isFullscreen.value) {
    isFullscreen.value = false;
  }
};

// 处理用户滚动事件
const handleScroll = () => {
  if (!logBodyRef.value) return;
  
  const element = logBodyRef.value;
  const currentScrollTop = element.scrollTop;
  
  // 检测用户是否在向上滚动
  if (currentScrollTop < lastScrollTop.value) {
    isUserScrolling.value = true;
  }
  
  // 检测是否滚动到底部
  const isAtBottom = element.scrollHeight - element.scrollTop - element.clientHeight <= 5;
  if (isAtBottom) {
    isUserScrolling.value = false;
  }
  
  lastScrollTop.value = currentScrollTop;
  
  if (scrollTimeout.value) {
    clearTimeout(scrollTimeout.value);
  }
  
  // 设置定时器，如果用户停止滚动3秒后，重新启用自动滚动
  scrollTimeout.value = setTimeout(() => {
    const isStillAtBottom = element.scrollHeight - element.scrollTop - element.clientHeight <= 5;
    if (isStillAtBottom) {
      isUserScrolling.value = false;
    }
  }, 3000);
};

// 平滑滚动到底部
const scrollToBottom = (smooth = false) => {
  if (!logBodyRef.value) return;
  
  const element = logBodyRef.value;
  
  if (smooth) {
    // 平滑滚动
    element.scrollTo({
      top: element.scrollHeight,
      behavior: 'smooth'
    });
  } else {
    // 立即滚动
    element.scrollTop = element.scrollHeight;
  }
};

// 强制滚动到底部
const forceScrollToBottom = () => {
  isUserScrolling.value = false;
  scrollToBottom();
};

defineExpose({
  logBodyRef,
  scrollToBottom,
  forceScrollToBottom
});

// 防抖函数
const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

const debouncedScrollToBottom = debounce(() => {
  if (props.autoScroll && !isUserScrolling.value) {
    scrollToBottom();
  }
}, 50); // 50ms防抖

// 日志内容变化时，自动滚动到底部
watch(() => props.logContent, (newContent, oldContent) => {
  if (!newContent) return;
  
  if (oldContent && newContent.length <= oldContent.length) {
    return;
  }
  
  nextTick(() => {
    debouncedScrollToBottom();
  });
}, { flush: 'post' });

// 监听autoScroll属性变化
watch(() => props.autoScroll, (newValue) => {
  if (newValue && !isUserScrolling.value) {
    nextTick(() => {
      scrollToBottom();
    });
  }
});

onMounted(() => {
  // 添加键盘事件监听
  document.addEventListener('keydown', handleKeyDown);
  
  // 初始滚动到底部
  if (props.autoScroll) {
    nextTick(() => {
      scrollToBottom();
    });
  }
});

onUnmounted(() => {
  // 移除键盘事件监听
  document.removeEventListener('keydown', handleKeyDown);
  
  // 清理定时器
  if (scrollTimeout.value) {
    clearTimeout(scrollTimeout.value);
  }
});
</script>

<style scoped>
.fullscreen-log-viewer {
  width: 100%;
  height: 100%;
  max-height: 100%;
  overflow: hidden;
}

.fullscreen-log-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  max-height: 100%;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  overflow: hidden;
  background-color: #1e1e1e;
  transition: all 0.3s;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background-color: #2d2d2d;
  color: #fff;
  border-bottom: 1px solid #000;
}

.log-title {
  font-weight: 500;
  font-size: 14px;
}

.log-actions {
  display: flex;
  gap: 8px;
}

:deep(.anticon) {
  color: #fff;
}

.log-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  background-color: #1e1e1e;
  max-height: calc(100% - 40px); /* 减去header的高度 */
  scroll-behavior: smooth; /* 启用平滑滚动 */
}

.log-body pre {
  margin: 0;
  color: #fff;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 13px;
  line-height: 1.5;
}

.fullscreen-mode {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  border-radius: 0;
  border: none;
  width: 100vw;
  height: 100vh;
}

.log-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #666;
  font-style: italic;
}

/* 自定义滚动条样式 */
.log-body::-webkit-scrollbar {
  width: 8px;
}

.log-body::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.log-body::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

.log-body::-webkit-scrollbar-thumb:hover {
  background: #777;
}
</style>