import type { Locale } from "./locale";
import { enUS, koKR, zhCN, type Translations } from "./locales";

export const translations: Record<Locale, Translations> = {
  "en-US": enUS,
  "zh-CN": zhCN,
  "ko-KR": koKR,
};
