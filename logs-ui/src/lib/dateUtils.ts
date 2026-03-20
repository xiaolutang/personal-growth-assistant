/** 日期工具函数 */

/** 获取今天的 ISO 时间范围 */
export function getTodayISORange(): { start_time: string; end_time: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
  return {
    start_time: start.toISOString(),
    end_time: end.toISOString(),
  };
}

/** ISO 时间转 datetime-local 输入框格式 */
export function isoToDateTimeLocal(iso: string | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/** datetime-local 格式转 ISO 时间 */
export function dateTimeLocalToISO(local: string): string {
  if (!local) return '';
  return new Date(local).toISOString();
}
