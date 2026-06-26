<template>
  <div class="chat-input" :class="{ 'chat-input--disabled': disabled }">
    <div class="input-wrapper">
      <div v-if="uploadedFiles.length > 0" class="uploaded-files">
        <div v-for="file in uploadedFiles" :key="file.id" class="file-item">
          <ElIcon class="file-icon"><Document /></ElIcon>
          <span class="file-name">{{ file.name }}</span>
          <ElIcon class="file-remove" @click="removeFile(file.id)"><Close /></ElIcon>
        </div>
      </div>
      <div class="input-container">
        <ElForm>
          <ElInput
            v-model="inputMessage"
            type="textarea"
            :placeholder="placeholder"
            :disabled="disabled || sending"
            :autosize="{ minRows: 1, maxRows: 6 }"
            resize="none"
            class="message-input"
            @keydown.enter.exact.prevent="handleSend"
            @keydown.shift.enter.exact="handleShiftEnter"
          />
        </ElForm>
        <div class="input-footer">
          <div class="input-footer-left">
            <div class="model-switcher model-switcher--readonly">
              <ElIcon class="model-icon"><Cpu /></ElIcon>
              <span class="model-name" :title="activeModelName">
                {{ activeModelName }}
              </span>
            </div>
          </div>
          <div class="input-actions">
            <ElUpload
              ref="uploadRef"
              :auto-upload="false"
              :show-file-list="false"
              :on-change="handleFileChange"
              :accept="acceptTypes"
              :multiple="true"
            >
              <ElButton :icon="Paperclip" class="upload-btn" circle />
            </ElUpload>
            <ElButton
              v-if="sending"
              class="send-button"
              type="danger"
              circle
              title="停止生成"
              @click="handleStop"
            >
              <ElIcon><VideoPause /></ElIcon>
            </ElButton>
            <ElButton
              v-else
              :disabled="(!inputMessage.trim() && uploadedFiles.length === 0) || disabled"
              class="send-button"
              type="primary"
              circle
              @click="handleSend"
            >
              <ElIcon><Promotion /></ElIcon>
            </ElButton>
          </div>
        </div>
      </div>
      <div class="input-hint">
        <span>按 Enter 发送消息，Shift + Enter 换行</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import {
  Promotion,
  Paperclip,
  Document,
  Close,
  VideoPause,
  Cpu,
} from "@element-plus/icons-vue";
import type { UploadFile } from "element-plus";
import type { UploadedFile } from "../types";
import AiChatAPI, { type AiModelConfigItem, type AiModelConfigList } from "@/api/module_ai/chat";

interface Props {
  disabled?: boolean;
  sending?: boolean;
  isConnected?: boolean;
}

interface Emits {
  (e: "send", message: string, files?: UploadedFile[]): void;
  (e: "stop"): void;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  sending: false,
  isConnected: true,
});

const emit = defineEmits<Emits>();

// ============ 模型选择器 ============ //
const items = ref<AiModelConfigItem[]>([]);
const defaultId = ref<number | null>(null);

const activeModelName = computed(() => {
  const item = items.value.find((i) => i.id === defaultId.value);
  return item ? `${item.name} · ${item.model_id}` : "平台默认模型";
});

const loadModels = async () => {
  try {
    const res = await AiChatAPI.getModelConfig();
    if (res.data?.code === 0 && res.data.data) {
      const data: AiModelConfigList = res.data.data;
      items.value = data.items || [];
      defaultId.value = data.default_id ?? data.active_id;
    }
  } catch {
    /* 静默失败 */
  }
};

onMounted(loadModels);

const inputMessage = ref("");
const uploadedFiles = ref<UploadedFile[]>([]);

const acceptTypes = computed(() => {
  return ".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif,.mp3,.wav,.mp4,.avi,.mov";
});

const placeholder = computed(() => {
  return props.isConnected ? "向FA助手发送消息..." : "请先连接到服务器";
});

const handleFileChange = (uploadFile: UploadFile) => {
  const file = uploadFile.raw;
  if (!file) return;

  const maxSize = 10 * 1024 * 1024;
  if (file.size > maxSize) {
    alert("文件大小不能超过10MB");
    return;
  }

  const uploadedFile: UploadedFile = {
    id: Date.now().toString() + Math.random().toString(36).substr(2),
    name: file.name,
    size: file.size,
    type: file.type,
    file,
  };

  uploadedFiles.value.push(uploadedFile);
};

const removeFile = (id: string) => {
  const index = uploadedFiles.value.findIndex((f) => f.id === id);
  if (index > -1) {
    uploadedFiles.value.splice(index, 1);
  }
};

const handleSend = () => {
  const message = inputMessage.value.trim();
  if ((!message && uploadedFiles.value.length === 0) || props.disabled || props.sending) {
    return;
  }
  emit("send", message, uploadedFiles.value.length > 0 ? [...uploadedFiles.value] : undefined);
  inputMessage.value = "";
  uploadedFiles.value = [];
};

const handleStop = () => {
  if (!props.sending) return;
  emit("stop");
};

const handleShiftEnter = () => {
  inputMessage.value += "\n";
};

defineExpose({
  refresh: loadModels,
  focus: () => {
    const input = document.querySelector(".message-input textarea") as HTMLTextAreaElement;
    input?.focus();
  },
});
</script>

<style lang="scss" scoped>
.chat-input {
  .input-wrapper {
    max-width: 800px;
    padding: 20px;
    margin: 0 auto;

    .uploaded-files {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;

      .file-item {
        display: flex;
        gap: 6px;
        align-items: center;
        padding: 8px 14px;
        font-size: 13px;
        background: var(--el-fill-color-light);
        border: 1px solid var(--el-border-color-light);
        border-radius: 8px;
        transition: all 0.2s ease;

        &:hover {
          background: var(--el-color-primary-light-9);
          border-color: var(--el-color-primary-light-7);
        }

        .file-icon {
          font-size: 16px;
          color: var(--el-color-primary);
        }

        .file-name {
          max-width: 180px;
          overflow: hidden;
          text-overflow: ellipsis;
          font-size: 13px;
          white-space: nowrap;
        }

        .file-remove {
          font-size: 14px;
          color: var(--el-text-color-secondary);
          cursor: pointer;
          transition: color 0.2s ease;

          &:hover {
            color: var(--el-color-danger);
          }
        }
      }
    }

    .input-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding: 20px;
      background: var(--el-bg-color-overlay);
      border: 1px solid var(--el-border-color-light);
      border-radius: 16px;
      box-shadow: var(--el-box-shadow-light);
      transition:
        border-color 0.2s ease,
        box-shadow 0.2s ease,
        transform 0.2s ease;

      &:hover {
        border-color: var(--el-color-primary);
        box-shadow: var(--el-box-shadow);
        transform: translateY(-2px);
      }

      &:focus-within {
        border-color: var(--el-color-primary);
        box-shadow: 0 0 0 1px var(--el-color-primary);
      }

      .message-input {
        flex: 1;
        min-width: 0;

        :deep(.el-textarea__inner) {
          padding: 0;
          line-height: 1.6;
          color: var(--el-text-color-primary);
          resize: none;
          background: transparent;
          border: none;
          box-shadow: none;
        }

        :deep(.el-textarea) {
          padding: 0;
        }
      }

      .input-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-top: 8px;

        .input-footer-left {
          display: flex;
          gap: 8px;
          align-items: center;
        }

        .model-switcher {
          display: flex;
          gap: 6px;
          align-items: center;
          height: 30px;
          padding: 0 10px;
          font-size: 13px;
          color: var(--el-text-color-regular);
          cursor: pointer;
          background: var(--el-fill-color-blank);
          border: 1px solid var(--el-border-color-light);
          border-radius: 6px;
          transition: all 0.2s;

          &:hover {
            color: var(--el-color-primary);
            background: var(--el-color-primary-light-9);
            border-color: var(--el-color-primary-light-5);
          }

          &.is-active {
            color: var(--el-color-primary);
            background: var(--el-color-primary-light-9);
            border-color: var(--el-color-primary);
          }

          .model-icon {
            font-size: 14px;
          }

          .model-name {
            max-width: 120px;
            overflow: hidden;
            text-overflow: ellipsis;
            font-weight: 500;
            white-space: nowrap;
          }

          .model-arrow {
            font-size: 12px;
            transition: transform 0.2s;

            &.expanded {
              transform: rotate(180deg);
            }
          }
        }

        .input-actions {
          display: flex;
          gap: 10px;
          align-items: center;

          .upload-btn {
            font-size: 18px;
            color: var(--el-text-color-secondary);
            transition: all 0.2s ease;

            &:hover {
              color: var(--el-color-primary);
              transform: scale(1.05);
            }
          }

          .send-button {
            flex-shrink: 0;
            border-radius: 50%;
            box-shadow: var(--el-box-shadow-light);
            transition: all 0.2s ease;

            &:hover {
              box-shadow: var(--el-box-shadow);
              transform: translateY(-1px);
            }

            &:active {
              transform: translateY(0);
            }
          }
        }
      }
    }

    .input-hint {
      margin-top: 12px;
      font-size: 12px;
      font-weight: 400;
      color: var(--el-text-color-secondary);
      text-align: center;
      letter-spacing: 0.5px;
    }
  }

  &.chat-input--disabled .input-wrapper .input-container {
    opacity: 0.72;
    filter: grayscale(0.06);

    &:hover {
      border-color: var(--el-border-color-light);
      box-shadow: var(--el-box-shadow-light);
      transform: none;
    }

    &:focus-within {
      border-color: var(--el-border-color-light);
      box-shadow: var(--el-box-shadow-light);
    }
  }
}
</style>

<style lang="scss">
/* 下拉菜单项样式 - 因为 scoped 限制无法直接覆盖命令项 */
.el-dropdown-menu {
  min-width: 240px;

  .el-dropdown-menu__item {
    display: flex;
    gap: 8px;
    align-items: center;
    padding: 8px 12px;

    &.is-active {
      color: var(--el-color-primary);
      background: var(--el-color-primary-light-9);
    }

    .dropdown-icon {
      flex-shrink: 0;
      font-size: 14px;
    }

    .dropdown-content {
      flex: 1;
      min-width: 0;
    }

    .dropdown-label {
      font-size: 14px;
      font-weight: 500;
    }

    .dropdown-meta {
      max-width: 160px;
      overflow: hidden;
      text-overflow: ellipsis;
      font-size: 12px;
      color: var(--el-text-color-secondary);
      white-space: nowrap;
    }

    .dropdown-empty {
      font-size: 13px;
      color: var(--el-text-color-secondary);
    }

    .el-tag {
      flex-shrink: 0;
      margin-left: auto;
    }
  }
}
</style>
