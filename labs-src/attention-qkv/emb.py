import json,re,sys,torch
from safetensors import safe_open
from tokenizers import Tokenizer
t=Tokenizer.from_file(sys.argv[1]+'/tokenizer.json')
with safe_open(sys.argv[1]+'/model.safetensors','pt') as f:
    E=f.get_tensor('model.embed_tokens.weight').float()
En=torch.nn.functional.normalize(E,dim=1)
out={}
for w,sents in [('小米',['我在粮油店买了两斤小米','我在数码店买了一部小米']),('长城',['放假我们去北京爬了长城','他贷款买了一辆新款长城'])]:
    i=t.encode(w).ids; assert len(i)==1; i=i[0]
    sims=En@En[i]
    top=torch.topk(sims,400)
    nn=[]
    for v,j in zip(top.values.tolist(),top.indices.tolist()):
        s=t.decode([j]).strip()
        if j==i or not re.fullmatch(r'[一-鿿]{1,4}',s) or s in [x[0] for x in nn]: continue
        nn.append((s,round(v,3)))
        if len(nn)>=8: break
    per=[]
    for s in sents:
        ids=t.encode(s).ids
        per.append([[t.decode([j]),round(float(sims[j]),3)] for j in ids])
    out[w]={'nearest':nn,'sent_sims':per}
    print(w,nn); print(per)
json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False)
