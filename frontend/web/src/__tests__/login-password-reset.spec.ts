import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick, reactive } from "vue";
import FaLoginAccountForm from "@/components/views/fa-login/forms/FaLoginAccountForm.vue";
import FaLoginForgetPanel from "@/components/views/fa-login/panels/FaLoginForgetPanel.vue";
import type { CaptchaInfo } from "@/api/module_system/auth";
import type { ForgetPasswordForm } from "@/api/module_system/user";

vi.mock("@/components/views/fa-login/widgets/FaLoginThirdPartySection.vue", () => ({
  default: { name: "FaLoginThirdPartySection", template: '<div data-test="oauth-section" />' },
}));

const global = {
  directives: { ripple: {} },
  mocks: {
    $t: (key: string) => key,
  },
  stubs: {
    ElButton: { template: "<button><slot /></button>" },
    ElCheckbox: { template: "<label><slot /></label>" },
    ElDivider: { template: "<div><slot /></div>" },
    ElForm: {
      template: "<form><slot /></form>",
      methods: { validate: () => Promise.resolve(true), clearValidate: vi.fn() },
    },
    ElFormItem: { template: "<div><slot /></div>" },
    ElIcon: { template: "<i><slot /></i>" },
    ElImage: { template: "<img />" },
    ElInput: {
      template: '<label><input /><span>{{ placeholder }}</span><slot name="prefix" /></label>',
      props: ["modelValue", "placeholder"],
    },
    ElTooltip: { template: "<div><slot /></div>" },
    FaLoginAuthLinkRow: {
      template: '<button data-test="auth-link" @click="$emit(\'link\')"><slot /></button>',
    },
    User: true,
    Lock: true,
    Message: true,
  },
};

describe("login password reset", () => {
  it("does not render third-party login entry by default", () => {
    const captchaState: CaptchaInfo = { enable: false, key: "", img_base: "" };
    const wrapper = mount(FaLoginAccountForm, {
      global,
      props: {
        loginForm: { username: "", password: "", captcha: "", captcha_key: "" },
        "onUpdate:loginForm": vi.fn(),
        isPassing: false,
        "onUpdate:isPassing": vi.fn(),
        isClickPass: false,
        "onUpdate:isClickPass": vi.fn(),
        rules: {},
        captchaState,
        codeLoading: false,
        demoAccountKey: "super",
        accounts: [],
        formKey: 1,
        isDark: false,
        dragVerifyTextColor: "#333",
        loading: false,
      },
    });

    expect(wrapper.find('[data-test="oauth-section"]').exists()).toBe(false);
  });

  it("renders email and code fields for reset password", async () => {
    const forgetForm = reactive<ForgetPasswordForm>({
      username: "",
      email: "",
      code: "",
      new_password: "",
      confirmPassword: "",
    });
    const wrapper = mount(FaLoginForgetPanel, {
      global,
      props: {
        forgetForm,
        "onUpdate:forgetForm": vi.fn(),
        forgetRules: {},
        formKey: 1,
        forgetLoading: false,
        codeSending: false,
        codeCountdown: 0,
      },
    });

    await nextTick();

    expect(wrapper.text()).toContain("forgetPassword.placeholder.email");
    expect(wrapper.text()).toContain("forgetPassword.placeholder.code");
    expect(wrapper.text()).toContain("forgetPassword.sendCode");
  });
});
