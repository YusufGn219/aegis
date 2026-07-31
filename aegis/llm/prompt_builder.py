"""System prompt + dinamik enum-kisitli tool semalarini birlestirip vLLM'e
gonderilecek istegi kurar.

ONEMLI (kullanilan vLLM surumunde - 0.26.0 - dogrulandi): tool_choice="auto"
ile guided decoding HICBIR ZAMAN uygulanmiyor (vllm/tool_parsers/utils.py
get_json_schema_from_tools: tool_choice=="auto" -> None doner). Yani JSON
semadaki `enum` kisiti auto modda sadece bir "ipucu"dur, gercek bir kisit
DEGILDIR - model enum disina cikabilir. Guided decoding sadece tool_choice
"required" ya da ISIMLENDIRILMIS (named) bir fonksiyon secildiginde devreye
girer. Bu yuzden asil halusinasyon-onleme garantisi iki asamali akistan
gelir: once assemble_request() (auto) ile HANGI tool'un (varsa) cagrilacagina
karar verilir, sonra assemble_named_request() ile O tool icin ISIMLENDIRILMIS
tool_choice kullanilarak argumanlar GERCEKTEN enum-kisitli uretilir. Bkz.
aegis.skills.workspace_organizer_skill (iki asamali cagriyi orkestre eden yer)
ve tests/integration/test_vllm_tool_calls.py (bu davranisi dogrulayan test)."""

from __future__ import annotations

from aegis import config
from aegis.tools.base import ToolContext
from aegis.tools.base import Tool

PROMPT_VERSION = "v2"

SYSTEM_PROMPT = (
    "Sen bir workspace asistanisin. Kullanicinin istegini karsilamak icin "
    "verilen tool'lardan tam olarak birini cagirmalisin. Her parametre "
    "degeri MUTLAKA o parametrenin enum listesinden secilmeli - listede "
    "olmayan bir deger UYDURMA. Uygun bir deger yoksa 'YOK' sec. Ornek: "
    "kullanici 'bir dosyayi tasi' der ama hangi dosya oldugunu belirtmezse, "
    "o parametre icin YOK sec; kendi dosya adini UYDURMA. E-posta "
    "isteklerinde, mesajdaki tirnak icindeki ifadelerin SIRASI onemlidir: "
    "ilk tirnakli ifade konudur (subject), ikinci tirnakli ifade govdedir "
    "(body). Hicbir tool istege uymuyorsa tool cagirma, normal ve Turkce "
    "bir cevap ver - ornegin 'Bugun hava nasil?' gibi bir soruya tool "
    "cagirmadan, duz metinle cevap ver."
)


def build_tool_schemas(tools: list[Tool], ctx: ToolContext) -> list[dict]:
    return [{"type": "function", "function": t.build_schema(ctx)} for t in tools]


def assemble_request(user_message: str, tools: list[Tool], ctx: ToolContext) -> dict:
    """tool_choice="auto": hangi tool'un (varsa) uygun oldugunu belirlemek
    icin. Guided decoding UYGULANMAZ - tool adi ve argumanlar serbest
    uretilir, sadece hermes parser'in ayristirdigi metinden cikarilir."""
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


def assemble_named_request(user_message: str, tool: Tool, ctx: ToolContext) -> dict:
    """tool_choice olarak TEK, ISIMLENDIRILMIS bir fonksiyon zorlanir. Bu
    modda vLLM, o tool'un JSON semasini (enum dahil) guided decoding ile
    GERCEKTEN zorluyor - assemble_request()'in auto modundan farkli olarak
    argumanlar enum disina cikamaz."""
    return {
        "model": config.MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "tools": build_tool_schemas([tool], ctx),
        "tool_choice": {"type": "function", "function": {"name": tool.name}},
        "temperature": 0,
    }
