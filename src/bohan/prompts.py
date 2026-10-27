"""Render a manual-review brief; never invent product claims or speech."""
import json
from pathlib import Path


def load_product(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Product must be a JSON object")
    for key in ("name", "image_ref"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ValueError(f"Product requires {key}")
    facts = value.get("facts")
    if not isinstance(facts, list) or not facts:
        raise ValueError("Product facts whitelist must not be empty")
    for fact in facts:
        if not isinstance(fact, dict) or any(not isinstance(fact.get(k), str) or not fact[k].strip()
                                            for k in ("claim", "evidence")):
            raise ValueError("Each product fact needs claim and evidence")
    return value


def render(product: dict | None, out: Path):
    if product is None:
        text = "# Seedance 2.0 提示词\n\n状态：blocked_missing_product\n缺少当前商品图片与卖点证据白名单，未生成提示词。\n"
        status = "blocked_missing_product"
    else:
        facts = "\n".join(f"- {f['claim']}（证据：{f['evidence']}）" for f in product["facts"])
        text = f"""# Seedance 2.0 导演草稿

状态：draft_needs_review。仅整理用户提供的商品事实，未完成参考视频复刻分析。
商品：{product['name']}
商品图片引用：{product['image_ref']}

## 已提供卖点白名单（证据内容仍需人工核对）
{facts}

## 固定约束
每个商品独立制作。外观、颜色、结构以本次商品图为准，禁止增加配件、Logo、功能或效果。
人物引用、场景、动作、德语原文与中文意思、镜头时长均待确认；没有确认口播时不自动补写。

## 制作顺序
1. 参考视频逐镜证据分析 → 当前商品白名单 → 三种商品驱动钩子。
2. 确认完整剧情、动作、德语与中文意思；真实试配音校验时长。
3. 建立人物/场景/道具状态母表；第一段九宫格独立关键帧与逐格质检。
4. 第一段完整提示词与生成视频审核；第二段首格衔接真实尾帧。
5. 第二段九宫格单独审核，再输出独立完整提示词。实际生成与发布须另行接入。

此文件不是已完成或可直接投产的最终提示词。transcript.json 和 vision.json 未复核时不得宣称完成视频分析。
"""
        status = "draft_needs_review"
    (out / "prompt.md").write_text(text, encoding="utf-8")
    return status
