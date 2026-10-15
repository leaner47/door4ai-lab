// 自动生成，勿手改：scripts/gen-access-map.mjs（npm run build 时运行）
export type PostAccess = { access: 'free' | 'paid'; series?: string };
export const POSTS: Record<string, PostAccess> = {
  "attention-qkv": {
    "access": "paid",
    "series": "ai-mastery"
  },
  "computer-anatomy": {
    "access": "paid",
    "series": "ai-mastery"
  },
  "kv-cache-quantization": {
    "access": "paid",
    "series": "ai-mastery"
  }
};
export const LABS: Record<string, string> = {
  "labs/attention-qkv": "attention-qkv",
  "labs/computer-anatomy": "computer-anatomy",
  "labs/kv-cache": "kv-cache-quantization"
};
