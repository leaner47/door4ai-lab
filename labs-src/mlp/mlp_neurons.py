"""Find Qwen3-0.6B MLP neurons whose activation at the polysemous word differs most between two contexts,
and which tokens each neuron's output direction promotes (logit lens on the neuron's down-projection column)."""
import json, re, sys, torch
from transformers import AutoModelForCausalLM, PreTrainedTokenizerFast
MD, OUT = sys.argv[1], sys.argv[2]
tok = PreTrainedTokenizerFast(tokenizer_file=MD + "/tokenizer.json")
model = AutoModelForCausalLM.from_pretrained(MD, dtype=torch.float32); model.eval()
L = model.config.num_hidden_layers
E = model.model.embed_tokens.weight.detach()
normw = model.model.norm.weight.detach()
zh = re.compile(r'^[一-鿿]{1,4}$')
vocab_ok = torch.tensor([bool(zh.match(tok.decode([i]).strip())) for i in range(E.shape[0])])
acts = {}
def hook(l):
    def f(mod, inp): acts[l] = inp[0][0, -1].detach().clone()
    return f
hs = [model.model.layers[l].mlp.down_proj.register_forward_pre_hook(hook(l)) for l in range(L)]
def run(s):
    acts.clear()
    with torch.no_grad(): model(tok(s, return_tensors="pt").input_ids)
    return [acts[l] for l in range(L)]
def promote(l, n, sign, k=6):
    v = model.model.layers[l].mlp.down_proj.weight[:, n].detach() * sign
    lg = (E * normw) @ v
    lg[~vocab_ok] = -1e9
    idx = torch.topk(lg, k).indices.tolist()
    return [tok.decode([i]).strip() for i in idx]
PAIRS = [("小米", "我在粮油店买了两斤小米", "我在数码店买了一部小米"), ("长城", "放假我们去北京爬了长城", "他贷款买了一辆新款长城")]
res = []
for w, a, b in PAIRS:
    A, B = run(a), run(b)
    layers = []
    for l in range(L):
        d = A[l] - B[l]
        top = torch.topk(d.abs(), 8).indices.tolist()
        layers.append({
            "diff_norm": round(d.norm().item() / (A[l].norm().item() + B[l].norm().item()) * 2, 4),
            "top": [{"n": n, "a": round(A[l][n].item(), 3), "b": round(B[l][n].item(), 3),
                     "promote": promote(l, n, 1 if (A[l][n] if abs(A[l][n]) >= abs(B[l][n]) else B[l][n]) > 0 else -1)} for n in top]})
    res.append({"word": w, "a": a, "b": b, "layers": layers})
    for l in (8, 20, 24, 27):
        print(w, l, layers[l]["diff_norm"], [(t["n"], t["a"], t["b"], t["promote"][:4]) for t in layers[l]["top"][:3]])
json.dump(res, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
