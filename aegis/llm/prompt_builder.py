"""System prompt + dinamik enum-kisitli tool semalarini birlestirip vLLM'e
gonderilecek istegi kurar. System prompt burada IKINCIL bir savunma katmani -
asil garanti tool semasindaki JSON `enum` kisiti (vLLM guided decoding bunu
zorluyor); prompt kaldirilsa da enum kisiti tek basina halusinasyonu engeller,
ama ucretsiz oldugu icin ve yonlendirmeye yardimci olabilecegi icin birakildi."""

from __future__ import annotations

from aegis import config
from aegis.tools.base import ToolContext
from aegis.tools.base import Tool

SYSTEM_PROMPT = (
    "Sen bir workspace asistanisin. Kullanicinin istegini karsilamak icin "
    "verilen tool'lardan tam olarak birini cagirmalisin. Her parametre "
    "degeri MUTLAKA o parametrenin enum listesinden secilmeli - listede "
    "olmayan bir deger UYDURMA. Uygun bir deger yoksa 'YOK' sec. Hicbir "
    "tool istege uymuyorsa tool cagirma, normal ve Turkce bir cevap ver."
)


def build_tool_schemas(tools: list[Tool], ctx: ToolContext) -> list[dict]:
    return [{"type": "function", "function": t.build_schema(ctx)} for t in tools]


def assemble_request(user_message: str, tools: list[Tool], ctx: ToolContext) -> dict:
    return {
        "model": config.MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "tools": build_tool_schemas(tools, ctx),
        "tool_choice": "auto",
        "temperature": 0,
    }
