"""Extract real attention data from Qwen3-0.6B for polysemy sentence pairs.
Output: JSON for the attention-qkv lab page."""
import json, math, sys
import torch
from transformers import AutoModelForCausalLM, PreTrainedTokenizerFast
from transformers.models.qwen3.modeling_qwen3 import apply_rotary_pos_emb

MD = sys.argv[1]
OUT = sys.argv[2]
torch.manual_seed(0)
tok = PreTrainedTokenizerFast(tokenizer_file=MD + "/tokenizer.json")
model = AutoModelForCausalLM.from_pretrained(MD, dtype=torch.float32, attn_implementation="eager")
model.eval()
cfg = model.config
H, KV, D = cfg.num_attention_heads, cfg.num_key_value_heads, cfg.head_dim
L = cfg.num_hidden_layers

PAIRS = [
    {"word": "小米", "a": "我在粮油店买了两斤小米", "b": "我在数码店买了一部小米", "ma": "粮食", "mb": "手机"},
    {"word": "长城", "a": "放假我们去北京爬了长城", "b": "他贷款买了一辆新款长城", "ma": "城墙", "mb": "汽车"},
]

def r(x, n=4):
    return round(float(x), n)

def run(sent):
    ids = tok(sent, return_tensors="pt").input_ids
    T = ids.shape[1]
    toks = [tok.decode([i]) for i in ids[0]]
    with torch.no_grad():
        out = model(ids, output_attentions=True, output_hidden_states=True)
        # attention from the last token (the polysemous word) : [L][H][T]
        att = [[[r(v) for v in out.attentions[l][0, h, -1, :].tolist()] for h in range(H)] for l in range(L)]
        # recompute layer-0 Q/K by hand for the score walk-through
        emb = out.hidden_states[0]
        lay = model.model.layers[0]
        sa = lay.self_attn
        hs = lay.input_layernorm(emb)
        q = sa.q_norm(sa.q_proj(hs).view(1, T, H, D)).transpose(1, 2)
        k = sa.k_norm(sa.k_proj(hs).view(1, T, KV, D)).transpose(1, 2)
        q_pre = q.clone()
        pos = torch.arange(T).unsqueeze(0)
        cos, sin = model.model.rotary_emb(hs, pos)
        q, k = apply_rotary_pos_emb(q, k, cos, sin)
        k = k.repeat_interleave(H // KV, dim=1)
        raw = torch.einsum('hd,htd->ht', q[0, :, -1, :], k[0])  # [H][T] raw dot products
        scaled = raw / math.sqrt(D)
        check = torch.softmax(scaled, -1)
        err = (check - out.attentions[0][0, :, -1, :]).abs().max().item()
        assert err < 1e-4, err
        hid = [out.hidden_states[l][0, -1, :] for l in range(L + 1)]
    return {
        "sent": sent, "tokens": toks, "att": att,
        "raw0": [[r(v, 2) for v in row] for row in raw.tolist()],
        "unscaled_softmax0": [[r(v) for v in row] for row in torch.softmax(raw, -1).tolist()],
        "q_pre0": q_pre[0, :, -1, :], "hid": hid,
    }

res = {"model": "Qwen3-0.6B", "layers": L, "heads": H, "kv_heads": KV, "head_dim": D, "pairs": []}
for p in PAIRS:
    A, B = run(p["a"]), run(p["b"])
    assert A["tokens"][-1] == p["word"] == B["tokens"][-1] and len(A["tokens"]) == len(B["tokens"])
    q_same = (A["q_pre0"] - B["q_pre0"]).abs().max().item()
    ang = []
    for l in range(L + 1):
        c = torch.nn.functional.cosine_similarity(A["hid"][l], B["hid"][l], dim=0).clamp(-1, 1)
        ang.append(r(math.degrees(math.acos(c.item())), 2))
    # pick the layer-0 head where the word attends most to the context words (excluding itself and position 0)
    best = None
    for h in range(H):
        sa_ = sum(A["att"][0][h][1:-1]); sb_ = sum(B["att"][0][h][1:-1])
        ma_ = max(A["att"][0][h][1:-1]); mb_ = max(B["att"][0][h][1:-1])
        score = min(ma_, mb_)
        if best is None or score > best[0]:
            best = (score, h)
    for X in (A, B):
        X.pop("q_pre0"); X.pop("hid")
    res["pairs"].append({"word": p["word"], "meaning_a": p["ma"], "meaning_b": p["mb"], "a": A, "b": B,
                         "angle_by_layer": ang, "q_identical_layer1_maxdiff": q_same, "best_head_layer1": best[1]})
    print(p["word"], "q diff", q_same, "best head", best[1], "angles", ang[:4], ang[-3:])
    for X in (A, B):
        h = best[1]
        print(" ", X["tokens"], [round(v * 100) for v in X["att"][0][h]])
        print("   raw", X["raw0"][h])
json.dump(res, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
print("ok")
