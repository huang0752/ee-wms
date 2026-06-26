<!-- 重置密码 / 忘记密码 -->
<template>
  <div>
    <ElForm
      ref="formRef"
      :model="forgetForm"
      :rules="forgetRules"
      :key="formKey"
      class="login-page-form mt-4"
      @keyup.enter="$emit('submit')"
    >
      <ElFormItem prop="username">
        <ElInput
          v-model.trim="forgetForm.username"
          class="custom-height"
          clearable
          :placeholder="$t('login.placeholder.username')"
          @keyup.enter="$emit('submit')"
        >
          <template #prefix>
            <ElIcon><User /></ElIcon>
          </template>
        </ElInput>
      </ElFormItem>
      <ElFormItem prop="email">
        <ElInput
          v-model.trim="forgetForm.email"
          class="custom-height"
          clearable
          :placeholder="$t('forgetPassword.placeholder.email')"
          @keyup.enter="$emit('submit')"
        >
          <template #prefix>
            <ElIcon><Message /></ElIcon>
          </template>
        </ElInput>
      </ElFormItem>
      <ElFormItem prop="code">
        <div class="flex w-full items-center gap-2.5">
          <ElInput
            v-model.trim="forgetForm.code"
            class="custom-height min-w-0 flex-1"
            clearable
            maxlength="6"
            :placeholder="$t('forgetPassword.placeholder.code')"
            @keyup.enter="$emit('submit')"
          >
            <template #prefix>
              <ElIcon><Lock /></ElIcon>
            </template>
          </ElInput>
          <ElButton
            class="h-10 shrink-0"
            :loading="codeSending"
            :disabled="codeCountdown > 0"
            @click="$emit('sendCode')"
          >
            {{ codeCountdown > 0 ? `${codeCountdown}s` : $t("forgetPassword.sendCode") }}
          </ElButton>
        </div>
      </ElFormItem>
      <ElTooltip :visible="isCapsLock" :content="$t('login.capsLock')" placement="right">
        <ElFormItem prop="new_password">
          <ElInput
            v-model.trim="forgetForm.new_password"
            class="custom-height"
            type="password"
            autocomplete="off"
            show-password
            clearable
            :placeholder="$t('login.placeholder.password')"
            @keyup="checkCapsLock"
          >
            <template #prefix>
              <ElIcon><Lock /></ElIcon>
            </template>
          </ElInput>
        </ElFormItem>
      </ElTooltip>
      <ElTooltip :visible="isCapsLock" :content="$t('login.capsLock')" placement="right">
        <ElFormItem prop="confirmPassword">
          <ElInput
            v-model.trim="forgetForm.confirmPassword"
            class="custom-height"
            type="password"
            autocomplete="off"
            show-password
            clearable
            :placeholder="$t('login.message.password.confirm')"
            @keyup="checkCapsLock"
          >
            <template #prefix>
              <ElIcon><Lock /></ElIcon>
            </template>
          </ElInput>
        </ElFormItem>
      </ElTooltip>
      <div class="mt-6">
        <ElButton
          class="h-11 w-full min-w-0 rounded-lg! text-base font-medium"
          type="primary"
          :loading="forgetLoading"
          v-ripple
          @click="$emit('submit')"
        >
          {{ $t("common.confirm") }}
        </ElButton>
      </div>
    </ElForm>

    <FaLoginAuthLinkRow
      :hint="$t('login.thinkOfPasswd')"
      :link-text="$t('login.backLoginBtnText')"
      @link="$emit('toLogin')"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Lock, Message, User } from "@element-plus/icons-vue";
import type { ForgetPasswordForm } from "@/api/module_system/user";
import type { FormRules } from "element-plus";

const forgetForm = defineModel<ForgetPasswordForm>("forgetForm", { required: true });

defineOptions({ name: "FaLoginForgetPanel" });

interface Props {
  forgetRules: FormRules<ForgetPasswordForm>;
  formKey: number | string;
  forgetLoading: boolean;
  codeSending: boolean;
  codeCountdown: number;
}

withDefaults(defineProps<Props>(), {});

interface Emits {
  submit: [];
  sendCode: [];
  toLogin: [];
}

const emit = defineEmits<Emits>();

const formRef = ref();
const isCapsLock = ref(false);

function checkCapsLock(event: KeyboardEvent) {
  if (event instanceof KeyboardEvent) {
    isCapsLock.value = event.getModifierState("CapsLock");
    if (event.key === "Enter") {
      emit("submit");
    }
  }
}

defineExpose({
  validate: () => formRef.value?.validate?.(),
  validateField: (props: string | string[]) => formRef.value?.validateField?.(props),
  clearValidate: () => formRef.value?.clearValidate?.(),
});
</script>

<style scoped lang="scss">
@use "../fa-login";
</style>
