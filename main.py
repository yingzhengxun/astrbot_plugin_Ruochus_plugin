import aiohttp
import asyncio
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

API_BASE = "https://data.railgo.zenglingkun.cn"
V2_API_BASE = "https://rg-api.zenglingkun.cn"
UAPI_BASE = "https://uapis.cn/api/v1"

BASE_CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
  padding: 32px 24px;
  width: 820px;
  color: #1e293b;
}
.card {
  background: #ffffff;
  border-radius: 16px;
  padding: 28px 32px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.25);
  margin-bottom: 16px;
}
.card:last-child { margin-bottom: 0; }
.title {
  font-size: 22px; font-weight: 700; color: #0f172a;
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 16px;
}
.title .badge {
  font-size: 14px; font-weight: 600; color: #fff;
  background: #2563eb; border-radius: 20px; padding: 2px 14px;
}
.subtitle {
  font-size: 14px; color: #64748b; margin-top: -8px; margin-bottom: 16px;
}
.info-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 8px 24px; margin-bottom: 12px;
}
.info-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 0; border-bottom: 1px solid #f1f5f9;
  font-size: 14px;
}
.info-item .label { color: #64748b; }
.info-item .value { color: #0f172a; font-weight: 600; }
.section-title {
  font-size: 15px; font-weight: 700; color: #2563eb;
  margin: 16px 0 10px 0; padding-left: 10px;
  border-left: 3px solid #2563eb;
}
table {
  width: 100%; border-collapse: collapse; font-size: 13px;
}
th {
  background: #f8fafc; color: #64748b; font-weight: 600; padding: 8px 6px;
  text-align: left; border-bottom: 2px solid #e2e8f0;
}
td { padding: 7px 6px; border-bottom: 1px solid #f1f5f9; }
tr:last-child td { border-bottom: none; }
.status-on { color: #16a34a; font-weight: 600; }
.status-late { color: #dc2626; font-weight: 600; }
.status-early { color: #d97706; font-weight: 600; }
.footer {
  text-align: center; font-size: 12px; color: #94a3b8;
  padding-top: 12px; margin-top: 8px; border-top: 1px solid #e2e8f0;
}
.stop-badge {
  display: inline-block; background: #eff6ff; color: #2563eb;
  font-size: 11px; padding: 1px 8px; border-radius: 10px;
}
.seg-start { color: #2563eb; font-weight: 700; }
.seg-end { color: #dc2626; font-weight: 700; }
.train-card {
  background: #f8fafc; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;
  border-left: 4px solid #2563eb;
}
.train-card .train-num { font-size: 16px; font-weight: 700; color: #0f172a; }
.train-card .train-meta { font-size: 12px; color: #64748b; margin-top: 2px; }
.train-card .train-route { font-size: 13px; color: #334155; margin-top: 6px; }
.station-tag {
  display: inline-block; background: #f0fdf4; color: #16a34a;
  font-size: 11px; padding: 1px 8px; border-radius: 10px;
}
"""

TMPL_TRAIN_QUERY = """
<div class="card">
  <div class="title">
    🚄 {{ train_num }}
    <span class="badge">{{ train_type }}</span>
  </div>
  <div class="info-grid">
    <div class="info-item"><span class="label">路局</span><span class="value">{{ bureau }}</span></div>
    <div class="info-item"><span class="label">车型</span><span class="value">{{ car }}</span></div>
    <div class="info-item"><span class="label">配属</span><span class="value">{{ car_owner }}</span></div>
    <div class="info-item"><span class="label">客运段</span><span class="value">{{ runner }}</span></div>
    {% if rundays %}
    <div class="info-item" style="grid-column: 1/3;"><span class="label">运行日</span><span class="value">{{ rundays }}</span></div>
    {% endif %}
  </div>
  {% if exit_info %}
  <div class="section-title">🚪 检票口 / 站台{% if exit_station %}（{{ exit_station }}）{% endif %}</div>
  <div style="display:flex; gap:24px; flex-wrap:wrap; margin-bottom:8px; font-size:13px;">
    {% if exit_info.platform %}<div><span style="color:#64748b;">站台：</span><strong>{{ exit_info.platform }}</strong></div>{% endif %}
    {% if exit_info.entrance %}<div><span style="color:#64748b;">检票口：</span><strong>{{ exit_info.entrance }}</strong></div>{% endif %}
    {% if exit_info.exit_door %}<div><span style="color:#64748b;">出站口：</span><strong>{{ exit_info.exit_door }}</strong></div>{% endif %}
  </div>
  {% endif %}
  <div class="section-title">📋 时刻表</div>
  <table>
    <tr><th>#</th><th>车站</th><th>到达</th><th>出发</th><th>停时</th><th>里程</th></tr>
    {% for s in timetable %}
    <tr>
      <td style="color:#94a3b8;">{{ loop.index }}</td>
      <td><strong>{{ s.station }}</strong>{% if s.day_label %}<br><span style="font-size:11px;color:#94a3b8;">{{ s.day_label }}</span>{% endif %}</td>
      <td>{{ s.arrive }}</td>
      <td>{{ s.depart }}</td>
      <td>{% if s.stop > 0 %}<span class="stop-badge">停{{ s.stop }}分</span>{% else %}-{% endif %}</td>
      <td>{{ s.dist }}km</td>
    </tr>
    {% endfor %}
  </table>
  {% if delays %}
  <div class="section-title">🕐 正晚点</div>
  <table>
    <tr><th>#</th><th>车站</th><th>状态</th></tr>
    {% for d in delays %}
    <tr>
      <td style="color:#94a3b8;">{{ loop.index }}</td>
      <td>{{ d.station }}</td>
      <td class="{{ d.status_class }}">{{ d.status_text }}</td>
    </tr>
    {% endfor %}
  </table>
  {% endif %}
  <div class="footer">数据支持：RailGo</div>
</div>
"""

TMPL_SEGMENT = """
<div class="card">
  <div class="title">
    🚄 {{ train_num }}
    <span class="badge">区间</span>
  </div>
  <div style="display:flex; align-items:center; gap:12px; font-size:15px; margin-bottom:16px; padding:10px 14px; background:#f0f9ff; border-radius:10px;">
    <span style="color:#2563eb;font-weight:700;">{{ dep_name }}</span>
    <span style="color:#94a3b8;">→</span>
    <span style="color:#dc2626;font-weight:700;">{{ arr_name }}</span>
    <span style="margin-left:auto; font-size:12px; color:#64748b;">全程 {{ total_dist }}km</span>
  </div>
  <div class="info-grid">
    <div class="info-item"><span class="label">路局</span><span class="value">{{ bureau }}</span></div>
    <div class="info-item"><span class="label">车型</span><span class="value">{{ car }}</span></div>
  </div>
  {% if exit_info %}
  <div class="section-title">🚪 检票口 / 站台（{{ dep_name }}）</div>
  <div style="display:flex; gap:24px; flex-wrap:wrap; margin-bottom:8px; font-size:13px;">
    {% if exit_info.platform %}<div><span style="color:#64748b;">站台：</span><strong>{{ exit_info.platform }}</strong></div>{% endif %}
    {% if exit_info.entrance %}<div><span style="color:#64748b;">检票口：</span><strong>{{ exit_info.entrance }}</strong></div>{% endif %}
    {% if exit_info.exit_door %}<div><span style="color:#64748b;">出站口：</span><strong>{{ exit_info.exit_door }}</strong></div>{% endif %}
  </div>
  {% endif %}
  <div class="section-title">📋 区间时刻表</div>
  <table>
    <tr><th>#</th><th>车站</th><th>到达</th><th>出发</th><th>停时</th><th>里程</th></tr>
    {% for s in timetable %}
    <tr>
      <td style="color:#94a3b8;">{{ loop.index }}</td>
      <td class="{{ s.row_class }}">{{ s.station }}</td>
      <td>{{ s.arrive }}</td>
      <td>{{ s.depart }}</td>
      <td>{% if s.stop > 0 %}<span class="stop-badge">停{{ s.stop }}分</span>{% else %}-{% endif %}</td>
      <td>{{ s.dist }}km</td>
    </tr>
    {% endfor %}
  </table>
  {% if delays %}
  <div class="section-title">🕐 区间正晚点</div>
  <table>
    <tr><th>车站</th><th>状态</th></tr>
    {% for d in delays %}
    <tr>
      <td>{{ d.station }}</td>
      <td class="{{ d.status_class }}">{{ d.status_text }}</td>
    </tr>
    {% endfor %}
  </table>
  {% endif %}
  <div class="footer">数据支持：RailGo</div>
</div>
"""

TMPL_STS = """
<div class="card">
  <div class="title">
    🚉 站到站查询
    <span class="badge">{{ count }}趟</span>
  </div>
  <div style="display:flex; align-items:center; gap:10px; font-size:14px; color:#64748b; margin-bottom:16px;">
    <span style="color:#2563eb;font-weight:600;">{{ from_name }}</span> → <span style="color:#dc2626;font-weight:600;">{{ to_name }}</span>
    <span style="margin-left:auto;">{{ date }}</span>
  </div>
  {% for t in trains %}
  <div class="train-card">
    <div class="train-num">{{ t.number }}</div>
    <div class="train-meta">{{ t.type }} · {{ t.bureau }} · {{ t.car }}</div>
    <div class="train-route">
      {{ t.from_station }} {{ t.from_depart }} → {{ t.to_station }} {{ t.to_arrive }}{{ t.day_str }}
      <span style="margin-left:12px; color:#64748b;">耗时 {{ t.pass_time }}</span>
    </div>
  </div>
  {% endfor %}
  <div class="footer">数据支持：RailGo</div>
</div>
"""

TMPL_STATION = """
<div class="card">
  <div class="title">
    🏢 {{ name }}
    <span class="badge">{{ telecode }}</span>
  </div>
  <div class="info-grid">
    <div class="info-item"><span class="label">路局</span><span class="value">{{ bureau }}</span></div>
    <div class="info-item"><span class="label">所属</span><span class="value">{{ belong }}</span></div>
    <div class="info-item"><span class="label">城市</span><span class="value">{{ city }}</span></div>
    <div class="info-item"><span class="label">省份</span><span class="value">{{ province }}</span></div>
    {% if types %}
    <div class="info-item" style="grid-column:1/3;"><span class="label">类型</span><span class="value">{{ types }}</span></div>
    {% endif %}
  </div>
  <div class="section-title">🚄 途经列车（共{{ train_count }}趟）</div>
  <div style="font-size:13px; line-height:2;">
    {% for batch in trains_batch %}
    <div>{% for t in batch %}<span class="station-tag">{{ t }}</span> {% endfor %}</div>
    {% endfor %}
  </div>
  <div class="footer">数据支持：RailGo</div>
</div>
"""

TMPL_LUCKY = """
<div class="card" style="text-align:center;">
  <div style="font-size:48px; margin-bottom:8px;">🎲</div>
  <div class="title" style="justify-content:center;">随机车次</div>
  <div style="font-size:28px; font-weight:800; color:#0f172a; margin:12px 0;">{{ number }}</div>
  <div style="font-size:18px; color:#334155; margin:8px 0;">
    <span style="color:#2563eb;">{{ from_name }}</span>
    <span style="color:#94a3b8; margin:0 12px;">→</span>
    <span style="color:#dc2626;">{{ to_name }}</span>
  </div>
  <div style="font-size:14px; color:#64748b; margin-top:4px;">{{ depart_time }} 出发</div>
  <div class="footer">数据支持：RailGo</div>
</div>
"""

TMPL_DELAY = """
<div class="card">
  <div class="title">
    🕐 正晚点
    <span class="badge">{{ train_num }}</span>
  </div>
  <table>
    <tr><th>#</th><th>车站</th><th>状态</th></tr>
    {% for d in delays %}
    <tr>
      <td style="color:#94a3b8;">{{ loop.index }}</td>
      <td><strong>{{ d.station }}</strong></td>
      <td class="{{ d.status_class }}">{{ d.status_text }}</td>
    </tr>
    {% endfor %}
  </table>
  <div class="footer">数据支持：RailGo</div>
</div>
"""

def _wrap_tmpl(body: str) -> str:
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{BASE_CSS}</style></head><body>{body}</body></html>"

def _status_class(status: str) -> str:
    if status == "正点": return "status-on"
    if status == "晚点": return "status-late"
    if status == "早点": return "status-early"
    return ""

def _status_text(status: str, delay_time: int) -> str:
    return f"{status} {delay_time}分" if delay_time > 0 else status

@register(
    "astrbot_plugin_Railway_Information_Inquiry",
    "yingruochu",
    "多功能查询插件，集成 RailGo 铁路信息查询（车次/区间/站到站/车站/正晚点/随机车次）与 UAPI 全能接口（天气/农历/节假日/翻译/词典/IP/QQ/GitHub/热榜/今日人品/Minecraft 等 44+ 功能）",
    "1.0.0",
    "https://github.com/yingzhengxun/astrbot_plugin_Railway_Information_Inquiry",
)
class RailwayInfoPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # ── 通用 HTTP 方法 ──────────────────────────────────

    async def _fetch_json(self, base_url: str, endpoint: str, params: dict = None):
        url = f"{base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as resp:
                    if resp.status != 200:
                        logger.error(f"API 请求失败: {url} status={resp.status}")
                        return None
                    return await resp.json()
        except Exception as e:
            logger.error(f"API 请求异常: {url} {e}")
            return None

    async def _post_json(self, base_url: str, endpoint: str, data: dict = None, params: dict = None):
        url = f"{base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, params=params, timeout=15) as resp:
                    if resp.status != 200:
                        logger.error(f"API 请求失败: {url} status={resp.status}")
                        return None
                    ct = resp.headers.get("Content-Type", "")
                    if "application/json" in ct:
                        return await resp.json()
                    return await resp.text()
        except Exception as e:
            logger.error(f"API 请求异常: {url} {e}")
            return None

    async def _fetch_v1(self, endpoint: str, params: dict = None):
        return await self._fetch_json(API_BASE, endpoint, params)

    async def _fetch_v2(self, endpoint: str, params: dict = None):
        return await self._fetch_json(V2_API_BASE, endpoint, params)

    async def _fetch_uapi(self, endpoint: str, params: dict = None):
        return await self._fetch_json(UAPI_BASE, endpoint, params)

    async def _post_uapi(self, endpoint: str, data: dict = None, params: dict = None):
        return await self._post_json(UAPI_BASE, endpoint, data, params)

    async def _name_to_telecode(self, name: str) -> str | None:
        data = await self._fetch_v1("/api/station/preselect", {"keyword": name})
        if not data:
            return None
        for station in data:
            if station.get("name") == name:
                return station.get("telecode")
        return data[0].get("telecode")

    def _parse_args(self, event: AstrMessageEvent):
        text = event.message_str.strip()
        parts = text.split()
        return parts[1:] if len(parts) > 1 else []

    def _uapi_plain(self, title: str, items: list) -> str:
        lines = [title, "━" * 30]
        for k, v in items:
            if v is not None and v != "" and v != []:
                lines.append(f"{k}: {v}")
        lines.append("")
        lines.append("数据支持：UAPI")
        return "\n".join(lines)

    async def _render_img(self, tmpl: str, data: dict) -> str:
        html = _wrap_tmpl(tmpl)
        options = {"full_page": True, "scale": "css"}
        return await self.html_render(html, data, options=options)

    # ══════════════════════════════════════════════════════
    #  铁路信息命令
    # ══════════════════════════════════════════════════════

    @filter.command("车次查询")
    async def train_query(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args:
            yield event.plain_result("请提供车次号，例如：/车次查询 G1")
            return
        train = args[0]
        yield event.plain_result("正在查询车次信息，请稍候...")
        data, main_data, delay_data = await asyncio.gather(
            self._fetch_v1("/api/train/query", {"train": train}),
            self._fetch_v2("/api/v2/getTrainMain", {"trainNum": train}),
            self._fetch_v2("/api/v2/getTrainDelayAll", {"trainNum": train}),
        )
        if not data:
            yield event.plain_result("查询失败，请检查车次号是否正确。")
            return
        train_num = data.get("numberFull", [train])[0]
        timetable_raw = data.get("timetable", [])
        rundays = None
        if main_data and isinstance(main_data, dict):
            mr = main_data.get("data", {}).get("rundays")
            if mr: rundays = f"{mr[0]} ~ {mr[-1]} 共{len(mr)}天"
        if not rundays:
            r = data.get("rundays", [])
            if r: rundays = f"{r[0]} ~ {r[-1]} 共{len(r)}天"
        exit_info = None; exit_station = ""
        if timetable_raw:
            first = timetable_raw[0]; tc = first.get("stationTelecode", "")
            if tc:
                ed = await self._fetch_v2("/api/v2/getExit", {"trainNum": train, "stationTelecode": tc})
                if ed and isinstance(ed, dict):
                    ei = ed.get("data")
                    if ei:
                        exit_info = {"platform": ei.get("platform",""), "entrance": "、".join(ei.get("entrance",[])), "exit_door": "、".join(ei.get("exit",[]))}
                        exit_station = first.get("station","")
        timetable = []
        for s in timetable_raw:
            d = s.get("day", 0)
            timetable.append({"station": s.get("station",""), "arrive": s.get("arrive",""), "depart": s.get("depart",""), "stop": s.get("stopTime",0), "dist": s.get("distance",0), "day_label": f"第{d+1}日" if d > 0 else ""})
        delays = []
        if delay_data and isinstance(delay_data, dict):
            raw = delay_data.get("data")
            if raw:
                for d in raw:
                    st = d.get("delayStatus",""); dt = d.get("delayTime",0)
                    delays.append({"station": d.get("stationName",""), "status_text": _status_text(st, dt), "status_class": _status_class(st)})
        url = await self._render_img(TMPL_TRAIN_QUERY, {
            "train_num": train_num, "train_type": data.get("type",""), "bureau": data.get("bureauName",""),
            "car": data.get("car",""), "car_owner": data.get("carOwner",""), "runner": data.get("runner",""),
            "rundays": rundays or "", "exit_info": exit_info, "exit_station": exit_station,
            "timetable": timetable, "delays": delays})
        yield event.image_result(url)

    @filter.command("区间查询")
    async def train_segment(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if len(args) < 3:
            yield event.plain_result("请提供车次号、出发站和到达站，例如：/区间查询 G1 北京南 上海")
            return
        train, dep_name, arr_name = args[0], args[1], args[2]
        yield event.plain_result("正在查询区间信息，请稍候...")
        data, delay_data = await asyncio.gather(
            self._fetch_v1("/api/train/query", {"train": train}),
            self._fetch_v2("/api/v2/getTrainDelayAll", {"trainNum": train}))
        if not data:
            yield event.plain_result("查询失败，请检查车次号是否正确。"); return
        tt = data.get("timetable", [])
        if not tt:
            yield event.plain_result("该车次暂无时刻表数据。"); return
        dp = ap = -1
        for i, s in enumerate(tt):
            if s.get("station") == dep_name: dp = i
            if s.get("station") == arr_name: ap = i
        if dp == -1: yield event.plain_result(f"未找到出发站「{dep_name}」"); return
        if ap == -1: yield event.plain_result(f"未找到到达站「{arr_name}」"); return
        if dp >= ap: yield event.plain_result(f"出发站必须在到达站之前。"); return
        seg = tt[dp:ap+1]; ds = seg[0]; dtc = ds.get("stationTelecode","")
        ei = None
        if dtc:
            ed = await self._fetch_v2("/api/v2/getExit", {"trainNum": train, "stationTelecode": dtc})
            if ed and isinstance(ed, dict):
                eid = ed.get("data")
                if eid: ei = {"platform": eid.get("platform",""), "entrance": "、".join(eid.get("entrance",[])), "exit_door": "、".join(eid.get("exit",[]))}
        td = seg[-1].get("distance",0) - seg[0].get("distance",0)
        tbl = []
        for s in seg:
            sn = s.get("station",""); rc = "seg-start" if sn == dep_name else ("seg-end" if sn == arr_name else "")
            dd = s.get("day",0)
            tbl.append({"station": sn, "arrive": s.get("arrive",""), "depart": s.get("depart",""), "stop": s.get("stopTime",0), "dist": s.get("distance",0), "row_class": rc, "day_label": f"第{dd+1}日" if dd > 0 else ""})
        sds = []
        if delay_data and isinstance(delay_data, dict):
            raw = delay_data.get("data")
            if raw:
                ss = {s.get("station") for s in seg}
                for d in raw:
                    sn = d.get("stationName","")
                    if sn in ss:
                        st = d.get("delayStatus",""); dt = d.get("delayTime",0)
                        sds.append({"station": sn, "status_text": _status_text(st, dt), "status_class": _status_class(st)})
        url = await self._render_img(TMPL_SEGMENT, {
            "train_num": data.get("numberFull",[train])[0], "dep_name": dep_name, "arr_name": arr_name,
            "total_dist": td, "bureau": data.get("bureauName",""), "car": data.get("car",""),
            "exit_info": ei, "timetable": tbl, "delays": sds})
        yield event.image_result(url)

    @filter.command("站到站")
    async def station_to_station(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if len(args) < 3:
            yield event.plain_result("请提供出发站名称、到达站名称和日期，例如：/站到站 北京南 上海 20251009"); return
        fn, tn, date = args[0], args[1], args[2]
        yield event.plain_result("正在查询车站电报码...")
        ft = await self._name_to_telecode(fn); tt = await self._name_to_telecode(tn)
        if not ft: yield event.plain_result(f"未找到车站「{fn}」"); return
        if not tt: yield event.plain_result(f"未找到车站「{tn}」"); return
        raw = await self._fetch_v1("/api/train/sts_query", {"from": ft, "to": tt, "date": date})
        if not raw: yield event.plain_result("查询失败"); return
        trains = []
        for t in raw:
            tb = t.get("timetable",[]); fp = t.get("fromPos",0); tp = t.get("toPos",0); dd = t.get("dayDiff",0)
            trains.append({"number": t.get("number",""), "type": t.get("type",""), "bureau": t.get("bureauName",""), "car": t.get("car",""),
                "from_station": tb[fp].get("station","") if fp < len(tb) else "", "to_station": tb[tp].get("station","") if tp < len(tb) else "",
                "from_depart": t.get("fromDepart",""), "to_arrive": t.get("toArrive",""), "pass_time": t.get("passTime",""), "day_str": f"+{dd}" if dd > 0 else ""})
        url = await self._render_img(TMPL_STS, {"from_name": fn, "to_name": tn, "date": date, "count": len(trains), "trains": trains})
        yield event.image_result(url)

    @filter.command("车站查询")
    async def station_query(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供车站名称，例如：/车站查询 新余北"); return
        sn = " ".join(args)
        yield event.plain_result("正在查询车站电报码...")
        tc = await self._name_to_telecode(sn)
        if not tc: yield event.plain_result(f"未找到车站「{sn}」"); return
        res = await self._fetch_v1("/api/station/query", {"telecode": tc})
        if not res or "data" not in res: yield event.plain_result("查询失败"); return
        info = res["data"]; trains = info.get("trainList",[]); batches = [trains[i:i+10] for i in range(0, len(trains), 10)]
        url = await self._render_img(TMPL_STATION, {
            "name": info.get("name",""), "telecode": tc, "bureau": info.get("bureau",""), "belong": info.get("belong",""),
            "city": info.get("city",""), "province": info.get("province",""), "types": ", ".join(info.get("type",[])),
            "train_count": len(trains), "trains_batch": batches})
        yield event.image_result(url)

    @filter.command("随机选取车次")
    async def lucky_train(self, event: AstrMessageEvent):
        data = await self._fetch_v1("/api/lucky")
        if not data: yield event.plain_result("获取失败"); return
        url = await self._render_img(TMPL_LUCKY, {"number": data.get("number",""), "from_name": data.get("fromStation",{}).get("name",""), "to_name": data.get("toStation",{}).get("name",""), "depart_time": data.get("departTime","")})
        yield event.image_result(url)

    @filter.command("车次正晚点")
    async def train_delay(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供车次号，例如：/车次正晚点 G1"); return
        tn = args[0]
        data = await self._fetch_v2("/api/v2/getTrainDelayAll", {"trainNum": tn})
        if not data or not isinstance(data, dict): yield event.plain_result("查询失败"); return
        raw = data.get("data")
        if not raw: yield event.plain_result("查询失败"); return
        delays = []
        for d in raw:
            st = d.get("delayStatus",""); dt = d.get("delayTime",0)
            delays.append({"station": d.get("stationName",""), "status_text": _status_text(st, dt), "status_class": _status_class(st)})
        url = await self._render_img(TMPL_DELAY, {"train_num": tn, "delays": delays})
        yield event.image_result(url)

    # ══════════════════════════════════════════════════════
    #  天气类
    # ══════════════════════════════════════════════════════

    @filter.command("天气")
    async def uapi_weather(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        city = args[0] if args else None
        params = {"extended": "true", "forecast": "true", "indices": "true"}
        if city: params["city"] = city
        data = await self._fetch_uapi("/misc/weather", params)
        if not data: yield event.plain_result("查询失败"); return
        items = [("城市", f"{data.get('province','')} {data.get('city','')} {data.get('district','')}"),
            ("天气", data.get("weather","")), ("温度", f"{data.get('temperature','')}℃（体感 {data.get('feels_like','')}℃）"),
            ("风向", data.get("wind_direction","")), ("风力", data.get("wind_power","")), ("湿度", data.get("humidity","")),
            ("能见度", data.get("visibility","")), ("气压", data.get("pressure","")), ("紫外线", data.get("uv","")),
            ("AQI", f"{data.get('aqi','')}（{data.get('aqi_category','')}）"), ("报告时间", data.get("report_time",""))]
        if data.get("forecast"):
            items.append(("",""))
            for f in data["forecast"]:
                items.append((f"{f.get('date','')}", f"{f.get('weather','')} {f.get('min_temp','')}~{f.get('max_temp','')}℃"))
        yield event.plain_result(self._uapi_plain(f"天气查询 - {city or '当前位置'}", items))

    @filter.command("历史天气")
    async def uapi_weather_history(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if len(args) < 1: yield event.plain_result("请提供城市名，例如：/历史天气 北京"); return
        city = args[0]; params = {"city": city, "days": 7}
        if len(args) >= 2: params["start_date"] = args[1]
        if len(args) >= 3: params["end_date"] = args[2]
        data = await self._fetch_uapi("/misc/weather-history", params)
        if not data: yield event.plain_result("查询失败"); return
        items = [("城市", f"{data.get('province','')} {data.get('city','')}")]
        if isinstance(data, dict) and "data" in data:
            for d in data["data"]:
                items.append(("","")); items.append((d.get("date",""), f"{d.get('weather','')} {d.get('min_temp','')}~{d.get('max_temp','')}℃ 降雨:{d.get('rain','')}mm"))
        yield event.plain_result(self._uapi_plain(f"历史天气 - {city}", items))

    @filter.command("世界时间")
    async def uapi_worldtime(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供城市名，例如：/世界时间 Tokyo"); return
        data = await self._fetch_uapi("/misc/worldtime", {"city": args[0]})
        if not data: yield event.plain_result("查询失败"); return
        yield event.plain_result(self._uapi_plain(f"世界时间 - {args[0]}", [("时区", data.get("timezone","")), ("日期时间", data.get("datetime",""))]))

    @filter.command("农历")
    async def uapi_lunar(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        params = {}
        if args: params["ts"] = args[0]
        data = await self._fetch_uapi("/misc/lunartime", params)
        if not data: yield event.plain_result("查询失败"); return
        items = [("公历", f"{data.get('year','')}-{data.get('month','')}-{data.get('day','')}"),
            ("星期", data.get("weekday_cn","")), ("农历", f"{data.get('lunar_year_name','')}{data.get('lunar_month_name','')}{data.get('lunar_day_name','')}"),
            ("生肖", data.get("zodiac","")), ("干支", f"{data.get('ganzhi_year','')}年 {data.get('ganzhi_month','')}月 {data.get('ganzhi_day','')}日"),
            ("节气", data.get("solar_term","无")), ("节日", "、".join(data.get("festivals",[])) if data.get("festivals") else "无")]
        yield event.plain_result(self._uapi_plain("农历查询", items))

    @filter.command("节假日")
    async def uapi_holiday(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        params = {}
        if args:
            if len(args[0]) == 4: params["year"] = args[0]
            elif len(args[0]) == 7: params["month"] = args[0]
            else: params["date"] = args[0]
        data = await self._fetch_uapi("/misc/holiday-calendar", params)
        if not data: yield event.plain_result("查询失败"); return
        items = []
        if data.get("summary"):
            s = data["summary"]
            items.append(("统计", f"共{s.get('total_days','')}天 周末{s.get('weekend_days','')}天 工作日{s.get('workdays','')}天 休息{s.get('rest_days','')}天"))
        if data.get("holidays"):
            for h in data["holidays"]:
                items.append(("","")); items.append((h.get("name",""), f"{h.get('start_date','')} ~ {h.get('end_date','')} {h.get('duration','')}天"))
        items.append(("","")); items.append(("说明", "输入 /节假日 2025 查看全年\n/节假日 2025-10 查看当月\n/节假日 2025-10-01 查看当日"))
        yield event.plain_result(self._uapi_plain("节假日", items))

    @filter.command("日期差")
    async def uapi_date_diff(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if len(args) < 2: yield event.plain_result("请提供两个日期，例如：/日期差 2025-01-01 2025-12-31"); return
        data = await self._post_uapi("/misc/date-diff", {"start_date": args[0], "end_date": args[1]})
        if not data: yield event.plain_result("计算失败"); return
        yield event.plain_result(self._uapi_plain("日期差", [(k, v) for k, v in data.items() if v is not None]))

    # ══════════════════════════════════════════════════════
    #  日常类
    # ══════════════════════════════════════════════════════

    @filter.command("每日单词")
    async def uapi_daily_word(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        params = {"count": 1, "example": "true", "phonetic": "true", "define": "true"}
        if args: params["category"] = args[0]
        data = await self._fetch_uapi("/daily/word", params)
        if not data: yield event.plain_result("获取失败"); return
        words = data if isinstance(data, list) else data.get("data", [data])
        items = []
        for w in words:
            items.append(("单词", w.get("word",""))); items.append(("音标", w.get("phonetic","")))
            if w.get("definition"): items.append(("释义", w.get("definition","")))
            if w.get("example"): items.append(("例句", w.get("example","")))
            items.append(("",""))
        yield event.plain_result(self._uapi_plain("每日单词", items))

    @filter.command("每日新闻")
    async def uapi_daily_news(self, event: AstrMessageEvent):
        url = f"{UAPI_BASE}/daily/news-image"
        yield event.image_result(url)

    @filter.command("一言")
    async def uapi_saying(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        params = {}
        if args: params["scene"] = args[0]
        data = await self._fetch_uapi("/saying/random", params)
        if not data: yield event.plain_result("获取失败"); return
        it = data.get("item", data); content = it.get("content", it.get("saying", "")); source = it.get("source", it.get("from", ""))
        yield event.plain_result(self._uapi_plain("一言", [("内容", content), ("出处", source)]))

    # ══════════════════════════════════════════════════════
    #  网络类（排除 myip）
    # ══════════════════════════════════════════════════════

    @filter.command("IP查询")
    async def uapi_ipinfo(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供 IP 地址，例如：/IP查询 8.8.8.8"); return
        data = await self._fetch_uapi("/network/ipinfo", {"ip": args[0]})
        if not data: yield event.plain_result("查询失败"); return
        items = [("IP", data.get("ip","")), ("位置", data.get("region","")), ("运营商", data.get("isp","")),
            ("归属", data.get("llc","")), ("ASN", data.get("asn","")), ("纬度", data.get("latitude","")), ("经度", data.get("longitude",""))]
        yield event.plain_result(self._uapi_plain(f"IP查询 - {args[0]}", items))

    @filter.command("域名查询")
    async def uapi_whois(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供域名，例如：/域名查询 example.com"); return
        data = await self._fetch_uapi("/network/whois", {"domain": args[0], "format": "json"})
        if not data: yield event.plain_result("查询失败"); return
        raw = data.get("data", data.get("whois", data))
        if isinstance(raw, str):
            yield event.plain_result(self._uapi_plain(f"WHOIS - {args[0]}", [("信息", raw[:1000])])); return
        yield event.plain_result(self._uapi_plain(f"WHOIS - {args[0]}", [(k, v) for k, v in raw.items() if v is not None and v != ""]))

    @filter.command("Ping")
    async def uapi_ping(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供主机名或 IP，例如：/Ping google.com"); return
        params = {"host": args[0], "count": 4}
        if len(args) > 1:
            try: params["count"] = int(args[1])
            except ValueError: pass
        data = await self._fetch_uapi("/network/ping", params)
        if not data: yield event.plain_result("Ping 失败"); return
        items = [("主机", data.get("host","")), ("在线", "是" if data.get("alive") else "否"),
            ("平均延迟", f"{data.get('avg_time','')}ms"), ("最小延迟", f"{data.get('min_time','')}ms"),
            ("最大延迟", f"{data.get('max_time','')}ms"), ("丢包率", f"{data.get('packet_loss','')}%"),
            ("发送/接收", f"{data.get('transmitted','')}/{data.get('received','')}")]
        yield event.plain_result(self._uapi_plain(f"Ping - {args[0]}", items))

    @filter.command("URL检测")
    async def uapi_urlstatus(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供 URL，例如：/URL检测 https://example.com"); return
        data = await self._fetch_uapi("/network/urlstatus", {"url": args[0]})
        if not data: yield event.plain_result("检测失败"); return
        items = [("URL", data.get("url","")), ("最终 URL", data.get("final_url","")),
            ("状态码", data.get("status_code","")), ("可访问", "是" if data.get("ok") else "否"),
            ("响应时间", f"{data.get('response_time','')}ms"), ("内容类型", data.get("content_type",""))]
        yield event.plain_result(self._uapi_plain("URL检测", items))

    @filter.command("微信域名")
    async def uapi_wxdomain(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供域名，例如：/微信域名 example.com"); return
        data = await self._fetch_uapi("/network/wxdomain", {"domain": args[0]})
        if not data: yield event.plain_result("检测失败"); return
        blocked = data.get("blocked", data.get("normal")); st = "已封禁" if blocked else "正常"
        yield event.plain_result(self._uapi_plain(f"微信域名检测 - {args[0]}", [("域名", data.get("domain","")), ("状态", st)]))

    # ══════════════════════════════════════════════════════
    #  社交类
    # ══════════════════════════════════════════════════════

    @filter.command("QQ用户")
    async def uapi_qq_user(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供 QQ 号，例如：/QQ用户 10001"); return
        data = await self._fetch_uapi("/social/qq-userinfo", {"qq": args[0]})
        if not data: yield event.plain_result("查询失败"); return
        items = [("QQ", data.get("qq","")), ("昵称", data.get("nickname","")),
            ("性别", data.get("sex","")), ("年龄", data.get("age","")),
            ("QID", data.get("qid","")), ("等级", data.get("qq_level","")),
            ("位置", data.get("location","")), ("注册时间", data.get("reg_time","")),
            ("VIP", "是" if data.get("is_vip") else "否"), ("SVIP", "是" if data.get("is_svip") else "否"),
            ("VIP等级", data.get("vip_level",""))]
        yield event.plain_result(self._uapi_plain(f"QQ用户 - {args[0]}", items))

    @filter.command("QQ群")
    async def uapi_qq_group(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供群号，例如：/QQ群 123456"); return
        data = await self._fetch_uapi("/social/qq-groupinfo", {"group_id": args[0]})
        if not data: yield event.plain_result("查询失败"); return
        items = [("群号", data.get("group_id","")), ("群名", data.get("group_name","")),
            ("简介", data.get("group_memo","")), ("成员数", data.get("member_count","")),
            ("最大成员", data.get("max_member_count","")), ("群等级", data.get("group_level","")),
            ("创建时间", data.get("create_time",""))]
        yield event.plain_result(self._uapi_plain(f"QQ群 - {args[0]}", items))

    # ══════════════════════════════════════════════════════
    #  GitHub
    # ══════════════════════════════════════════════════════

    @filter.command("GitHub")
    async def uapi_github(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供 GitHub 用户名，例如：/GitHub torvalds"); return
        params = {"username": args[0], "pinned": "true", "repos": "true", "repos_limit": 5}
        data = await self._fetch_uapi("/github/user", params)
        if not data: yield event.plain_result("查询失败"); return
        items = [("用户名", data.get("login","")), ("名称", data.get("name","")), ("简介", data.get("bio","")),
            ("公司", data.get("company","")), ("位置", data.get("location","")), ("博客", data.get("blog","")),
            ("仓库", data.get("public_repos","")), ("关注者", data.get("followers","")), ("关注", data.get("following",""))]
        if data.get("pinned_repositories"):
            items.append(("","")); items.append(("Pinned", "、".join(r.get("name","") for r in data["pinned_repositories"])))
        yield event.plain_result(self._uapi_plain(f"GitHub - {args[0]}", items))

    # ══════════════════════════════════════════════════════
    #  词典类
    # ══════════════════════════════════════════════════════

    @filter.command("词典")
    async def uapi_dictionary(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供英文单词，例如：/词典 hello"); return
        data = await self._fetch_uapi("/dictionary/lookup", {"word": args[0]})
        if not data: yield event.plain_result("查询失败"); return
        items = [("单词", data.get("word",""))]
        if data.get("phonetics"):
            p = data["phonetics"]
            items.append(("英式音标", p.get("uk",{}).get("phonetic",""))); items.append(("美式音标", p.get("us",{}).get("phonetic","")))
        if data.get("definitions"):
            for d in data["definitions"]:
                items.append(("","")); items.append((d.get("pos",""), "；".join(d.get("definitions",[]))))
        if data.get("examples"):
            items.append(("",""))
            for e in data["examples"][:3]: items.append(("例句", e.get("sentence","")))
        yield event.plain_result(self._uapi_plain(f"词典 - {args[0]}", items))

    @filter.command("单词发音")
    async def uapi_audio(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供英文单词，例如：/单词发音 hello"); return
        accent = args[1] if len(args) > 1 else "us"
        url = f"{UAPI_BASE}/dictionary/audio?word={args[0]}&accent={accent}"
        yield event.image_result(url)

    # ══════════════════════════════════════════════════════
    #  文本处理类
    # ══════════════════════════════════════════════════════

    @filter.command("翻译")
    async def uapi_translate(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if len(args) < 2: yield event.plain_result("请提供目标语言和文本，例如：/翻译 en 你好世界"); return
        target = args[0]; text = " ".join(args[1:])
        data = await self._post_uapi("/text/translate", {"text": text}, {"target": target})
        if not data: yield event.plain_result("翻译失败"); return
        result = data.get("translated", data.get("result", data.get("text", "")))
        yield event.plain_result(self._uapi_plain("翻译", [("原文", text), ("译文", result)]))

    @filter.command("MD5")
    async def uapi_md5(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供文本，例如：/MD5 hello"); return
        text = " ".join(args)
        data = await self._fetch_uapi("/text/md5", {"text": text})
        if not data: yield event.plain_result("计算失败"); return
        md5_val = data.get("md5", data.get("result", data.get("data", "")))
        yield event.plain_result(self._uapi_plain("MD5 哈希", [("原文", text), ("MD5", md5_val)]))

    @filter.command("MD5校验")
    async def uapi_md5_verify(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if len(args) < 2: yield event.plain_result("请提供文本和 MD5 值，例如：/MD5校验 hello 5d41402abc4b2a76b9719d911017c592"); return
        text, md5_val = args[0], args[1]
        data = await self._post_uapi("/text/md5-verify", {"text": text, "md5": md5_val})
        if not data: yield event.plain_result("校验失败"); return
        match = data.get("match", data.get("verified", data.get("result")))
        yield event.plain_result(self._uapi_plain("MD5 校验", [("原文", text), ("MD5", md5_val), ("匹配", "是" if match else "否")]))

    @filter.command("Base64编码")
    async def uapi_b64_encode(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供文本，例如：/Base64编码 hello"); return
        text = " ".join(args)
        data = await self._post_uapi("/text/base64-encode", {"text": text})
        if not data: yield event.plain_result("编码失败"); return
        result = data.get("base64", data.get("result", data.get("encoded", "")))
        yield event.plain_result(self._uapi_plain("Base64 编码", [("原文", text), ("Base64", result)]))

    @filter.command("Base64解码")
    async def uapi_b64_decode(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供 Base64 字符串，例如：/Base64解码 aGVsbG8="); return
        text = " ".join(args)
        data = await self._post_uapi("/text/base64-decode", {"base64": text})
        if not data: yield event.plain_result("解码失败"); return
        result = data.get("text", data.get("result", data.get("decoded", "")))
        yield event.plain_result(self._uapi_plain("Base64 解码", [("Base64", text), ("原文", result)]))

    @filter.command("Markdown转HTML")
    async def uapi_md2html(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供 Markdown 文本，例如：/Markdown转HTML # 标题"); return
        text = " ".join(args)
        data = await self._post_uapi("/text/markdown-to-html", {"text": text, "format": "json"})
        if not data: yield event.plain_result("转换失败"); return
        html = data.get("html", data.get("result", data.get("data", "")))
        yield event.plain_result(self._uapi_plain("Markdown 转 HTML", [("Markdown", text[:200] + ("..." if len(text) > 200 else "")), ("HTML", html[:500] + ("..." if len(html) > 500 else ""))]))

    @filter.command("Markdown转PDF")
    async def uapi_md2pdf(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供 Markdown 文本，例如：/Markdown转PDF # 标题"); return
        text = " ".join(args)
        if len(text) > 500: yield event.plain_result("文本过长，请控制在 500 字以内。"); return
        data = await self._post_uapi("/text/markdown-to-pdf", {"text": text})
        if not data: yield event.plain_result("转换失败（可能需要 Token 认证）。"); return
        yield event.plain_result("转换成功，请通过 API 返回的 PDF 链接查看。")

    # ══════════════════════════════════════════════════════
    #  图像类
    # ══════════════════════════════════════════════════════

    @filter.command("必应每日")
    async def uapi_bing(self, event: AstrMessageEvent):
        data = await self._fetch_uapi("/image/bing-daily")
        if not data: yield event.plain_result("获取失败"); return
        img_url = data.get("image_url", data.get("image_url_1080", ""))
        if img_url: yield event.image_result(img_url)
        items = [("标题", data.get("title","")), ("描述", data.get("description","")), ("版权", data.get("copyright","")), ("日期", data.get("date",""))]
        yield event.plain_result(self._uapi_plain("必应每日壁纸", items))

    @filter.command("二维码")
    async def uapi_qrcode(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供要生成二维码的文本或网址，例如：/二维码 https://example.com"); return
        text = " ".join(args)
        yield event.image_result(f"{UAPI_BASE}/image/qrcode?text={text}&size=300")

    @filter.command("摸头")
    async def uapi_motou(self, event: AstrMessageEvent):
        yield event.image_result(f"{UAPI_BASE}/image/motou")

    @filter.command("随机图片")
    async def uapi_random_image(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        url = f"{UAPI_BASE}/random/image"
        if args:
            parts = args[0].split("x")
            if len(parts) == 2: url += f"?width={parts[0]}&height={parts[1]}"
        yield event.image_result(url)

    @filter.command("答案之书")
    async def uapi_answerbook(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请输入你的问题，例如：/答案之书 今天适合出门吗？"); return
        q = " ".join(args)
        data = await self._fetch_uapi("/answerbook/ask", {"question": q})
        if not data: yield event.plain_result("获取失败"); return
        yield event.plain_result(self._uapi_plain("答案之书", [("问题", q), ("答案", data.get("title_zh", data.get("description_zh", "")))]))

    # ══════════════════════════════════════════════════════
    #  杂项
    # ══════════════════════════════════════════════════════

    @filter.command("热榜")
    async def uapi_hotboard(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供热榜类型，例如：/热榜 weibo"); return
        params = {"type": args[0], "limit": 20}
        if len(args) > 1: params["limit"] = args[1]
        data = await self._fetch_uapi("/misc/hotboard", params)
        if not data: yield event.plain_result("获取失败"); return
        lst = data.get("list", data.get("data", []))
        items = []
        for i, item in enumerate(lst[:20], 1):
            title = item.get("title", item.get("name", "")); hot = item.get("hot", item.get("heat", ""))
            items.append((f"#{i}", f"{title} {'['+str(hot)+']' if hot else ''}"))
        yield event.plain_result(self._uapi_plain(f"热榜 - {args[0]}", items))

    @filter.command("今日人品")
    async def uapi_fortune(self, event: AstrMessageEvent):
        data = await self._fetch_uapi("/misc/randomnumber", {"min": 0, "max": 100, "count": 1})
        if not data: yield event.plain_result("获取失败"); return
        score = data[0] if isinstance(data, list) else data.get("data", [0])[0]
        if score >= 90: comment = "今天运气爆棚！"
        elif score >= 70: comment = "今天运气不错～"
        elif score >= 50: comment = "今天运气一般般"
        elif score >= 30: comment = "今天运气不太好"
        else: comment = "今天诸事不宜，小心谨慎"
        yield event.plain_result(self._uapi_plain("今日人品", [("评分", f"{score}/100"), ("评价", comment)]))

    @filter.command("电影票房")
    async def uapi_box_office(self, event: AstrMessageEvent):
        data = await self._fetch_uapi("/misc/movie-box-office")
        if not data: yield event.plain_result("获取失败"); return
        items = []
        market = data.get("market", {})
        if market:
            items.append(("大盘", f"{market.get('box_office','')} 元")); items.append(("场次", f"{market.get('show_count','')} 场"))
            items.append(("人次", f"{market.get('view_count','')} 人")); items.append(("",""))
        for m in data.get("list", data.get("data", []))[:15]:
            items.append((f"#{m.get('rank','')} {m.get('movie_name','')}", f"票房 {m.get('box_office','')} 累计 {m.get('sum_box_office','')} 排片 {m.get('show_count','')} 场"))
        yield event.plain_result(self._uapi_plain("电影票房", items))

    # ══════════════════════════════════════════════════════
    #  Minecraft 类
    # ══════════════════════════════════════════════════════

    @filter.command("MC服务器")
    async def uapi_mc_server(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供服务器地址，例如：/MC服务器 mc.hypixel.net"); return
        params = {"host": args[0]}
        if len(args) > 1: params["port"] = args[1]
        data = await self._fetch_uapi("/game/minecraft/serverstatus", params)
        if not data: yield event.plain_result("查询失败"); return
        items = [("地址", data.get("ip","")), ("端口", data.get("port","")), ("在线", "是" if data.get("online") else "否"),
            ("版本", data.get("version","")), ("玩家", f"{data.get('players','')}/{data.get('max_players','')}"), ("MOTD", data.get("motd_clean",""))]
        yield event.plain_result(self._uapi_plain(f"MC服务器 - {args[0]}", items))

    @filter.command("MC玩家")
    async def uapi_mc_user(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供玩家名，例如：/MC玩家 Notch"); return
        data = await self._fetch_uapi("/game/minecraft/userinfo", {"username": args[0]})
        if not data: yield event.plain_result("查询失败"); return
        items = [("UUID", data.get("uuid","")), ("当前名称", data.get("username",""))]
        if data.get("name_history"):
            names = [f"{n.get('name','')} ({n.get('changed_to_at','')})" for n in data["name_history"]]
            items.append(("曾用名", "、".join(names)))
        if data.get("skin_url"): items.append(("皮肤", data.get("skin_url","")))
        if data.get("cape_url"): items.append(("披风", data.get("cape_url","")))
        yield event.plain_result(self._uapi_plain(f"MC玩家 - {args[0]}", items))

    @filter.command("MC版本")
    async def uapi_mc_version(self, event: AstrMessageEvent):
        data = await self._fetch_uapi("/game/minecraft/version")
        if not data: yield event.plain_result("获取失败"); return
        items = [(k, v) for k, v in (data if isinstance(data, dict) else {"版本": str(data)}).items()]
        yield event.plain_result(self._uapi_plain("Minecraft 最新版本", items))

    @filter.command("MCMod")
    async def uapi_mc_mods(self, event: AstrMessageEvent):
        args = self._parse_args(event)
        if not args: yield event.plain_result("请提供搜索关键词，例如：/MCMod jei"); return
        params = {"query": args[0], "limit": 5, "enrich": "true"}
        if len(args) > 1: params["source"] = args[1]
        data = await self._fetch_uapi("/game/minecraft/mods", params)
        if not data: yield event.plain_result("搜索失败"); return
        results = data if isinstance(data, list) else data.get("data", data.get("results", []))
        items = []
        for mod in results[:10]:
            name = mod.get("name", mod.get("title","")); author = mod.get("author", mod.get("author_name",""))
            ver = mod.get("version", mod.get("latest_version","")); desc = mod.get("description", mod.get("summary",""))
            items.append((name, f"{author} | {ver} | {desc[:80]}"))
        yield event.plain_result(self._uapi_plain(f"MCMod 搜索 - {args[0]}", items))

    async def terminate(self):
        pass

