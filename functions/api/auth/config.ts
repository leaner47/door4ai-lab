// GET /api/auth/config → 登录页需要的公开配置
import { authEnabled, json, type AuthEnv } from '../../_lib/auth/util';

export const onRequestGet: PagesFunction<AuthEnv> = async ({ env }) =>
  json({ enabled: authEnabled(env), turnstileSiteKey: env.TURNSTILE_SECRET ? env.TURNSTILE_SITE_KEY || null : null });
