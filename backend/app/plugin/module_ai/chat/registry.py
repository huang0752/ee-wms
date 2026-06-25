from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromptSpec:
    key: str
    name: str
    instructions: str
    version: str = "1.0.0"


@dataclass(frozen=True)
class ActionSpec:
    key: str
    name: str
    kind: str
    description: str
    payload_schema: dict[str, object] = field(default_factory=dict)


class AiRegistry:
    """Prompt/智能动作注册中心的轻量内存抽象。"""

    def __init__(self) -> None:
        self._prompts: dict[str, PromptSpec] = {}
        self._actions: dict[str, ActionSpec] = {}

    def register_prompt(self, spec: PromptSpec) -> None:
        self._prompts[spec.key] = spec

    def register_action(self, spec: ActionSpec) -> None:
        self._actions[spec.key] = spec

    def get_prompt(self, key: str) -> PromptSpec | None:
        return self._prompts.get(key)

    def get_action(self, key: str) -> ActionSpec | None:
        return self._actions.get(key)

    def list_prompts(self) -> list[PromptSpec]:
        return list(self._prompts.values())

    def list_actions(self) -> list[ActionSpec]:
        return list(self._actions.values())


default_ai_registry = AiRegistry()
default_ai_registry.register_prompt(
    PromptSpec(
        key="chat.default",
        name="默认对话 Prompt",
        instructions="使用中文回答，保持简洁明了；如果不确定，请说明。",
    )
)
default_ai_registry.register_action(
    ActionSpec(
        key="navigate.system",
        name="系统页面导航",
        kind="navigate",
        description="建议前端跳转到系统管理相关页面。",
        payload_schema={
            "type": "object",
            "required": ["path", "name"],
            "properties": {
                "path": {"type": "string"},
                "name": {"type": "string"},
            },
        },
    )
)
