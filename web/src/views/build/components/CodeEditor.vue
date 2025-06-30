<template>
  <div class="code-editor">
    <div class="editor-header">
      <span>{{ title }}</span>
    </div>
    <div class="editor-content">
      <Codemirror
        ref="editorRef"
        v-model="code"
        :placeholder="placeholder"
        :autofocus="false"
        :indent-with-tab="true"
        :tab-size="2"
        :extensions="extensions"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { Codemirror } from 'vue-codemirror';
import { StreamLanguage } from '@codemirror/language';
import { shell } from '@codemirror/legacy-modes/mode/shell';
import { oneDark } from '@codemirror/theme-one-dark';
import { EditorView } from '@codemirror/view';
// import "codemirror/mode/shell/shell.js";

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  title: {
    type: String,
    required: true,
  },
  placeholder: {
    type: String,
    default: '',
  },
  maxHeight: {
    type: Number,
    default: 400, // 默认最大高度为400px
  },
});

const emit = defineEmits(['update:modelValue']);
const editorRef = ref(null);
const code = ref(props.modelValue);

// 编辑器扩展
const extensions = [
  StreamLanguage.define(shell),
  oneDark,
  EditorView.lineWrapping,
  EditorView.theme({
    "&": {
      maxHeight: `${props.maxHeight}px`,
      height: "auto"
    },
    ".cm-scroller": {
      overflow: "auto"
    },
    ".cm-content": {
      minHeight: "100px"
    }
  })
];

watch(code, (newValue) => {
  emit('update:modelValue', newValue);
});

watch(() => props.modelValue, (newValue) => {
  if (code.value !== newValue) {
    code.value = newValue;
  }
});
</script>

<style scoped>
.code-editor {
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  overflow: hidden;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #fafafa;
  color: rgba(0, 0, 0, 0.85);
  border-bottom: 1px solid #d9d9d9;
  font-size: 14px;
  font-weight: 500;
}

.editor-content {
  position: relative;
}

:deep(.cm-editor) {
  height: 100%;
}

:deep(.cm-editor.cm-focused) {
  outline: none;
}

:deep(.cm-scroller) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.5;
  padding: 8px;
}

:deep(.cm-content) {
  white-space: pre-wrap;
}
</style> 