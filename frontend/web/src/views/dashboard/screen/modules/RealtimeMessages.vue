<template>
  <div class="panel p1">
    <div class="panel-hd">
      <span class="dot accent" />实时操作日志
      <span class="msg-count">NEW</span>
    </div>
    <div class="msg-scroll">
      <div v-if="messagesDuplicated.length > 0" class="msg-inner">
        <div v-for="(m, i) in messagesDuplicated" :key="i" class="msg-row">
          <span class="msg-time">{{ m.time }}</span>
          <span class="msg-tag" :class="m.tag">{{ m.tagText }}</span>
          <span>{{ m.text }}</span>
        </div>
      </div>
      <div v-else class="msg-empty">暂无实时库存流水</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

defineOptions({ name: "RealtimeMessages" });

interface ScreenMessage {
  time: string;
  tag: string;
  tagText: string;
  text: string;
}

const props = withDefaults(
  defineProps<{
    messages?: ScreenMessage[];
  }>(),
  {
    messages: () => [],
  }
);

const messagesDuplicated = computed(() => {
  return props.messages.length > 0 ? [...props.messages, ...props.messages] : [];
});
</script>

<style scoped>
.msg-scroll {
  position: relative;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.msg-inner {
  width: 100%;
  animation: scrollUp 28s linear infinite;
}

.msg-empty {
  display: grid;
  height: 100%;
  font-size: 12px;
  color: #94a3b8;
  place-items: center;
  opacity: 0.65;
}

.msg-row {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 5px 0;
  font-size: 11px;
  border-bottom: 1px solid rgb(26 40 80 / 30%);
  opacity: 0.75;
}

.msg-time {
  flex-shrink: 0;
  width: 38px;
  font-variant-numeric: tabular-nums;
  opacity: 0.4;
}

.msg-tag {
  flex-shrink: 0;
  padding: 1px 4px;
  font-size: 9px;
  border-radius: 3px;
}

.msg-tag.order {
  color: #00d4ff;
  background: rgb(0 212 255 / 15%);
}

.msg-tag.system {
  color: #7c3aed;
  background: rgb(124 58 237 / 15%);
}

.msg-tag.audit {
  color: #10b981;
  background: rgb(16 185 129 / 15%);
}

.msg-tag.deploy {
  color: #f59e0b;
  background: rgb(245 158 11 / 15%);
}

.msg-tag.notice {
  color: #00d4ff;
  background: rgb(0 212 255 / 15%);
}

.msg-tag.alarm {
  color: #ef4444;
  background: rgb(239 68 68 / 15%);
}

.msg-count {
  padding: 2px 6px;
  margin-left: auto;
  font-size: 10px;
  color: #00d4ff;
  background: rgb(0 212 255 / 15%);
  border-radius: 10px;
  opacity: 0.6;
}
@keyframes scrollUp {
  0% {
    transform: translateY(0);
  }

  100% {
    transform: translateY(-50%);
  }
}
</style>
