const AR={new:"جديد",preparing:"قيد التحضير",ready:"جاهز",delivered:"تم التسليم",cancelled:"ملغي"};
const $=s=>document.querySelector(s),m=$("#m"),fmt=n=>Math.round(n).toLocaleString("en-US")+" ج.م";
async function api(p,o={}){const r=await fetch("/api"+p,{method:o.method||"GET",headers:{"Content-Type":"application/json"},body:o.body?JSON.stringify(o.body):undefined});const d=await r.json();if(!r.ok)throw new Error(d.error||"خطأ");return d}
const tag=s=>`<span class="tag s-${s}">${AR[s]}</span>`;
const day=d=>d.slice(5).replace("-","/");
const chart=a=>`<div class="chart chartw">${a.map(x=>`<div title="${fmt(x.revenue)}" style="height:${Math.max(2,x.revenue/Math.max(...a.map(y=>y.revenue))*100)}%"><i>${day(x.day)}</i></div>`).join("")}</div>`;
function msg(t,ok=true){const e=document.createElement("div");e.className="msg "+(ok?"ok":"bad");e.id="flash";e.textContent=t;m.prepend(e);setTimeout(()=>e.remove(),4000)}
const pages={
async dash(){const[s,d,t]=await Promise.all([api("/reports/summary"),api("/reports/daily"),api("/reports/top-products")]);
m.innerHTML=`<h2>لوحة المعلومات</h2><div class="kpis">
<div class="card kpi"><span>الإيرادات</span><b>${fmt(s.revenue)}</b></div><div class="card kpi"><span>عدد الطلبات</span><b>${s.orders}</b></div>
<div class="card kpi"><span>متوسط الطلب</span><b>${fmt(s.avg_order)}</b></div><div class="card kpi"><span>طلبات مفتوحة</span><b>${s.open_orders}</b></div><div class="card kpi"><span>العملاء</span><b>${s.customers}</b></div></div>
<div class="grid2"><div class="card"><b>الإيرادات اليومية (آخر 14 يوم)</b>${chart(d)}</div>
<div class="card"><b>الأعلى إيرادا</b><table><tr><th>المنتج</th><th>الكمية</th></tr>${t.map(x=>`<tr><td>${x.name}</td><td>${x.qty}</td></tr>`).join("")}</table></div></div>`},
async orders(){const st=window._st||"",q=window._q||"";const o=await api(`/orders?status=${st}&q=${encodeURIComponent(q)}`);
m.innerHTML=`<h2>الطلبات</h2><div class="bar"><select id="st"><option value="">كل الحالات</option>${Object.entries(AR).map(([k,v])=>`<option value="${k}" ${k==st?"selected":""}>${v}</option>`).join("")}</select>
<input id="q" placeholder="بحث باسم العميل أو رقم الطلب" value="${q}"><button id="go" class="sec">بحث</button><button id="add">+ طلب جديد</button></div><div id="form"></div>
<table><tr><th>#</th><th>العميل</th><th>الإجمالي</th><th>الحالة</th><th>التاريخ</th><th>تغيير الحالة</th></tr>
${o.map(x=>`<tr><td>${x.id}</td><td>${x.customer_name}</td><td>${fmt(x.total)}</td><td>${tag(x.status)}</td><td>${x.created_at.slice(0,16).replace("T"," ")}</td>
<td><select data-id="${x.id}" class="chg">${Object.entries(AR).map(([k,v])=>`<option value="${k}" ${k==x.status?"selected":""}>${v}</option>`).join("")}</select></td></tr>`).join("")||"<tr><td colspan=6>لا توجد طلبات</td></tr>"}</table>`;
$("#st").onchange=e=>{window._st=e.target.value;show("orders")};$("#go").onclick=()=>{window._q=$("#q").value;show("orders")};
document.querySelectorAll(".chg").forEach(s=>s.onchange=async e=>{try{await api("/orders/"+s.dataset.id,{method:"PATCH",body:{status:s.value}});await show("orders");msg("تم تحديث حالة الطلب #"+s.dataset.id)}catch(x){msg(x.message,false)}});
$("#add").onclick=async()=>{const[c,p]=await Promise.all([api("/customers"),api("/products")]);
$("#form").innerHTML=`<div class="card" style="margin-bottom:12px"><div class="bar"><select id="nc">${c.map(x=>`<option value="${x.id}">${x.name}</option>`).join("")}</select></div>
${p.map(x=>`<div class="bar"><span style="width:140px">${x.name} (${x.price})</span><input type="number" min="0" max="50" value="0" data-p="${x.id}" class="qty" style="width:70px"></div>`).join("")}
<button id="save">حفظ الطلب</button></div>`;
$("#save").onclick=async()=>{const items=[...document.querySelectorAll(".qty")].filter(i=>+i.value>0).map(i=>({product_id:+i.dataset.p,qty:+i.value}));
try{const r=await api("/orders",{method:"POST",body:{customer_id:+$("#nc").value,items}});window._st="";await show("orders");msg("تم إنشاء الطلب #"+r.id)}catch(x){msg(x.message,false)}}}},
async customers(){const c=await api("/customers");
m.innerHTML=`<h2>العملاء</h2><div class="card bar" style="margin-bottom:12px"><input id="n" placeholder="الاسم"><input id="p" placeholder="الموبايل 01xxxxxxxxx"><input id="a" placeholder="المنطقة"><button id="sv">إضافة عميل</button></div>
<table><tr><th>الاسم</th><th>الموبايل</th><th>المنطقة</th><th>الطلبات</th><th>إجمالي الإنفاق</th></tr>${c.map(x=>`<tr><td>${x.name}</td><td>${x.phone}</td><td>${x.area||""}</td><td>${x.orders_count}</td><td>${fmt(x.spent)}</td></tr>`).join("")}</table>`;
$("#sv").onclick=async()=>{try{await api("/customers",{method:"POST",body:{name:$("#n").value,phone:$("#p").value,area:$("#a").value}});await show("customers");msg("تمت إضافة العميل")}catch(x){msg(x.message,false)}}},
async reports(){const[d,t,b]=await Promise.all([api("/reports/daily"),api("/reports/top-products"),api("/reports/by-status")]);
m.innerHTML=`<h2>التقارير</h2><div class="card" style="margin-bottom:12px"><b>الإيرادات اليومية</b>${chart(d)}</div><div class="grid2">
<div class="card"><b>أعلى 5 منتجات بالإيراد</b><table><tr><th>المنتج</th><th>الكمية</th><th>الإيراد</th></tr>${t.map(x=>`<tr><td>${x.name}</td><td>${x.qty}</td><td>${fmt(x.revenue)}</td></tr>`).join("")}</table></div>
<div class="card"><b>الطلبات حسب الحالة</b><table>${b.map(x=>`<tr><td>${tag(x.status)}</td><td>${x.n}</td></tr>`).join("")}</table></div></div>`}};
async function show(p){document.querySelectorAll("nav a").forEach(a=>a.classList.toggle("on",a.dataset.p==p));try{await pages[p]()}catch(e){m.innerHTML=`<div class="msg bad">${e.message}</div>`}}
document.querySelectorAll("nav a").forEach(a=>a.onclick=()=>show(a.dataset.p));show("dash");
