from pydantic import BaseModel

from app.llm.gateway import extract_json


class X(BaseModel):
    a: int


def test_extract_json_repairs_common_garbage():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('<think>hmm</think>Вот ответ: {"a": 2} — готово') == {"a": 2}
