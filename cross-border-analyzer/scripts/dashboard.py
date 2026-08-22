#!/usr/bin/env python3
"""从评分后的 CSV 生成交互式 HTML 仪表盘（纯本地，无外部依赖）。

用法:
    python3 dashboard.py <scored.csv> <dashboard.html>
"""

import argparse
import csv
import json
import os
import sys


TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>跨境商品分析仪表盘</title>
<style>
:root { --brand:#111827; --accent:#2563eb; --warn:#d97706; --danger:#dc2626; --ok:#16a34a; }
* { box-sizing:border-box; }
body { font-family:-apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; margin:0; background:#f3f4f6; color:#111827; }
header { background:var(--brand); color:#fff; padding:18px 24px; }
header h1 { margin:0; font-size:20px; }
header p { margin:4px 0 0; opacity:.8; font-size:13px; }
.wrap { max-width:1200px; margin:20px auto; padding:0 16px; }
.filters { background:#fff; border-radius:10px; padding:14px 18px; margin-bottom:18px;
  display:flex; flex-wrap:wrap; gap:16px; align-items:center; box-shadow:0 1px 3px rgba(0,0,0,.08); }
.filters label { font-size:13px; color:#374151; display:flex; flex-direction:column; gap:4px; }
.filters input, .filters select { padding:5px 8px; border:1px solid #d1d5db; border-radius:6px; font-size:13px; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:14px; margin-bottom:18px; }
.card { background:#fff; border-radius:10px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,.08); }
.card .num { font-size:26px; font-weight:700; margin-top:4px; }
.card .lbl { font-size:12px; color:#6b7280; }
.panel { background:#fff; border-radius:10px; padding:18px; margin-bottom:18px; box-shadow:0 1px 3px rgba(0,0,0,.08); }
.panel h2 { margin:0 0 12px; font-size:15px; }
svg { width:100%; height:auto; }
.tbl { width:100%; border-collapse:collapse; font-size:13px; }
.tbl th,.tbl td { padding:8px 10px; border-bottom:1px solid #e5e7eb; text-align:left; white-space:nowrap; }
.tbl th { background:#f9fafb; position:sticky; top:0; }
.tag { display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; margin-right:4px; }
.tag.new { background:#dcfce7; color:#15803d; }
.tag.red { background:#fee2e2; color:#b91c1c; }
.tag.comm { background:#fef3c7; color:#b45309; }
.tag.pot { background:#dbeafe; color:#1d4ed8; }
.tag.care { background:#f3e8ff; color:#7e22ce; }
</style>
</head>
<body>
<header>
  <h1>跨境商品分析仪表盘</h1>
  <p id="meta"></p>
</header>
<div class="wrap">
  <div class="filters">
    <label>价格区间($) <input type="range" id="priceMax" min="0" max="200" value="200">
      <span id="priceLbl">0 – 200</span></label>
    <label>最低周期销量 <input type="number" id="minSales" value="0" min="0" style="width:90px"></label>
    <label>品类
      <select id="catSel"><option value="">全部</option></select>
    </label>
    <label>排序
      <select id="sortSel">
        <option value="potential">综合潜力</option>
        <option value="viability">可做性</option>
        <option value="market_heat">市场热度</option>
        <option value="sales7">周期销量</option>
        <option value="price">价格</option>
      </select>
    </label>
  </div>

  <div class="cards">
    <div class="card"><div class="lbl">商品数</div><div class="num" id="cN"></div></div>
    <div class="card"><div class="lbl">价格中位数($)</div><div class="num" id="cP"></div></div>
    <div class="card"><div class="lbl">周期销量合计</div><div class="num" id="cS"></div></div>
    <div class="card"><div class="lbl">平均潜力分</div><div class="num" id="cA"></div></div>
  </div>

  <div class="panel"><h2>价格分布</h2><svg id="hist" viewBox="0 0 600 220"></svg></div>
  <div class="panel"><h2>周期销量 vs 价格（气泡大小 = 综合潜力）</h2><svg id="scatter" viewBox="0 0 600 300"></svg></div>
  <div class="panel"><h2>Top 20 综合潜力</h2><svg id="bars" viewBox="0 0 600 420"></svg></div>
  <div class="panel"><h2>商品列表</h2><div style="max-height:480px;overflow:auto">
    <table class="tbl" id="grid"><thead><tr>
      <th>排名</th><th>图片</th><th>商品</th><th>价格($)</th><th>周期销量</th><th>佣金率</th>
      <th>热度</th><th>可做性</th><th>潜力</th><th>标记</th>
    </tr></thead><tbody></tbody></table>
  </div></div>
</div>
<script>
const DATA = __DATA__;
const ROWS = DATA.rows;
document.getElementById('meta').textContent =
  '来源: ' + DATA.source + ' | 生成: ' + DATA.generated + ' | 共 ' + ROWS.length + ' 个商品';

const cats = [...new Set(ROWS.map(r => r.category || '未知'))].sort();
const catSel = document.getElementById('catSel');
cats.forEach(c => { const o = document.createElement('option'); o.value = c; o.textContent = c; catSel.appendChild(o); });

const fmt = (v, d=1) => v == null || isNaN(v) ? '-' : Number(v).toLocaleString('zh-CN', {maximumFractionDigits: d});
const esc = s => (s == null ? '' : String(s)).replace(/&/g,'&amp;').replace(/</g,'&lt;')
  .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const tagCls = m => m.includes('暴涨新星') ? 'new' : m.includes('价格战红海') ? 'red' :
  m.includes('高佣') ? 'comm' : m.includes('高潜力') ? 'pot' : m.includes('谨慎') ? 'care' : '';
const svgNS = 'http://www.w3.org/2000/svg';

function filtered() {
  const pm = +document.getElementById('priceMax').value;
  const ms = +document.getElementById('minSales').value || 0;
  const cat = document.getElementById('catSel').value;
  const sort = document.getElementById('sortSel').value;
  let arr = ROWS.filter(r =>
    (+r.price || 0) <= pm && (+r.sales7 || 0) >= ms && (!cat || r.category === cat));
  arr.sort((a, b) => (+b[sort] || 0) - (+a[sort] || 0));
  return arr;
}

function renderCards(arr) {
  const ps = arr.map(r => +r.price).filter(v => !isNaN(v));
  const ss = arr.map(r => +r.sales7).filter(v => !isNaN(v));
  const pot = arr.map(r => +r.potential).filter(v => !isNaN(v));
  document.getElementById('cN').textContent = arr.length;
  document.getElementById('cP').textContent = ps.length ? fmt(ps.sort((a,b)=>a-b)[Math.floor(ps.length/2)]) : '-';
  document.getElementById('cS').textContent = fmt(ss.reduce((a,b)=>a+b,0), 0);
  document.getElementById('cA').textContent = pot.length ? fmt(pot.reduce((a,b)=>a+b,0)/pot.length) : '-';
}

function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); }
function axis(el, x0, y0, x1, y1) {
  const l = document.createElementNS(svgNS,'line');
  l.setAttribute('x1',x0); l.setAttribute('y1',y0); l.setAttribute('x2',x1); l.setAttribute('y2',y1);
  l.setAttribute('stroke','#9ca3af'); el.appendChild(l);
}

function renderHist(arr) {
  const el = document.getElementById('hist'); clear(el);
  const W=600, H=220, pad=40;
  axis(el, pad, H-pad, W-pad, H-pad);
  const bins = new Array(10).fill(0);
  arr.forEach(r => { const p = +r.price; if (!isNaN(p)) bins[Math.min(9, Math.floor(p/10))]++; });
  const max = Math.max(1, ...bins);
  bins.forEach((c,i) => {
    const h = (H-pad-10) * c / max;
    const x = pad + i * (W-2*pad) / 10 + 3, w = (W-2*pad)/10 - 6;
    const rect = document.createElementNS(svgNS,'rect');
    rect.setAttribute('x',x); rect.setAttribute('y',H-pad-h); rect.setAttribute('width',w);
    rect.setAttribute('height',h); rect.setAttribute('fill','#2563eb'); rect.setAttribute('rx',2);
    el.appendChild(rect);
    const t = document.createElementNS(svgNS,'text');
    t.setAttribute('x',x+w/2); t.setAttribute('y',H-pad+14); t.setAttribute('text-anchor','middle');
    t.setAttribute('font-size','10'); t.textContent = i*10+'-'+(i*10+9); el.appendChild(t);
  });
}

function renderScatter(arr) {
  const el = document.getElementById('scatter'); clear(el);
  const W=600, H=300, pad=42;
  const maxP = Math.max(1, ...arr.map(r=>+r.price).filter(v=>!isNaN(v)));
  const maxS = Math.max(1, ...arr.map(r=>+r.sales7).filter(v=>!isNaN(v)));
  axis(el, pad, H-pad, W-pad, H-pad);
  arr.slice(0,120).forEach(r => {
    const x = pad + (+r.price||0)/maxP*(W-2*pad);
    const y = H-pad - (+r.sales7||0)/maxS*(H-2*pad);
    const c = document.createElementNS(svgNS,'circle');
    c.setAttribute('cx',x); c.setAttribute('cy',y); c.setAttribute('r', 2.5 + (+r.potential||0)/25);
    c.setAttribute('fill', (+r.viability||0) >= 60 ? '#16a34a' : '#d1d5db');
    el.appendChild(c);
  });
}

function renderBars(arr) {
  const el = document.getElementById('bars'); clear(el);
  const W=600, H=420, pad=40;
  const top = arr.slice(0,20);
  const max = Math.max(1, ...top.map(r=>+r.potential||0));
  const bh = (H-2*pad-10) / Math.max(1, top.length);
  top.forEach((r,i) => {
    const w = (W-2*pad) * (+r.potential||0) / max;
    const y = pad + i*bh;
    const rect = document.createElementNS(svgNS,'rect');
    rect.setAttribute('x',pad); rect.setAttribute('y',y+2); rect.setAttribute('width',w);
    rect.setAttribute('height',bh-6); rect.setAttribute('fill','#2563eb'); rect.setAttribute('rx',2);
    el.appendChild(rect);
    const t = document.createElementNS(svgNS,'text');
    t.setAttribute('x',pad+4); t.setAttribute('y',y+bh/2+4); t.setAttribute('font-size','11');
    t.setAttribute('fill','#fff'); t.textContent = (r.name||'未知').slice(0,16);
    el.appendChild(t);
    const v = document.createElementNS(svgNS,'text');
    v.setAttribute('x',pad+w+6); v.setAttribute('y',y+bh/2+4); v.setAttribute('font-size','11');
    v.textContent = fmt(r.potential); el.appendChild(v);
  });
}

function renderGrid(arr) {
  const tb = document.querySelector('#grid tbody'); clear(tb);
  arr.slice(0,200).forEach((r,i) => {
    const tr = document.createElement('tr');
    const tags = (r.markers||'').split(';').filter(Boolean).map(m =>
      '<span class="tag '+tagCls(m)+'">'+m+'</span>').join('');
    const img = r.image ? '<img src="'+esc(r.image)+'" width="56" height="56" '+
      'style="object-fit:cover;border-radius:6px" loading="lazy" alt="">' : '-';
    tr.innerHTML = '<td>'+(i+1)+'</td><td>'+img+'</td><td>'+esc(r.name||'-')+'</td><td>'+fmt(r.price)+
      '</td><td>'+fmt(r.sales7,0)+'</td><td>'+fmt(r.commission)+'%</td><td>'+fmt(r.market_heat)+
      '</td><td>'+fmt(r.viability)+'</td><td>'+fmt(r.potential)+'</td><td>'+tags+'</td>';
    tb.appendChild(tr);
  });
}

function renderAll() {
  const arr = filtered();
  renderCards(arr); renderHist(arr); renderScatter(arr); renderBars(arr); renderGrid(arr);
}

document.getElementById('priceMax').addEventListener('input', e => {
  document.getElementById('priceLbl').textContent = '0 – ' + e.target.value;
  renderAll();
});
['minSales','catSel','sortSel'].forEach(id => document.getElementById(id).addEventListener('input', renderAll));
renderAll();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="生成交互式仪表盘")
    ap.add_argument("input", help="评分后 CSV")
    ap.add_argument("output", help="输出 dashboard.html")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        sys.exit(f"输入文件不存在: {args.input}")
    with open(args.input, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit("输入为空，无法生成仪表盘")

    from datetime import datetime
    payload = {
        "rows": rows,
        "source": os.path.basename(args.input),
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    html = TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成: {args.output}")


if __name__ == "__main__":
    main()
