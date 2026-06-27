/**
 * 快速入口配置
 * 包含：应用列表、快速链接等配置
 */
import { WEB_LINKS } from "@/utils/constants/definitions";
import type { FastEnterConfig } from "@/types/config";

const fastEnterConfig: FastEnterConfig = {
  // 显示条件（屏幕宽度）
  minWidth: 1200,
  // 应用列表
  applications: [
    {
      name: "功能引导",
      description: "产品操作指南",
      icon: "ri:compass-3-line",
      iconColor: "#009688",
      enabled: true,
      order: 1,
      routeName: "FastlinkTutorial",
    },
    {
      name: "AI 助手",
      description: "智能问答与业务辅助",
      icon: "ri:user-line",
      iconColor: "#13DEB9",
      enabled: false,
      order: 2,
      routeName: "FastlinkFachat",
    },
    {
      name: "更新日志",
      description: "版本更新与变更记录",
      icon: "ri:gamepad-line",
      iconColor: "#38C0FC",
      enabled: true,
      order: 3,
      routeName: "FastlinkChangeLog",
    },
    {
      name: "操作手册",
      description: "产品操作指南",
      icon: "ri:book-2-line",
      iconColor: "#009688",
      enabled: true,
      order: 4,
      routeName: "FastlinkTutorial",
    },
  ],
  // 快速链接
  quickLinks: [
    {
      name: "登录",
      enabled: false,
      order: 1,
      routeName: "Login",
    },
    {
      name: "注册",
      enabled: false,
      order: 2,
      routeName: "Login",
    },
    {
      name: "忘记密码",
      enabled: false,
      order: 3,
      routeName: "Login",
    },
    {
      name: "礼花效果",
      enabled: true,
      order: 4,
      isDialog: true,
      featureFlag: "demoContent",
    },
    {
      name: "个人中心",
      enabled: true,
      order: 5,
      routeName: "FastlinkProfile",
    },
    {
      name: "留言管理",
      enabled: false,
      order: 6,
      routeName: "FastlinkArticleList",
      routeQuery: { commentWall: "1" },
    },
  ],
};

export default Object.freeze(fastEnterConfig);
