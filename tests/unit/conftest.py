"""Skill-seviyesi testler arasinda paylasilan kucuk yardimcilar."""


def fake_tool_call_response(tool_name: str, arguments_json: str):
    class _FakeFunction:
        name = tool_name
        arguments = arguments_json

    class _FakeToolCall:
        function = _FakeFunction()

    class _FakeMessage:
        tool_calls = [_FakeToolCall()]
        content = None

    class _FakeChoice:
        message = _FakeMessage()

    class _FakeUsage:
        prompt_tokens = 10
        completion_tokens = 5

    class _FakeResponse:
        choices = [_FakeChoice()]
        usage = _FakeUsage()

    return _FakeResponse()
