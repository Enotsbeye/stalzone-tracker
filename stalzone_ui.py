"""Страница программы: разметка, стили и скрипт. Сервер в stalzone_app.py подставляет __TOKEN__.

Вид «мох и янтарь»: графит с зеленцой, янтарь артефакта — для действий, цвета редкости — как в игре.
Главное на экране — картинка предмета в «ячейке инвентаря», подсвеченной цветом его редкости,
и одно предложение по-русски: что купить, за сколько продашь и насколько это надёжно."""

UI_HTML = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>STALZONE Трекер</title>
<style>
@font-face{font-family:"Golos";src:url(/font/golos.woff2) format("woff2");font-weight:400 900;font-display:swap}
@font-face{font-family:"Unbounded";src:url(/font/unbounded.woff2) format("woff2");font-weight:200 900;font-display:swap}
/* светлая — бумага с зеленцой, тёмная — Зона в сумерках; янтарь — действия, зелёный — деньги */
:root{
  --bg:#ecefe9; --surface:#fafbf8; --surface-2:#f1f3ee; --sunk:#e3e7df; --line:#d7dcd3; --line-2:#c2c8bd;
  --text:#1b201c; --muted:#58615a; --faint:#8a9288;
  --amber:#efb03a; --amber-ink:#2a1d03; --amber-text:#8a5d04; --amber-soft:rgba(239,176,58,.2);
  --good:#1b8546; --good-soft:rgba(27,133,70,.11); --warn:#9a6300; --warn-soft:rgba(239,176,58,.2);
  --bad:#bf3f2d; --bad-soft:rgba(191,63,45,.1);
  --q0:#8a948a; --q1:#3c9f49; --q2:#2c79c8; --q3:#8b4dc9; --q4:#cc4239; --q5:#c9850c;
  --shadow:0 24px 60px rgba(30,42,32,.2);
  --font:"Golos","Segoe UI",system-ui,sans-serif; --display:"Unbounded","Golos","Segoe UI",sans-serif;
  color-scheme:light;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#151916; --surface:#1c201d; --surface-2:#232824; --sunk:#111412; --line:#2d332e; --line-2:#3b433d;
  --text:#e8ebe4; --muted:#a0a89c; --faint:#6c756a;
  --amber:#efb03a; --amber-ink:#2a1d03; --amber-text:#f2bd55; --amber-soft:rgba(239,176,58,.14);
  --good:#74d192; --good-soft:rgba(116,209,146,.12); --warn:#f2bd55; --warn-soft:rgba(242,189,85,.13);
  --bad:#f07e6c; --bad-soft:rgba(240,126,108,.12);
  --q0:#a6afa4; --q1:#6acc6d; --q2:#58a1ee; --q3:#b47bee; --q4:#ee6a60; --q5:#f1b33b;
  --shadow:0 24px 60px rgba(0,0,0,.5);
  color-scheme:dark;
}}
:root[data-theme="dark"]{
  --bg:#151916; --surface:#1c201d; --surface-2:#232824; --sunk:#111412; --line:#2d332e; --line-2:#3b433d;
  --text:#e8ebe4; --muted:#a0a89c; --faint:#6c756a;
  --amber:#efb03a; --amber-ink:#2a1d03; --amber-text:#f2bd55; --amber-soft:rgba(239,176,58,.14);
  --good:#74d192; --good-soft:rgba(116,209,146,.12); --warn:#f2bd55; --warn-soft:rgba(242,189,85,.13);
  --bad:#f07e6c; --bad-soft:rgba(240,126,108,.12);
  --q0:#a6afa4; --q1:#6acc6d; --q2:#58a1ee; --q3:#b47bee; --q4:#ee6a60; --q5:#f1b33b;
  --shadow:0 24px 60px rgba(0,0,0,.5);
  color-scheme:dark;
}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--text);font:15px/1.5 var(--font);-webkit-font-smoothing:antialiased;overflow:hidden}
button,input,select,textarea{font:inherit;color:inherit}
[hidden]{display:none!important}
.num{font-variant-numeric:tabular-nums}
.muted{color:var(--muted)}
.small{font-size:12.5px}
:focus-visible{outline:2px solid var(--amber);outline-offset:2px}
.app{display:grid;grid-template-columns:212px minmax(0,1fr);height:100vh}

/* --- навигация --- */
.side{display:flex;flex-direction:column;gap:24px;padding:22px 12px 16px;background:var(--surface);border-right:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:11px;padding:0 8px}
.logo{width:36px;height:36px;border-radius:11px;display:grid;place-items:center;background:var(--amber);color:var(--amber-ink);flex:none}
.logo svg{width:18px;height:18px}
.brand b{display:block;font:650 14px/1.15 var(--display)}
.brand span{font-size:12.5px;color:var(--muted)}
.nav{display:flex;flex-direction:column;gap:2px}
.nav button{all:unset;cursor:pointer;display:flex;align-items:center;gap:12px;padding:9px 10px;border-radius:10px;color:var(--muted);font-weight:500}
.nav button:hover{background:var(--surface-2);color:var(--text)}
.nav button.on{background:var(--surface-2);color:var(--text);font-weight:650}
.nav button:focus-visible{outline:2px solid var(--amber)}
.nav svg{width:19px;height:19px;flex:none}
.nav .cnt{margin-left:auto;min-width:22px;padding:1px 7px;border-radius:20px;background:var(--amber);color:var(--amber-ink);font-size:12px;font-weight:700;text-align:center}
.nav .cnt.quiet{background:var(--sunk);color:var(--muted)}
.nav .cnt.ok{background:var(--good-soft);color:var(--good)}
.nav .cnt:empty{display:none}
.side-foot{margin-top:auto;padding:0 10px;font-size:12.5px;color:var(--muted)}
.side-foot b{color:var(--amber-text);font-weight:650}

/* --- шапка --- */
main{display:flex;flex-direction:column;min-width:0;height:100vh}
.top{display:flex;align-items:center;gap:16px;padding:20px 28px 10px}
.top h1{margin:0;font:600 21px/1.2 var(--display)}
.state{margin-left:auto;display:flex;align-items:center;gap:9px;font-size:14px;color:var(--muted);white-space:nowrap}
.dot{width:9px;height:9px;border-radius:50%;background:var(--faint);flex:none}
.dot.live{background:var(--good);animation:pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--good) 55%,transparent)}70%{box-shadow:0 0 0 8px transparent}100%{box-shadow:0 0 0 0 transparent}}
.run{all:unset;cursor:pointer;padding:10px 18px;border-radius:11px;font-weight:650;background:var(--amber);color:var(--amber-ink);white-space:nowrap}
.run:hover{filter:brightness(1.06)}
.run.stop{background:var(--surface);color:var(--text);box-shadow:inset 0 0 0 1px var(--line-2)}
.run:focus-visible{outline:2px solid var(--amber);outline-offset:2px}
.view{display:none;flex:1;min-height:0;overflow:auto;padding:6px 28px 28px}
.view.on{display:flex;flex-direction:column;gap:16px}
.view.on>*{flex-shrink:0}   /* иначе длинный список сжимается до высоты окна и обрезается — его не пролистать */

/* --- главное предложение --- */
.hero{display:flex;flex-direction:column;gap:3px;padding:2px 0 2px}
.hero h2{margin:0;font:650 23px/1.3 var(--font);letter-spacing:-.01em;text-wrap:balance}
.hero h2 .good{color:var(--good)}
.hero p{margin:0;color:var(--muted);max-width:76ch}
.progress{height:3px;border-radius:3px;background:var(--line);overflow:hidden;margin-top:10px;max-width:440px}
.progress i{display:block;height:100%;width:0;background:var(--amber);transition:width .4s}

/* --- поля и кнопки --- */
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.field{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:8px 12px;outline:none;min-width:0}
.field:focus{border-color:var(--amber)}
select.field{padding:8px 10px;cursor:pointer}
.search{width:200px}
.field.small{width:136px}
.spacer{flex:1}
.btn{all:unset;cursor:pointer;display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:10px;background:var(--surface);border:1px solid var(--line);font-size:14px;font-weight:600;white-space:nowrap}
.btn:hover{border-color:var(--line-2);background:var(--surface-2)}
.btn:focus-visible{outline:2px solid var(--amber);outline-offset:2px}
.btn.primary{background:var(--amber);color:var(--amber-ink);border-color:transparent}
.btn.primary:hover{filter:brightness(1.05)}
.btn.ghost{background:transparent;border-color:transparent;color:var(--muted)}
.btn.ghost:hover{color:var(--text);background:var(--surface-2)}
.btn.sm{padding:5px 10px;font-size:13px;border-radius:8px}
.btn.done{color:var(--good);border-color:color-mix(in srgb,var(--good) 40%,transparent);background:transparent}
.seg{display:flex;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:3px}
.seg button{all:unset;cursor:pointer;padding:5px 12px;border-radius:7px;color:var(--muted);font-weight:550;font-size:14px}
.seg button.on{background:var(--sunk);color:var(--text)}
.toggle{all:unset;cursor:pointer;font-size:14px;font-weight:550;padding:7px 13px;border-radius:20px;border:1px solid var(--line);background:var(--surface);color:var(--muted);white-space:nowrap}
.toggle:hover{border-color:var(--line-2);color:var(--text)}
.toggle.on{border-color:color-mix(in srgb,var(--amber) 60%,transparent);background:var(--amber-soft);color:var(--text)}
.toggle.rare.on{border-color:color-mix(in srgb,var(--q3) 55%,transparent);background:color-mix(in srgb,var(--q3) 14%,transparent)}
.check{display:inline-flex;align-items:center;gap:7px;font-size:14px;color:var(--muted);cursor:pointer}
.field.bare{border-color:transparent;background:transparent;padding-left:2px;font-weight:600;color:var(--text)}
.field.bare:hover{background:var(--surface)}
.btn.copy{background:transparent;color:var(--muted);border-color:transparent;padding:4px 8px}
.btn.copy:hover{color:var(--text);border-color:var(--line);background:var(--surface)}
.btn.copy svg{width:15px;height:15px}

/* --- ячейка предмета: картинка из базы игры, подсветка цветом редкости --- */
.slot{position:relative;flex:none;width:64px;height:64px;border-radius:14px;display:grid;place-items:center;
  background:radial-gradient(110% 80% at 50% 108%,color-mix(in srgb,var(--rc) 40%,transparent),transparent 72%),var(--sunk);
  box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--rc) 46%,transparent)}
.slot:before{content:attr(data-l);font:600 21px/1 var(--display);color:color-mix(in srgb,var(--rc) 78%,var(--text))}
.slot.ok:before{content:none}
.slot img{position:absolute;left:8%;top:8%;width:84%;height:84%;object-fit:contain}
.slot.sm{width:40px;height:40px;border-radius:10px}.slot.sm:before{font-size:14px}
.slot.xs{width:24px;height:24px;border-radius:7px}.slot.xs:before{font-size:10px}
.slot.lg{width:92px;height:92px;border-radius:18px}.slot.lg:before{font-size:30px}

/* --- находки --- */
.lots{display:flex;flex-direction:column;background:var(--surface);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.lots:empty{display:none}
.lot{display:grid;grid-template-columns:64px minmax(0,1fr) auto;gap:16px;align-items:center;padding:14px 18px;border-bottom:1px solid var(--line);cursor:pointer}
.lot:last-child{border-bottom:0}
.lot:hover{background:var(--surface-2)}
.lot.sel{background:var(--surface-2);box-shadow:inset 3px 0 0 var(--amber)}
.lot.mine{box-shadow:inset 3px 0 0 var(--good)}
.lot.old{opacity:.55}
.lot-title{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 10px}
.lot .n{font-weight:650;font-size:16px}
.lot-deal{margin-top:2px}
.lot-deal b{font-weight:650}
.lot-meta{margin-top:7px;display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;font-size:13.5px;color:var(--muted)}
.lot-side{display:flex;flex-direction:column;align-items:flex-end;gap:3px;text-align:right}
.near{margin-top:22px}
.near-head h3{margin:0 0 2px;font-size:15px;font-weight:650}
.near-head p{margin:0 0 10px}
.near-head a{color:inherit}
.near-list{display:flex;flex-direction:column;border:1px dashed var(--line-2);border-radius:14px;overflow:hidden}
.nr{display:grid;grid-template-columns:40px minmax(0,1fr) auto;gap:12px;align-items:center;padding:9px 14px;border-bottom:1px dashed var(--line)}
.nr:last-child{border-bottom:0}
.nr .n{font-weight:600}
.nr .why{font-size:13px;color:var(--warn)}
.nr-side{display:flex;flex-direction:column;align-items:flex-end;gap:2px;text-align:right;font-size:13.5px}
.nr-side b{font-weight:650}
.nr.gone{opacity:.5}
.lot-side .exp{color:var(--good);font-weight:600}
tr.sellrow td{padding-top:0;background:var(--surface-2);white-space:normal;text-align:left}
.sell{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;padding:8px 0 4px}
.sell .opts{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.opt{all:unset;cursor:pointer;display:flex;flex-direction:column;gap:1px;padding:5px 10px;border-radius:10px;border:1px solid var(--line);background:var(--surface);font-size:13px}
.opt:hover{border-color:var(--line-2)}
.opt span{color:var(--muted);font-size:12px}
.opt.best{box-shadow:inset 0 0 0 1px var(--amber)}
.ls{flex-basis:100%;font-size:13.5px;color:var(--muted)}
.ls.bad{color:var(--bad);font-weight:600}
.ls.good{color:var(--good)}
.acc{margin-top:16px}
.acc p{margin:0 0 10px}
.accrows{display:flex;flex-direction:column;border-top:1px solid var(--line)}
.accrows div{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:14px;padding:6px 0;border-bottom:1px solid var(--line);font-size:13.5px}
.neg{color:var(--bad)}
.pos{color:var(--good)}
table.craft td.profit,table.craft td.neg{font-size:15px}
.ylist{display:flex;flex-direction:column;gap:2px;margin-bottom:10px}
.yrow{display:flex;justify-content:space-between;gap:10px;padding:3px 0;border-bottom:1px dashed var(--line)}
.yrow .n{font-weight:550}
.skills{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 14px}
.skill{display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:14px}
.skill .field{width:84px;padding:5px 8px}
.advice{display:flex;flex-direction:column;gap:8px}
.adv{display:flex;flex-direction:column;gap:1px;font-size:14px}
.adv span{color:var(--muted)}
table.craft{table-layout:fixed}
table.craft td{vertical-align:top;white-space:normal}
table.craft td.num{white-space:nowrap}
table.craft th{white-space:normal}
table.craft th:nth-child(-n+2),table.craft td:nth-child(-n+2){text-align:left}
table.craft tr.loss{opacity:.6}
.noprice{color:var(--faint)}
.tag.bad{color:var(--bad);background:var(--bad-soft)}
.tag.excl{color:var(--amber-ink);background:var(--amber)}
.warncard{border-color:color-mix(in srgb,var(--bad) 45%,var(--line))}
.warncard h3{color:var(--bad)}
.nr.gone .n{text-decoration:line-through}
.lot-side .btn{margin-top:4px;margin-right:-8px}
.profit{font:600 19px/1.2 var(--display);color:var(--good);white-space:nowrap}
.neg{color:var(--bad);font-weight:650}
.grade{font-size:14px;font-weight:600}
.rk{font-size:13px;font-weight:650}
.tags{display:inline-flex;flex-wrap:wrap;gap:6px;align-items:center}
.tag{font-size:12px;font-weight:650;padding:1px 8px;border-radius:6px;background:var(--sunk);color:var(--muted);white-space:nowrap}
.tag.bid{color:var(--q2);background:color-mix(in srgb,var(--q2) 14%,transparent)}
.tag.rare{color:var(--q3);background:color-mix(in srgb,var(--q3) 15%,transparent)}
.tag.mine{color:var(--good);background:var(--good-soft)}
.tag.stale{color:var(--warn);background:var(--warn-soft)}
.tag.fresh{color:var(--amber-text);background:var(--amber-soft)}
.tag.cat{background:transparent;box-shadow:inset 0 0 0 1px var(--line);font-weight:550}
.chance{display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:650;padding:2px 10px 2px 8px;border-radius:20px;white-space:nowrap}
.chance:before{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}
.chance.hi,.cv.hi{color:var(--good)}.chance.hi{background:var(--good-soft)}
.chance.mid,.cv.mid{color:var(--warn)}.chance.mid{background:var(--warn-soft)}
.chance.lo,.cv.lo{color:var(--bad)}.chance.lo{background:var(--bad-soft)}
.chance.none{color:var(--muted);background:var(--sunk)}
.empty{display:grid;place-items:center;text-align:center;color:var(--muted);padding:56px 20px;background:var(--surface);border:1px dashed var(--line-2);border-radius:16px}
.empty h3{color:var(--text);margin:16px 0 4px;font-size:18px}
.empty div{max-width:52ch}
.empty.compact{padding:22px 20px}
.empty.compact .radar{display:none}
.empty.compact h3{margin-top:0;font-size:16px}
.radar{width:82px;height:82px;border-radius:50%;margin:auto;position:relative;overflow:hidden;
  background:radial-gradient(circle,var(--surface-2) 0 28%,transparent 29%),repeating-radial-gradient(circle,transparent 0 12px,var(--line) 13px 14px)}
.radar:after{content:"";position:absolute;inset:0;background:conic-gradient(from 0deg,color-mix(in srgb,var(--amber) 45%,transparent),transparent 70deg);animation:spin 3s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){.dot.live,.radar:after{animation:none}}

/* --- плашки сверху --- */
.note-bar{display:flex;align-items:center;gap:14px;background:var(--surface);border:1px solid color-mix(in srgb,var(--amber) 55%,transparent);border-radius:14px;padding:12px 16px}
.note-bar .ic{flex:none;width:30px;height:30px;border-radius:9px;display:grid;place-items:center;background:var(--amber);color:var(--amber-ink);font-weight:800}
.note-bar .tx{flex:1;min-width:0}
.note-bar .tx div{color:var(--muted);font-size:14px}
.note-bar .tx div b{color:var(--amber-text)}
.note-bar.good{border-color:color-mix(in srgb,var(--good) 55%,transparent)}
.note-bar.good .ic{background:var(--good);color:var(--surface)}
.onboard{background:var(--surface);border:1px solid color-mix(in srgb,var(--amber) 55%,transparent);border-radius:16px;padding:18px 20px}
.onboard h3{margin:0 0 4px;font-size:17px}
.steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:14px}
.step{background:var(--surface-2);border-radius:12px;padding:12px 14px}
.step b{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--amber);color:var(--amber-ink);font-size:12px;margin-right:6px}
.step p{margin:6px 0 10px;color:var(--muted);font-size:14px}

/* --- карточка находки справа --- */
.drawer{position:fixed;top:0;right:0;height:100vh;width:452px;max-width:100vw;background:var(--surface);border-left:1px solid var(--line);box-shadow:var(--shadow);transform:translateX(104%);transition:transform .22s ease;overflow:auto;z-index:20;padding:22px 24px 30px}
.drawer.on{transform:none}
@media (prefers-reduced-motion:reduce){.drawer{transition:none}}
.close{all:unset;cursor:pointer;float:right;width:32px;height:32px;border-radius:9px;display:grid;place-items:center;color:var(--muted);font-size:17px}
.close:hover{background:var(--surface-2);color:var(--text)}
.dhead{display:flex;gap:16px;align-items:center;margin-top:4px}
.dhead h2{margin:0;font:650 20px/1.25 var(--font)}
.bigprofit{font:600 30px/1.15 var(--display);color:var(--good);margin:20px 0 2px}
.calc{margin:16px 0 4px;border:1px solid var(--line);border-radius:12px;overflow:hidden}
.calc div{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 14px;border-bottom:1px solid var(--line)}
.calc small{display:block;color:var(--faint);font-size:12.5px}
.calc span:first-child{color:var(--muted)}
.calc div:last-child{border-bottom:0;background:var(--good-soft);font-weight:700;color:var(--good)}
.calc div:last-child span{color:var(--good)}
.sect{margin-top:22px}
.sect h3{margin:0 0 8px;font-size:15px;font-weight:650}
.cv{font-size:19px;font-weight:700}
.cv span{font-size:14px;font-weight:550;color:var(--muted);margin-left:6px}
.cbar{height:6px;background:var(--sunk);border-radius:6px;overflow:hidden;margin:9px 0 12px}
.cbar i{display:block;height:100%;border-radius:6px;background:currentColor}
.reasons{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:7px}
.reasons li{display:flex;gap:9px;font-size:14px}
.reasons li:before{content:"";flex:none;width:7px;height:7px;border-radius:50%;margin-top:8px;background:var(--faint)}
.reasons li.up:before{background:var(--good)}
.reasons li.down:before{background:var(--bad)}
.kv{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:5px 12px;font-size:13px;margin-top:12px;padding-top:10px;border-top:1px solid var(--line)}
.kv span:nth-child(odd){color:var(--muted)}
.kv span:nth-child(even){text-align:right;font-variant-numeric:tabular-nums}
.chart svg{display:block;width:100%;height:auto;overflow:visible}
.chart .cap{font-size:13px;color:var(--muted);margin-top:6px}
.facts{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:18px}
.fact{background:var(--surface-2);border-radius:12px;padding:10px 12px}
.fact .l{font-size:12.5px;color:var(--muted)}
.fact .v{font-weight:600;margin-top:2px}
.note{font-size:14px;color:var(--muted);background:var(--surface-2);border-radius:12px;padding:11px 13px;margin:12px 0 0}
.note.warn{background:var(--warn-soft);color:var(--text)}
.note.ok{background:var(--good-soft);color:var(--text)}
.buybox{display:flex;gap:8px;align-items:center;margin-top:18px}
.buybox .field{width:160px}
.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}

/* --- карточки разделов --- */
.grid2{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:16px;align-items:start}
.col{display:flex;flex-direction:column;gap:16px;min-width:0}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:18px 20px}
.card h3{margin:0 0 4px;font-size:16px;font-weight:650}
.card .sub{color:var(--muted);font-size:14px;margin-bottom:12px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0 10px}
.tabs button{all:unset;cursor:pointer;font-size:13.5px;padding:5px 11px;border-radius:20px;background:var(--surface-2);border:1px solid var(--line);color:var(--muted)}
.tabs button.on{background:var(--sunk);color:var(--text);border-color:var(--line-2)}
.tabs button span{color:var(--faint);margin-left:5px}
.results{max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:12px}
.res{display:flex;align-items:center;gap:10px;padding:7px 10px;border-bottom:1px solid var(--line)}
.res:last-child{border-bottom:0}
.res:hover{background:var(--surface-2)}
.res .n{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:550}
.star{all:unset;cursor:pointer;color:var(--faint);font-size:18px;line-height:1;padding:2px 4px}
.star:hover{color:var(--q3)}
.star.on{color:var(--q3)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.chip{display:flex;align-items:center;gap:7px;background:var(--surface-2);border:1px solid var(--line);border-radius:30px;padding:4px 6px 4px 5px}
.chip .star{font-size:15px;padding:0}
.chip > button:last-child{all:unset;cursor:pointer;width:20px;height:20px;border-radius:50%;display:grid;place-items:center;color:var(--muted);font-size:12px}
.chip > button:last-child:hover{background:var(--bad-soft);color:var(--bad)}
.catrow{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid var(--line)}
.catrow:last-of-type{border-bottom:0}
.catrow b{font-weight:600}
.catrow small{display:block;color:var(--muted);font-size:13px}
.art-head{display:grid}

/* --- настройки --- */
.form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;align-items:start}
.row{display:grid;grid-template-columns:minmax(0,1fr) 150px;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid var(--line)}
.row:last-child{border-bottom:0}
.row.wide{grid-template-columns:1fr}
.row.w2{grid-template-columns:minmax(0,1fr) 190px}
.row label{font-weight:550}
.row small{display:block;color:var(--muted);font-size:13px;font-weight:400}
.row .field{width:100%}
.switch{position:relative;width:42px;height:24px;justify-self:end}
.switch input{opacity:0;width:0;height:0;position:absolute}
.switch i{position:absolute;inset:0;background:var(--line-2);border-radius:20px;cursor:pointer;transition:.2s}
.switch i:before{content:"";position:absolute;width:18px;height:18px;left:3px;top:3px;background:#fff;border-radius:50%;transition:.2s}
.switch input:checked+i{background:var(--amber)}
.switch input:checked+i:before{transform:translateX(18px)}
.switch input:focus-visible+i{outline:2px solid var(--amber);outline-offset:2px}
.linkrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.savebar{position:sticky;bottom:-28px;display:flex;justify-content:flex-end;gap:10px;padding:14px 0 6px;background:linear-gradient(transparent,var(--bg) 40%)}
.row.flash{animation:flash 1.8s ease}
@keyframes flash{0%,55%{background:var(--amber-soft)}100%{background:transparent}}

/* --- покупки --- */
.tablewrap{background:var(--surface);border:1px solid var(--line);border-radius:16px;overflow:auto}
table{width:100%;border-collapse:collapse}
th{position:sticky;top:0;background:var(--surface);z-index:1;text-align:right;font-size:13px;font-weight:600;color:var(--muted);padding:11px 14px;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
tr:last-child td{border-bottom:0}
.item{display:flex;align-items:center;gap:12px}
.item .n{font-weight:600}
.item .tags{display:flex;margin-top:3px}
.item .when{display:block;font-size:12.5px;color:var(--faint);margin-top:2px}
.status{font-size:12px;font-weight:650;padding:1px 8px;border-radius:20px;white-space:nowrap}
.status.holding{color:var(--q2);background:color-mix(in srgb,var(--q2) 14%,transparent)}
.status.listed{color:var(--warn);background:var(--warn-soft)}
.status.sold{color:var(--good);background:var(--good-soft)}
.inline{display:flex;gap:6px;align-items:center;justify-content:flex-end}
.inline .field{width:120px;padding:5px 8px}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px 16px}
.kpi .l{font-size:13px;color:var(--muted)}
.kpi .v{font-size:21px;font-weight:700;margin-top:2px}
.kpi .v.good{color:var(--good)}
.kpi .s{font-size:12.5px;color:var(--faint)}

/* --- доступ --- */
.idrow{display:flex;align-items:center;gap:12px;margin:12px 0;flex-wrap:wrap}
.idrow b{font:600 20px/1.2 var(--display);letter-spacing:.04em;color:var(--amber-text)}
textarea.field.code{width:100%;min-height:74px;resize:vertical;font:12.5px/1.4 Consolas,"Cascadia Mono",monospace;word-break:break-all}
.issued{display:grid;grid-template-columns:minmax(0,1fr) auto auto auto;gap:4px 14px;font-size:14px;margin-top:10px;align-items:center}
.issued span{padding:7px 0;border-bottom:1px solid var(--line)}
.issued .act{display:flex;gap:6px;justify-content:flex-end}
.dotx{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--faint);margin-right:6px}
.dotx.on{background:var(--good)}
.howto ol{margin:8px 0 6px 18px;padding:0}
.howto li{margin:4px 0}
.howto code,#srvStatus code{background:var(--sunk);padding:1px 6px;border-radius:5px;font-size:13px}
.howto summary{cursor:pointer;color:var(--text);font-weight:600}

/* --- журнал --- */
.log{flex:1;background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:14px 18px;font-size:13.5px;line-height:1.65;overflow:auto;white-space:pre-wrap}
.log .t{color:var(--faint);font-variant-numeric:tabular-nums}
.log .e{color:var(--bad)}
.log .f{color:var(--good);font-weight:600}
.log .w{color:var(--warn)}

/* --- прочее --- */
.overlay{position:fixed;inset:0;z-index:50;display:grid;place-items:center;background:color-mix(in srgb,var(--bg) 94%,transparent);text-align:center}
.overlay h2{margin:14px 0 6px}
.lock{width:min(540px,92vw);text-align:left;background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:26px}
.lock h2{margin:12px 0 6px;font:600 20px/1.3 var(--display)}
.lock textarea.field.code{margin:10px 0 12px}
.toast{position:fixed;bottom:22px;left:50%;transform:translate(-50%,20px);background:var(--text);color:var(--surface);padding:11px 18px;border-radius:12px;opacity:0;transition:.25s;pointer-events:none;z-index:60;font-weight:550;max-width:min(560px,90vw)}
.toast.on{opacity:1;transform:translate(-50%,0)}
.toast.err{background:var(--bad);color:#fff}
::-webkit-scrollbar{width:11px;height:11px}
::-webkit-scrollbar-thumb{background:var(--line-2);border-radius:10px;border:3px solid var(--bg)}

@media (max-width:1180px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.steps{grid-template-columns:1fr}.form,.grid2{grid-template-columns:1fr}}
@media (max-width:980px){
  .app{grid-template-columns:64px minmax(0,1fr)}
  .side{padding:18px 8px}.brand div:last-child,.nav .lbl,.side-foot{display:none}.brand{justify-content:center;padding:0}
  .nav button{justify-content:center;position:relative}.nav .cnt{position:absolute;top:2px;right:2px;min-width:18px;padding:0 5px;font-size:11px}
  .lot{grid-template-columns:48px minmax(0,1fr)}.lot .slot{width:48px;height:48px}.lot-side{grid-column:2;align-items:flex-start;text-align:left}
}
</style>
</head>
<body>
<div class="app">
  <aside class="side">
    <div class="brand"><div class="logo"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l9 10-9 10-9-10z" opacity=".35"/><path d="M12 6.5l5 5.5-5 5.5-5-5.5z"/></svg></div><div><b>STALZONE</b><span>трекер аукциона</span></div></div>
    <nav class="nav">
      <button data-view="deals" class="on"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2M8.5 11.5l2 2 3.5-4"/></svg><span class="lbl">Находки</span><span class="cnt" id="cntDeals"></span></button>
      <button data-view="items"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><path d="M17 14v6M14 17h6"/></svg><span class="lbl">Предметы</span><span class="cnt quiet" id="cntItems"></span></button>
      <button data-view="buys"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 8h14l-1.2 11.2a2 2 0 01-2 1.8H8.2a2 2 0 01-2-1.8z"/><path d="M9 8V6a3 3 0 016 0v2"/><path d="M9.5 14l2 2 3.5-4"/></svg><span class="lbl">Мои покупки</span><span class="cnt ok" id="cntBuys"></span></button>
      <button data-view="craft"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3h6M10 3v6.2L4.8 18.4A1.8 1.8 0 006.4 21h11.2a1.8 1.8 0 001.6-2.6L14 9.2V3"/><path d="M7.5 15h9"/></svg><span class="lbl">Крафт</span></button>
      <button data-view="settings"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/></svg><span class="lbl">Настройки</span></button>
      <button data-view="access"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/></svg><span class="lbl">Доступ</span></button>
      <button data-view="log"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 6h14M5 12h14M5 18h9"/></svg><span class="lbl">Журнал</span></button>
    </nav>
    <div class="side-foot" id="modeLbl">Регион RU</div>
  </aside>

  <main>
    <header class="top">
      <h1 id="viewTitle">Находки</h1>
      <div class="state"><span class="dot" id="dot"></span><span id="stateTxt">Поиск остановлен</span></div>
      <button class="run" id="runBtn">Начать поиск</button>
    </header>

    <section class="view on" id="view-deals">
      <div class="note-bar good" id="updNote" hidden>
        <div class="ic">↑</div>
        <div class="tx"><b id="updTitle">Доступна новая версия</b><div id="updSub"></div></div>
        <button class="btn primary" id="updBtn">Обновить</button>
      </div>
      <div class="note-bar" id="demoNote" hidden>
        <div class="ic">!</div>
        <div class="tx"><b>Демо-режим: тестовые данные EXBO, а не настоящий аукцион</b><div id="demoNoteSub"></div></div>
        <button class="btn" id="demoOffBtn">Выключить в настройках</button>
      </div>
      <div class="onboard" id="onboard" hidden>
        <h3>Подключи доступ к API — это займёт пару минут</h3>
        <div class="muted">Без ключей трекер не видит аукцион. Ключи бесплатно выдаёт сама EXBO.</div>
        <div class="steps">
          <div class="step"><b>1</b>Подай заявку<p>Отправь /newapp боту EXBO и войди через свой аккаунт.</p><button class="btn" data-open="api_bot">Открыть @stalzone_api_bot</button></div>
          <div class="step"><b>2</b>Вставь ключи<p>После одобрения бот пришлёт Client ID и Client Secret.</p><button class="btn" data-goto="settings">Перейти в настройки</button></div>
          <div class="step"><b>3</b>Проверь на демо<p>Пока ждёшь одобрения, включи демо: ключи для него уже встроены.</p><button class="btn" id="demoOnBtn">Включить демо</button></div>
        </div>
      </div>
      <div class="hero">
        <h2 id="sumH">Поиск остановлен</h2>
        <p id="sumS">Нажми «Начать поиск» — трекер будет проверять аукцион без остановки и покажет здесь лоты дешевле рынка.</p>
        <div class="progress"><i id="kBar"></i></div>
      </div>
      <div class="toolbar">
        <input class="field search" id="search" placeholder="Найти в находках" autocomplete="off">
        <select class="field" id="fSort" title="Порядок"><option value="exp">Сначала самая ожидаемая прибыль</option><option value="profit">Сначала самые прибыльные</option><option value="chance">Сначала самые надёжные</option><option value="listed">Сначала самые свежие</option><option value="pct">Сначала с самой большой скидкой</option><option value="name">По названию</option></select>
        <button class="toggle rare" id="fRare" title="Только особо редкие находки">💎 Редкие</button>
        <div class="spacer"></div>
        <label class="check"><input type="checkbox" id="hideOld" checked> Скрывать проданные</label>
        <button class="btn ghost sm" id="clearBtn" title="Убрать все находки из списка">Очистить список</button>
      </div>
      <div class="lots" id="rows"></div>
      <div class="empty" id="empty"><div><div class="radar"></div><h3 id="emptyH">Пока ничего не найдено</h3><div id="emptyT">Нажми «Начать поиск» — трекер начнёт проверять аукцион.</div></div></div>
      <section class="near" id="nearBox" hidden>
        <div class="near-head">
          <h3>Почти находки</h3>
          <p class="muted small">Дешевле рынка, но не прошли твои пороги. Видно, что именно отсеяно, — пороги меняются в <a href="#" data-goto="settings">«Настройках»</a>.</p>
        </div>
        <div class="near-list" id="nearRows"></div>
      </section>
    </section>

    <section class="view" id="view-items">
      <div class="grid2">
        <div class="card">
          <h3>Каталог предметов</h3>
          <div class="sub">Найди предмет и нажми «Следить». ★ — особо редкий: о нём придёт отдельное уведомление.</div>
          <input class="field" id="catSearch" placeholder="Например: Морфин, вихрь, запчасти, броня" autocomplete="off" style="width:100%">
          <div class="tabs" id="catTabs"></div>
          <div class="results" id="catResults"><div class="res muted">Загружаю базу предметов…</div></div>
          <div class="muted small" id="catMore" style="margin-top:8px"></div>
        </div>
        <div class="col">
          <div class="card" id="yieldBox" hidden>
            <h3>Что приносит находки</h3>
            <div class="sub" id="yieldSub"></div>
            <div id="yieldBody"></div>
          </div>
          <div class="card">
            <h3>Мой список <span class="muted" id="watchCnt" style="font-weight:500"></span></h3>
            <div class="note ok" id="subItemsNote" hidden>Подписка: список и категории — это фильтр. Показываю находки сервера только по ним, а если пусто — все.</div>
            <div class="chips" id="chips"></div>
            <div class="muted" id="chipsEmpty" style="margin-top:12px">Список пуст.</div>
          </div>
          <div class="card">
            <h3>Категории целиком</h3>
            <div class="sub">Трекер сам проверит все предметы категории, даже если их нет в твоём списке.</div>
            <div class="catrow art-head"><div><b>Артефакты</b><small id="artSub">все артефакты из базы игры</small></div><label class="switch"><input type="checkbox" id="sAllArts" data-cat="artefact"><i></i></label></div>
            <div class="catrow"><div><b>Броня</b><small data-cnt="armor"></small></div><label class="switch"><input type="checkbox" data-cat="armor"><i></i></label></div>
            <div class="catrow"><div><b>Оружие</b><small data-cnt="weapon"></small></div><label class="switch"><input type="checkbox" data-cat="weapon"><i></i></label></div>
            <div class="catrow"><div><b>Запчасти</b><small data-cnt="parts"></small></div><label class="switch"><input type="checkbox" data-cat="parts"><i></i></label></div>
            <div class="catrow"><div><b>Инструменты</b><small data-cnt="tools"></small></div><label class="switch"><input type="checkbox" data-cat="tools"><i></i></label></div>
            <div class="note" id="catNote">Каждый предмет — 1–2 запроса к API за круг (лимит EXBO — 400 в минуту). Чем больше предметов, тем длиннее круг. Цена брони и оружия зависит от заточки — такие находки проверяй в игре.</div>
          </div>
        </div>
      </div>
    </section>

    <section class="view" id="view-buys">
      <div class="kpis">
        <div class="kpi"><div class="l">Вложено в товар</div><div class="v num" id="bInv">0 ₽</div><div class="s" id="bInvS">ещё не продано</div></div>
        <div class="kpi"><div class="l">Ожидаемая прибыль</div><div class="v num good" id="bExp">0 ₽</div><div class="s">по текущим ценам, после комиссии</div></div>
        <div class="kpi"><div class="l">Заработано</div><div class="v num" id="bEarn">0 ₽</div><div class="s" id="bEarnS">по проданным</div></div>
        <div class="kpi"><div class="l">Продано</div><div class="v num" id="bSold">0</div><div class="s" id="bSoldS">сделок</div></div>
      </div>
      <div class="toolbar">
        <div class="seg" id="bSeg"><button data-b="open" class="on">Не проданы</button><button data-b="sold">Проданы</button><button data-b="all">Все</button></div>
        <div class="spacer"></div>
        <span class="muted small">Купил лот из находок — открой его и нажми «Я купил».</span>
      </div>
      <div class="tablewrap">
        <table>
          <thead><tr><th>Предмет</th><th>Кол-во</th><th>Купил за</th><th>Продать по</th><th>Прибыль</th><th>Шанс</th><th></th></tr></thead>
          <tbody id="bRows"></tbody>
        </table>
      </div>
      <div class="empty" id="bEmpty"><div><div class="radar"></div><h3 id="bEmptyH">Пока нет покупок</h3><div id="bEmptyT">Купил лот из находок — открой его и нажми «Я купил». Трекер будет следить за его ценой и шансом продажи.</div></div></div>
      <div class="card acc" id="accBox">
        <h3>Сбываются ли прогнозы</h3>
        <div class="sub" id="accSub">Трекер запоминает свою оценку каждой находки и через несколько часов сравнивает её с тем, за сколько такие лоты реально продавали.</div>
        <div id="accBody"></div>
      </div>
    </section>

    <section class="view" id="view-craft">
      <div class="grid2 craft-top">
        <div class="card">
          <h3>Мои навыки в убежище</h3>
          <div class="sub">Уровни навыков — по ним видно, какие рецепты тебе доступны. Сохраняются сами.</div>
          <div class="skills" id="skills"></div>
        </div>
        <div class="card">
          <h3>Какой навык качать</h3>
          <div class="sub">Что откроет следующий уровень каждого навыка — по сегодняшним ценам аукциона.</div>
          <div id="advice" class="advice"><div class="muted">Загружаю рецепты…</div></div>
        </div>
      </div>
      <div class="toolbar" style="margin-top:16px">
        <input class="field search" id="crSearch" placeholder="Найти рецепт или ингредиент" autocomplete="off">
        <label class="check"><input type="checkbox" id="crMine" checked> Только доступные мне</label>
        <select class="field" id="crSort"><option value="profit">Сначала самые прибыльные</option><option value="energy">Больше прибыли на 1000 энергии</option><option value="name">По названию</option></select>
        <div class="spacer"></div>
        <span class="muted small" id="crPrices"></span>
        <button class="btn" id="crFetch">Узнать цены</button>
      </div>
      <div class="tablewrap">
        <table class="craft">
          <colgroup><col style="width:30%"><col style="width:32%"><col><col><col><col></colgroup>
          <thead><tr><th>Что получится</th><th>Из чего</th><th>Стоимость</th><th>Продать за</th><th>Прибыль</th><th>На 1000 энергии</th></tr></thead>
          <tbody id="crRows"></tbody>
        </table>
      </div>
      <div class="muted small" style="margin-top:10px">Цены — медиана сделок за неделю из твоей базы, продажа — после комиссии 5%. Прибыль не учитывает улучшения убежища, которых может не быть: они показаны серым под рецептом.</div>
    </section>

    <section class="view" id="view-settings">
      <div class="form">
        <div class="card">
          <h3>Что считать выгодным</h3>
          <div class="sub">Лот попадёт в находки, только если выполнены оба условия.</div>
          <div class="row"><label>Дешевле рынка минимум на<small>в процентах</small></label><input class="field num" id="sDiscount" inputmode="numeric"></div>
          <div class="row"><label>Минимальная прибыль<small>после комиссии 5%, ₽</small></label><input class="field num" id="sMinProfit" inputmode="numeric"></div>
        </div>
        <div class="card">
          <h3>Лоты со ставками</h3>
          <div class="sub">Торги скоро закончатся, а ставка намного ниже рынка. Для них действует минимальная прибыль, а «дешевле рынка» — нет. В сообщении — предельная ставка.</div>
          <div class="row"><label>Искать лоты со ставками</label><label class="switch"><input type="checkbox" id="sBids"><i></i></label></div>
          <div class="row"><label>Сообщать, если до конца торгов меньше<small>минут, от 5 до 720</small></label><input class="field num" id="sBidWindow" inputmode="numeric"></div>
          <div class="row"><label>Но не меньше<small>минут — чтобы не приходило то, что уже не успеть</small></label><input class="field num" id="sBidMin" inputmode="numeric"></div>
        </div>
        <div class="card">
          <h3>Надёжность</h3>
          <div class="sub">Пока идёт поиск, компьютер не уснёт (экран гаснуть может). О важном — продано, твой лот перебили, поиск встал, компьютер спал — трекер напишет в Telegram, если он настроен ниже.</div>
          <div class="row"><label>Запускать вместе с Windows<small>окно откроется свёрнутым, поиск начнётся сам</small></label><label class="switch"><input type="checkbox" id="sAutostart"><i></i></label></div>
        </div>
        <div class="card">
          <h3>Доступ к API</h3>
          <div class="sub">Ключи выдаёт @stalzone_api_bot после одобрения заявки.</div>
          <div class="note ok" id="sharedNote" hidden>Работает ключ API владельца из кода доступа — свои ключи не нужны. Впишешь свои — будут использоваться они.</div>
          <div class="note ok" id="feedNote" hidden>Подписка: находки приходят с сервера владельца — ключи EXBO не нужны.</div>
          <div class="row" id="demoRow"><label>Демо-режим<small>Тестовые данные EXBO, ключи не нужны</small></label><label class="switch"><input type="checkbox" id="sDemo"><i></i></label></div>
          <div class="row wide"><label>Client ID</label><input class="field" id="sClientId" autocomplete="off"></div>
          <div class="row wide"><label>Client Secret</label><input class="field" id="sClientSecret" type="password" autocomplete="off"></div>
          <div class="row wide"><label>Ещё ключи API<small>необязательно: по одному в строке — Client ID, пробел, Client Secret. Запросы делятся между ключами, каждый добавляет 400 в минуту. Сохранённые секреты показаны точками.</small></label><textarea class="field code" id="sKeys" placeholder="4729 секрет&#10;4730 секрет" autocomplete="off" spellcheck="false"></textarea></div>
          <div class="muted small" id="keysInfo"></div>
          <div class="linkrow"><button class="btn" data-open="api_bot">Получить доступ</button><button class="btn" data-open="docs">Документация</button></div>
        </div>
        <div class="card">
          <h3>Уведомления</h3>
          <div class="sub">Звук в программе и сообщение в Telegram о каждой новой находке.</div>
          <div class="row"><label>Звук при находке<small>сохраняется на этом компьютере</small></label><label class="switch"><input type="checkbox" id="sSound"><i></i></label></div>
          <div class="row wide"><label>Токен бота Telegram<small>создай бота у @BotFather</small></label><input class="field" id="sTgToken" type="password" autocomplete="off"></div>
          <div class="row wide"><label>Chat ID<small>число от @userinfobot; у своего бота нажми Start</small></label><input class="field" id="sTgChat" autocomplete="off"></div>
          <div class="linkrow"><button class="btn" id="tgTestBtn">Проверить Telegram</button><button class="btn" data-open="botfather">Открыть @BotFather</button></div>
        </div>
        <div class="card">
          <h3>Особо редкие</h3>
          <div class="sub">Отдельный звук, пометка 💎 и сообщение в Telegram с заголовком «ОСОБО РЕДКИЙ».</div>
          <div class="row"><label>Отдельные уведомления</label><label class="switch"><input type="checkbox" id="sRare"><i></i></label></div>
          <div class="row w2"><label>Артефакты от качества</label><select class="field" id="sRareQ"><option value="3">редкий</option><option value="4">исключительный</option><option value="5">легендарный</option></select></div>
          <div class="row"><label>Минимальная прибыль для них<small>после комиссии, ₽ — можно ниже обычной</small></label><input class="field num" id="sRareProfit" inputmode="numeric"></div>
          <div class="note">Ещё особо редкими считаются снаряжение ранга «Легенда» и всё, что отмечено звёздочкой ★ во вкладке «Предметы».</div>
        </div>
        <div class="card">
          <h3>Программа и данные</h3>
          <div class="sub">Версия <span id="appVer"></span>. Ключи, настройки, находки и журнал хранятся отдельно от программы — обновление их не сотрёт.</div>
          <div class="row w2"><label>Тема<small>меняется сразу</small></label><select class="field" id="sTheme"><option value="system">Как в Windows</option><option value="light">Светлая</option><option value="dark">Тёмная</option></select></div>
          <div class="row w2"><label>Вид программы<small>новый — как программы Windows 11</small></label><select class="field" id="sUi"><option value="new">Новый</option><option value="old">Классический</option></select></div>
          <div class="row wide"><label>Папка с данными<small id="dataDir" style="word-break:break-all"></small></label></div>
          <div class="muted small" id="dbInfo" style="margin-top:10px">База сделок пока пустая — начнёт копиться после запуска.</div>
          <div class="muted small" id="updInfo" style="margin-top:8px"></div>
          <div class="linkrow"><button class="btn" id="updCheckBtn">Проверить обновления</button><button class="btn" id="openDataBtn">Открыть папку</button></div>
        </div>
      </div>
      <div class="savebar"><span class="muted" id="saveHint" style="align-self:center"></span><button class="btn primary" id="saveBtn">Сохранить</button></div>
    </section>

    <section class="view" id="view-access">
      <div class="form">
        <div class="col">
          <div class="card">
            <h3>Этот компьютер</h3>
            <div class="sub">Вставь код от владельца — больше ничего не нужно: компьютер привяжется сам.</div>
            <div class="idrow"><b class="num" id="accMachine">—</b><button class="btn" id="accCopyId">Копировать код запроса</button></div>
            <div class="muted small" style="margin:-4px 0 8px">Код запроса нужен, только если владелец сам его попросит.</div>
            <div class="note" id="accStatus"></div>
            <div id="accCodeBox">
              <div class="row wide"><label>Новый код доступа<small>если владелец прислал новый или продлил старый</small></label><textarea class="field code" id="accCode" placeholder="SZ1-…"></textarea></div>
              <div class="linkrow"><button class="btn" id="accCodeBtn">Применить код</button></div>
            </div>
          </div>
          <div class="card" id="ownerSetup">
            <h3>Для владельца программы</h3>
            <div class="sub" id="osSub">Закрытый доступ включается один раз: владелец создаёт личный ключ, а его открытая часть вписывается в программу.</div>
            <div class="linkrow" id="osNoKey"><button class="btn primary" id="osCreate">Создать ключ владельца</button></div>
            <div id="osHasKey" hidden>
              <div class="row wide"><label>Открытый ключ<small>его не страшно показывать — по нему программа проверяет коды</small></label><textarea class="field code" id="osPub" readonly></textarea></div>
              <div class="linkrow"><button class="btn" id="osCopy">Копировать ключ</button><button class="btn" data-opendata="1">Открыть папку с ключом</button></div>
            </div>
            <div class="note warn" id="osWarn" hidden>Личный ключ — файл owner_key.pem в папке данных. Сделай копию (флешка, облако) и никому не отправляй: с ним можно выдавать коды от твоего имени.</div>
          </div>
        </div>
        <div class="col">
          <div class="card warncard" id="keyWarn" hidden>
            <h3>Твой ключ API тратит ещё кто-то</h3>
            <div class="sub" id="keyWarnText"></div>
            <div class="linkrow"><button class="btn" data-open="api_bot">Открыть @stalzone_api_bot</button><button class="btn" data-goto="settings">Вписать новый секрет</button></div>
          </div>
          <div class="card" id="serverCard" hidden>
            <h3>Сервер для подписчиков</h3>
            <div class="sub">Один поиск — для всех: твоя программа раздаёт найденное из памяти, подписчики лимит EXBO не тратят, и твой поиск не замедляется, сколько бы их ни было. Пока сервер работает, компьютер должен быть включён.</div>
            <div class="row"><label>Раздавать находки подписчикам</label><label class="switch"><input type="checkbox" id="srvOn"><i></i></label></div>
            <div class="row wide"><label>Публичный адрес<small>его даёт Tailscale Funnel, например https://мой-пк.xxxx.ts.net — он вписывается в новые коды</small></label><input class="field" id="srvUrl" placeholder="https://…ts.net" autocomplete="off"></div>
            <div class="note" id="srvStatus"></div>
            <div class="linkrow"><button class="btn primary" id="srvFunnel">Открыть доступ из интернета</button><button class="btn" id="srvLink" hidden>Открыть ссылку Tailscale</button></div>
            <div class="linkrow"><button class="btn" id="srvSave">Сохранить</button><button class="btn" id="srvTest">Проверить адрес</button></div>
            <details class="note howto"><summary>Если кнопка не помогла — то же вручную</summary>
              <ol>
                <li>Скачай и установи Tailscale: tailscale.com/download → Windows. Войди через Google или Microsoft.</li>
                <li>Открой «Командную строку» (Win+R → <b>cmd</b> → Enter) и выполни: <code id="funnelCmd">tailscale funnel --bg 8790</code></li>
                <li>Если попросит — открой ссылку из окна и подтверди включение Funnel.</li>
                <li>Команда покажет адрес вида https://имя.xxxx.ts.net — вставь его выше, нажми «Сохранить» и «Проверить адрес».</li>
              </ol>
              Флаг --bg оставляет сервер открытым и после перезагрузки. Закрыть: <code>tailscale funnel --https=443 off</code></details>
          </div>
          <div class="card" id="ownerIssue" hidden>
            <h3>Выдать доступ</h3>
            <div class="sub">Код можно просто отправить: компьютер подписчика привяжется сам при первом подключении. Для группы или канала поставь больше мест — каждый новый компьютер займёт одно.</div>
            <div class="note warn" id="isWarn" hidden>Сервер ещё не открыт в интернет — по новому коду находки не придут. Нажми «Открыть доступ из интернета» в карточке сервера.</div>
            <div class="row wide"><label>Кому<small>имя человека или название группы — по нему потом можно отключить</small></label><input class="field" id="isName" autocomplete="off"></div>
            <div class="row"><label>Мест<small>1 — один человек; больше — один код на группу</small></label><input class="field num" id="isSeats" value="1" inputmode="numeric"></div>
            <div class="row"><label>Срок<small>дней, 0 — бессрочно</small></label><input class="field num" id="isDays" value="30" inputmode="numeric"></div>
            <details class="note howto"><summary>Привязать к конкретному компьютеру сразу</summary>
              <div class="row wide" style="margin-top:8px"><label>Код запроса<small>подписчик копирует его в своей программе: «Копировать код запроса»</small></label><input class="field" id="isMachine" placeholder="SZR1-…" autocomplete="off"></div>
            </details>
            <div class="linkrow"><button class="btn primary" id="isBtn">Создать код</button></div>
            <div id="isResult" hidden>
              <div class="row wide"><label>Сообщение подписчику<small>ссылка на программу, код и что сделать — отправь целиком</small></label><textarea class="field code" id="isMsg" readonly style="min-height:150px"></textarea></div>
              <textarea id="isCode" hidden readonly></textarea>
              <div class="linkrow"><button class="btn primary" id="isCopy">Скопировать сообщение</button><button class="btn" id="isCopyCode">Скопировать только код</button></div>
            </div>
          </div>
          <div class="card" id="ownerList" hidden>
            <h3>Подписчики</h3>
            <div class="sub">«+30 дн.» — новый код с продлением от конца оплаченного срока (места переходят на него). «Освободить» — если подписчик сменил компьютер. «Отключить» сразу закрывает находки.</div>
            <div class="issued" id="issuedList"></div>
            <div class="linkrow"><button class="btn" data-open="revoked_new">Создать revoked.txt</button><button class="btn" data-open="revoked_edit">Изменить revoked.txt</button></div>
            <div class="muted small" style="margin-top:6px">revoked.txt — для тех, кто пользуется программой без сервера: впиши имя или номер кода, программа у него закроется в течение трёх часов.</div>
          </div>
        </div>
      </div>
    </section>

    <section class="view" id="view-log"><div class="log" id="log"></div></section>
  </main>
</div>

<aside class="drawer" id="drawer" aria-label="Карточка находки"></aside>
<div class="overlay" id="restartOverlay" hidden><div><div class="radar"></div><h2>Устанавливаю обновление</h2><div class="muted">Программа закроется и через несколько секунд откроется уже новой версией.</div></div></div>
<div class="overlay" id="lockOverlay" hidden><div class="lock">
  <div class="logo"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l9 10-9 10-9-10z" opacity=".35"/><path d="M12 6.5l5 5.5-5 5.5-5-5.5z"/></svg></div>
  <h2>Закрытый доступ</h2>
  <div class="muted" id="lockReason"></div>
  <div class="idrow"><span class="muted">ID этого компьютера:</span><b class="num" id="lockMachine">—</b><button class="btn primary" id="lockCopy">Копировать код запроса</button></div>
  <div class="muted small">Отправь владельцу код запроса (кнопка выше скопирует его целиком) — он пришлёт код доступа. Вставь его сюда:</div>
  <textarea class="field code" id="lockCode" placeholder="SZ1-…"></textarea>
  <button class="btn primary" id="lockBtn">Открыть доступ</button>
</div></div>
<div class="toast" id="toast" role="status"></div>

<script>
const TOKEN = "__TOKEN__";
const QN = ["обычный","необычный","особый","редкий","исключительный","легендарный"];
const TITLES = {deals:"Находки", items:"Предметы", buys:"Мои покупки", craft:"Крафт в убежище", settings:"Настройки", access:"Доступ", log:"Журнал"};
const FILTER_CATS = ["artefact", "armor", "weapon", "parts", "tools"];
const RANK_RU = {RANK_NEWBIE: "Новичок", RANK_STALKER: "Сталкер", RANK_VETERAN: "Ветеран", RANK_MASTER: "Мастер", RANK_LEGEND: "Легенда"};
const RANK_Q = {RANK_NEWBIE: 1, RANK_STALKER: 2, RANK_VETERAN: 3, RANK_MASTER: 4, RANK_LEGEND: 5};
const RELEASES_URL = "https://github.com/Enotsbeye/stalzone-tracker-releases/releases/latest";
let S = null, view = "deals", kind = "all", selected = null;
let knownIds = new Set(), firstLoad = true, lastErr = 0, formDirty = false;
const $ = (id) => document.getElementById(id);
const rub = (x) => Math.round(x).toLocaleString("ru-RU").replace(/\s/g, " ") + " ₽";
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const store = { get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
                set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} } };
let CAT = null, CATMAP = {}, CATNAMES = {}, catTab = store.get("catTab", "all"), catLoading = 0;
let F = Object.assign({rare: false, sort: "exp"}, store.get("filters", {}), {cat: "all", chance: 0, profit: "", fresh: false});
let bFilter = store.get("bFilter", "open"), sellOpen = null, showBarter = store.get("showBarter", false);

// ---------- тема ----------
function applyTheme(t) { if (t === "light" || t === "dark") document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; }
const INITIAL_THEME = "__THEME__";   // тему помнит программа (общая с новым видом), а не только этот браузер
applyTheme(INITIAL_THEME.startsWith("__") ? store.get("theme", "system") : INITIAL_THEME);

async function api(path, body) {
  const opt = { headers: { "X-Token": TOKEN } };
  if (body !== undefined) { opt.method = "POST"; opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  const r = await fetch(path, opt);
  return r.json();
}
function toast(msg, err) {
  const t = $("toast"); t.textContent = msg; t.className = "toast on" + (err ? " err" : "");
  clearTimeout(toast.h); toast.h = setTimeout(() => t.className = "toast", 2800);
}
function plural(n, forms) {
  const a = n % 10, b = n % 100;
  return forms[a === 1 && b !== 11 ? 0 : a >= 2 && a <= 4 && (b < 12 || b > 14) ? 1 : 2];
}
function ago(iso, now) {
  if (!iso) return "—";
  const m = (now - Date.parse(iso) / 1000) / 60;
  if (m < 1) return "только что";
  if (m < 60) return Math.round(m) + " мин назад";
  if (m < 48 * 60) return Math.round(m / 60) + " ч назад";
  return Math.round(m / 1440) + " дн. назад";
}
function fmtWindow(h) { return h < 36 ? Math.round(h) + " ч" : Math.round(h / 24) + " дн."; }
function until(iso) {
  if (!iso) return "—";
  const d = new Date(iso), now = new Date();
  const hm = d.toLocaleTimeString("ru-RU", {hour: "2-digit", minute: "2-digit"});
  return d.toDateString() === now.toDateString() ? "сегодня " + hm : d.toLocaleDateString("ru-RU", {day: "2-digit", month: "2-digit"}) + " " + hm;
}
function fmtHours(h) { if (h === null || h === undefined) return ""; if (h < 1) return "меньше часа"; if (h < 48) return "~" + Math.round(h) + " ч"; return "~" + Math.round(h / 24) + " дн."; }
function n1(x) { return (x >= 10 ? Math.round(x) : Math.round(x * 10) / 10).toLocaleString("ru-RU"); }

// ---------- ячейка предмета: картинка из базы игры, цвет редкости ----------
function letter(name) { return (String(name || "?").replace(/[«»"'\s]/g, "").charAt(0) || "?").toUpperCase(); }
function slot(id, name, color, size) {
  return `<span class="slot${size ? " " + size : ""}" data-l="${esc(letter(name))}" style="--rc:${color}"><img src="/icon/${encodeURIComponent(id || "")}.png" alt="" loading="lazy" onload="if(this.naturalWidth>4)this.parentNode.classList.add('ok');else this.remove()" onerror="this.remove()"></span>`;
}
function isArtefact(d) { return d.cat === "artefact" || (d.cat == null && d.quality !== null && d.quality !== undefined); }
function tone(d) {
  if (isArtefact(d) && d.quality !== null && d.quality !== undefined) return `var(--q${Math.max(0, Math.min(5, d.quality))})`;
  if (d.rank && RANK_Q[d.rank]) return `var(--q${RANK_Q[d.rank]})`;
  return "var(--q0)";
}
function gradeText(d) {
  if (!isArtefact(d)) return d.ptn ? "+" + d.ptn : "";
  if (d.quality === null || d.quality === undefined) return "";
  return (QN[d.quality] || d.quality) + " " + (d.exact ? "+" + d.ptn : d.ptn >= 15 ? "+15" : "+" + d.ptn + "…" + (d.ptn + 4));
}
function gradeTag(d) { const t = gradeText(d); return t ? `<span class="grade" style="color:${tone(d)}">${esc(t)}</span>` : ""; }
function rankText(d) { return d.rank && RANK_RU[d.rank] && ["armor", "weapon", "attachment", "backpacks", "containers"].includes(d.cat) ? RANK_RU[d.rank] : ""; }
function rankTag(d) { const t = rankText(d); return t ? `<span class="rk" style="color:${tone(d)}">${t}</span>` : ""; }
function qualityTag(d) { return gradeTag(Object.assign({cat: "artefact"}, d)); }

function beep(rare) {
  if (!store.get("sound", true)) return;
  try {
    const ctx = beep.ctx || (beep.ctx = new (window.AudioContext || window.webkitAudioContext)());
    const notes = rare ? [[0, 784], [0.12, 988], [0.24, 1319], [0.42, 1568]] : [[0, 880], [0.13, 1180]];
    notes.forEach(([t, f]) => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.frequency.value = f; o.type = rare ? "triangle" : "sine";
      g.gain.setValueAtTime(0.0001, ctx.currentTime + t);
      g.gain.exponentialRampToValueAtTime(rare ? 0.22 : 0.18, ctx.currentTime + t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + t + (rare ? 0.2 : 0.12));
      o.connect(g).connect(ctx.destination); o.start(ctx.currentTime + t); o.stop(ctx.currentTime + t + 0.22);
    });
  } catch (e) {}
}
function notifyDesktop(d) {
  try {
    if ("Notification" in window && Notification.permission === "granted")
      new Notification((d.rare ? "💎 Особо редкий: " : "") + d.name + " — прибыль ~" + rub(d.profit),
        { body: (d.kind === "bid" ? "Ставка · " : "Купить · ") + d.amount + " шт за " + rub(d.cost) + (d.chance != null ? " · шанс продать " + Math.round(d.chance * 100) + "%" : "") });
  } catch (e) {}
}

// ---------- умный поиск ----------
// понимает опечатки («морфн»), неверную раскладку («vjhaby» → «морфин»), латиницу и кириллицу («мп7» → MP7),
// слова в любом порядке; точное совпадение и начало названия — выше всего
const KB_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`", KB_RU = "йцукенгшщзхъфывапролджэячсмитьбюё";
const KB = {};
[...KB_EN].forEach((c, i) => { KB[c] = KB_RU[i]; KB[KB_RU[i]] = c; });
const C2L = {а:"a",б:"b",в:"v",г:"g",д:"d",е:"e",ж:"zh",з:"z",и:"i",й:"y",к:"k",л:"l",м:"m",н:"n",о:"o",п:"p",р:"r",с:"s",т:"t",у:"u",ф:"f",х:"h",ц:"c",ч:"ch",ш:"sh",щ:"sch",ъ:"",ы:"y",ь:"",э:"e",ю:"yu",я:"ya"};
function normQ(s) { return String(s || "").toLowerCase().replace(/ё/g, "е").replace(/[«»"'`.,:;!?()\[\]\/\\_+-]+/g, " ").replace(/\s+/g, " ").trim(); }
function toLat(s) { return [...s].map((c) => C2L[c] ?? c).join(""); }
function lev(a, b, lim) {
  if (Math.abs(a.length - b.length) > lim) return lim + 1;
  let prev = Array.from({length: b.length + 1}, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i]; let best = i;
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      best = Math.min(best, cur[j]);
    }
    if (best > lim) return lim + 1;
    prev = cur;
  }
  return prev[b.length];
}
function searchKey(name, extra) {
  const n = normQ(name), l = toLat(n);
  return {n, l, w: n.split(" "), lw: l.split(" "), c: n.replace(/ /g, ""), lc: l.replace(/ /g, ""), x: normQ(extra || "")};
}
function prepQuery(text) {
  const n = normQ(text);
  if (!n) return null;
  const vs = [n], sw = normQ([...n].map((c) => KB[c] || c).join(""));
  if (sw && sw !== n) vs.push(sw);
  return vs.map((v) => ({n: v, w: v.split(" "), l: toLat(v), lw: toLat(v).split(" "), c: v.replace(/ /g, ""), lc: toLat(v).replace(/ /g, "")}));
}
function scoreOne(q, k) {
  let best = 0;
  for (const [qs, ks, qw, kw] of [[q.n, k.n, q.w, k.w], [q.l, k.l, q.lw, k.lw]]) {
    if (!qs) continue;
    if (ks === qs) return 1000;
    if (ks.startsWith(qs)) { best = Math.max(best, 900 - ks.length); continue; }
    if (qw.every((w) => kw.some((x) => x.startsWith(w)))) { best = Math.max(best, 700 - ks.length); continue; }
    if (qw.every((w) => ks.includes(w))) { best = Math.max(best, 500 - ks.length); continue; }
    const qc = qs === q.n ? q.c : q.lc, kc = ks === k.n ? k.c : k.lc;   // «ак103» = «АК-103»
    if (qc.length >= 3 && kc.startsWith(qc)) { best = Math.max(best, 850 - ks.length); continue; }
    if (qc.length >= 3 && kc.includes(qc)) { best = Math.max(best, 450 - ks.length); continue; }
    let ok = true, cost = 0;
    for (const w of qw) {
      if (kw.some((x) => x.startsWith(w)) || ks.includes(w)) continue;
      if (w.length < 3) { ok = false; break; }
      const lim = w.length >= 7 ? 2 : 1;
      let d = lim + 1;
      for (const x of kw) d = Math.min(d, lev(w, x.slice(0, w.length), lim), lev(w, x, lim));
      if (d > lim) { ok = false; break; }
      cost += d;
    }
    if (ok) best = Math.max(best, 300 - cost * 40 - ks.length);
  }
  if (!best && k.x && q.w.every((w) => k.x.split(" ").some((x) => x.startsWith(w)))) best = 150;   // категория, ранг
  return best;
}
function matchScore(qv, key) { let b = 0; for (const q of qv) b = Math.max(b, scoreOne(q, key)); return b; }

// ---------- навигация ----------
function go(v) {
  view = v;
  document.querySelectorAll(".nav button").forEach((b) => b.classList.toggle("on", b.dataset.view === v));
  document.querySelectorAll(".view").forEach((s) => s.classList.toggle("on", s.id === "view-" + v));
  $("viewTitle").textContent = TITLES[v];
  if (v !== "deals") closeDrawer();
  if (v === "items" && CAT) renderCatalog(true);
  if (v === "items") loadYield();
  if (v === "craft") loadCraft();
}
document.querySelectorAll(".nav button").forEach((b) => b.onclick = () => go(b.dataset.view));
document.querySelectorAll("[data-goto]").forEach((b) => b.onclick = (e) => { e.preventDefault(); go(b.dataset.goto); });
document.querySelectorAll("[data-open]").forEach((b) => b.onclick = () => api("/api/open", {link: b.dataset.open}));
$("demoOnBtn").onclick = async () => {
  const r = await api("/api/settings", {demo: true});
  toast(r.ok ? "Демо-режим включён — нажми «Начать поиск»" : r.message, !r.ok);
  refresh();
};
$("demoOffBtn").onclick = () => {
  go("settings");
  const row = $("demoRow");
  row.classList.remove("flash"); void row.offsetWidth; row.classList.add("flash");
  row.scrollIntoView({block: "center", behavior: "smooth"});
  toast("Выключи «Демо-режим» и нажми «Сохранить»");
};

// ---------- запуск ----------
$("runBtn").onclick = async () => {
  if (S && S.status.running) { await api("/api/stop", {}); toast("Останавливаю поиск…"); return; }
  try { if ("Notification" in window && Notification.permission === "default") Notification.requestPermission(); } catch (e) {}
  const r = await api("/api/start", {});
  if (!r.ok) { toast(r.message, true); if (!S.configured) go("settings"); else go("items"); }
  else toast("Поиск запущен");
  refresh();
};

// ---------- находки ----------
$("search").oninput = () => renderDeals(true);
$("hideOld").onchange = () => { renderDeals(true); renderNear(true); };
$("clearBtn").onclick = async () => { await api("/api/deals/clear", {}); closeDrawer(); refresh(); };
function catGroup(c) { return FILTER_CATS.includes(c) ? c : "other"; }
function saveFilters() { store.set("filters", F); }
function syncFilters() {
  $("fSort").value = F.sort || "exp";
  $("fRare").classList.toggle("on", !!F.rare);
}
$("fSort").onchange = () => { F.sort = $("fSort").value; saveFilters(); renderDeals(true); };
$("fRare").onclick = () => { F.rare = !F.rare; saveFilters(); syncFilters(); renderDeals(true); };
syncFilters();
function chanceCls(c) { return c >= 0.7 ? "hi" : c >= 0.4 ? "mid" : "lo"; }
function chanceWords(c) { return c >= 0.7 ? "Продастся быстро" : c >= 0.4 ? "Может повисеть" : "Продать будет трудно"; }
function chancePill(c, h) {
  if (c === null || c === undefined) return `<span class="chance none">шанс не посчитан</span>`;
  return `<span class="chance ${chanceCls(c)}" title="Шанс продать за сутки${h ? " · обычно за " + fmtHours(h) : ""}">${chanceWords(c)} · ${Math.round(c * 100)}%</span>`;
}
function chanceCell(c, h) { return chancePill(c, h); }
function fateTag(d) {
  if (d.bought) return `<span class="tag mine">✓ Куплено</span>`;
  if (d.fate === "sold") return `<span class="tag" title="Лот пропал, и в истории есть сделка ровно на него">уже купили</span>`;
  if (d.fate === "removed") return `<span class="tag" title="Лот пропал, а сделки по нему в истории нет">снят</span>`;
  if (d.fate === "expired") return `<span class="tag">истёк</span>`;
  if (d.gone) return `<span class="tag" title="Лота больше нет — сверяю с историей сделок, купили его или сняли">пропал</span>`;
  return "";
}
function dealTags(d, now) {
  const fresh = now - d.found < 300 && !d.gone;
  return (d.kind === "bid" ? `<span class="tag bid">Ставка</span>` : "")
    + (d.rare ? `<span class="tag rare">💎 редкий</span>` : "")
    + (fresh ? `<span class="tag fresh">новое</span>` : "")
    + (d.only_you_until && d.only_you_until > now && !d.gone ? `<span class="tag excl" title="Сервер отдал эту находку сначала тебе — потом её увидят все">🎯 только тебе ещё ${Math.max(1, Math.ceil((d.only_you_until - now) / 60))} мин</span>` : "")
    + fateTag(d)
    + (d.stale && !d.gone ? `<span class="tag stale" title="${esc(d.stale)}">давно висит</span>` : "");
}
function visibleDeals() {
  const qv = prepQuery($("search").value);
  const now = S.now, minProfit = +(F.profit || 0);
  let list = S.deals.filter((d) => (kind === "all" || d.kind === kind)
    && (!qv || matchScore(qv, d._k || (d._k = searchKey(d.name, (CATNAMES[d.cat] || "") + " " + (RANK_RU[d.rank] || "")))) > 0)
    && (F.cat === "all" || catGroup(d.cat) === F.cat)
    && (!F.chance || (d.chance !== null && d.chance !== undefined && d.chance * 100 >= F.chance))
    && (!minProfit || d.profit >= minProfit)
    && (!F.rare || d.rare)
    && (!F.fresh || (d.listed && now - Date.parse(d.listed) / 1000 < 1800))
    && (!$("hideOld").checked || d.bought || (!d.gone && (!d.ends || Date.parse(d.ends) / 1000 > now))));
  const key = F.sort || "profit";
  const val = (d) => key === "listed" ? Date.parse(d.listed || 0) : key === "chance" ? (d.chance == null ? -1 : d.chance)
    : key === "exp" ? (d.exp_profit == null ? d.profit * 0.3 : d.exp_profit) : key === "name" ? d.name : d[key];
  list.sort((a, b) => { const x = val(a), y = val(b); return key === "name" ? String(x).localeCompare(y, "ru") : (y - x); });
  return list;
}
function dealCard(d, now) {
  const old = !d.bought && (d.gone || (d.ends && Date.parse(d.ends) / 1000 <= now));
  const bid = d.kind === "bid", many = d.amount > 1;
  return `<article class="lot${selected === d.id ? " sel" : ""}${old ? " old" : ""}${d.rare ? " rare" : ""}${d.bought ? " mine" : ""}" data-id="${d.id}" tabindex="0">
    ${slot(d.item_id, d.name, tone(d))}
    <div>
      <div class="lot-title"><span class="n">${esc(d.name)}</span>${gradeTag(d)}${rankTag(d)}</div>
      <div class="lot-deal">${bid ? (d.has_bids ? "Перебей ставку" : "Сделай ставку") : "Купи"} ${many ? d.amount + " шт " : ""}за <b class="num">${rub(d.cost)}</b> — продашь примерно за <b class="num">${rub(d.resale)}</b>${many ? ` <span class="muted num">(${rub(d.unit)} → ${rub(d.market)} за шт)</span>` : ""}</div>
      <div class="lot-meta">${chancePill(d.chance, d.sell_hours)}<span>${bid ? "до конца торгов: " + until(d.ends) : "выставлен " + ago(d.listed, now)}</span><span class="tags">${dealTags(d, now)}</span></div>
    </div>
    <div class="lot-side">
      <div class="profit num">+${rub(d.profit)}</div>
      ${d.exp_profit != null ? `<div class="small num exp" title="Прибыль × шанс продать за сутки">ожидаемо +${rub(d.exp_profit)}</div>` : ""}
      <div class="muted small num">дешевле рынка на ${Math.round(d.pct)}%</div>
      <button class="btn sm copy" data-copy="${d.id}" title="Вставь в поиск аукциона в игре"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 00-2-2H6a2 2 0 00-2 2v8a2 2 0 002 2h2"/></svg>Скопировать название</button>
    </div>
  </article>`;
}
let lastDealsSig = "";
function renderDeals(force) {
  if (!S) return;
  const list = visibleDeals(), now = S.now;
  const sig = JSON.stringify([list.map((d) => [d.id, d.gone, d.fate, d.bought, d.chance, d.profit, d.stale ? 1 : 0]), selected, Math.floor(now / 30)]);
  if (force || sig !== lastDealsSig) {
    lastDealsSig = sig;
    $("rows").innerHTML = list.map((d) => dealCard(d, now)).join("");
    $("rows").querySelectorAll(".lot").forEach((el) => {
      el.onclick = (e) => { if (!e.target.closest("[data-copy]")) openDrawer(+el.dataset.id); };
      el.onkeydown = (e) => { if (e.key === "Enter") openDrawer(+el.dataset.id); };
    });
    $("rows").querySelectorAll("[data-copy]").forEach((b) => b.onclick = () => {
      const d = S.deals.find((x) => x.id === +b.dataset.copy); if (d) copyText(d.name);
    });
  }
  const empty = list.length === 0;
  $("empty").style.display = empty ? "grid" : "none";
  $("empty").classList.toggle("compact", (S.near || []).some((r) => !r.gone));
  if (empty) {
    if (S.status.running && !S.deals.length && (S.near || []).some((r) => !r.gone)) {
      $("emptyH").textContent = "По твоим порогам — пока ничего";
      $("emptyT").textContent = "Ниже лоты дешевле рынка, которые отсеяли пороги. Если их много, а находок нет, попробуй снизить «Минимальную прибыль».";
    }
    else if (S.status.running && !S.deals.length) {
      $("emptyH").textContent = "Ищу выгодные лоты…";
      $("emptyT").textContent = "Как только что-то найдётся — появится здесь, со звуком. Окно можно свернуть.";
    }
    else if (S.deals.length) { $("emptyH").textContent = "Под фильтры ничего не подходит"; $("emptyT").textContent = "Нажми «Сбросить» или сними галочку «Скрывать проданные»."; }
    else { $("emptyH").textContent = "Пока ничего не найдено"; $("emptyT").textContent = "Нажми «Начать поиск» — трекер начнёт проверять аукцион."; }
  }
}
// ---------- «почти находки»: что отсеяли пороги и почему ----------
function nearWhy(r) {
  const out = (r.why || []).map((w) => w.what === "profit" ? `прибыль меньше твоего порога ${rub(w.need)}`
    : `дешевле рынка только на ${Math.floor(nearPct(r))}%, а нужно от ${Math.round(w.need)}%`);
  return out.join("; ") || "не прошла пороги";
}
function nearPct(r) { const base = Math.min(r.hist || 0, r.market || 0); return base > 0 ? (1 - r.unit / base) * 100 : 0; }
let lastNearSig = "";
function renderNear(force) {
  const list = (S.near || []).filter((r) => !r.gone || !$("hideOld").checked);
  const sig = JSON.stringify([list.map((r) => [r.key, r.gone, r.fate, r.profit, (r.why || []).length]), Math.floor(S.now / 30)]);
  $("nearBox").hidden = !list.length;
  if (!force && sig === lastNearSig) return;
  lastNearSig = sig;
  $("nearRows").innerHTML = list.map((r, i) => `<div class="nr${r.gone ? " gone" : ""}">
    ${slot(r.item_id, r.name, tone(r), "sm")}
    <div>
      <div class="lot-title"><span class="n">${esc(r.name)}</span>${gradeTag(r)}${rankTag(r)}</div>
      <div class="small">Купить${r.amount > 1 ? " " + r.amount + " шт" : ""} за <b class="num">${rub(r.cost)}</b> — продать примерно за <b class="num">${rub(r.resale)}</b> · ${r.gone ? (r.fate === "sold" ? "уже купили" : "лот снят") : "выставлен " + ago(r.listed, S.now)}</div>
      <div class="why">${esc(nearWhy(r))}</div>
    </div>
    <div class="nr-side"><b class="num">+${rub(r.profit)}</b><span class="muted num">−${Math.floor(nearPct(r))}% к рынку</span>
      <button class="btn sm copy" data-ncopy="${i}" title="Вставь в поиск аукциона в игре">Скопировать название</button></div>
  </div>`).join("");
  $("nearRows").querySelectorAll("[data-ncopy]").forEach((b) => b.onclick = () => { const r = list[+b.dataset.ncopy]; if (r) copyText(r.name); });
}
function chanceBlock(c) {
  if (!c) return `<div class="sect"><h3>Шанс продать за сутки</h3><div class="muted">Мало сделок, чтобы оценить.</div></div>`;
  const p = Math.round(c.chance * 100), cls = chanceCls(c.chance);
  const why = [];
  if (c.data && c.data.hours > 0) {
    const life = c.data.per_hour > 0 ? 1 / c.data.per_hour : null;
    why.push([`Похожие лоты на твоём рынке продаются в среднем за ${life ? fmtHours(life).replace("~", "≈ ") : "долго"} — по ${c.data.sold} ${plural(c.data.sold, ["продаже", "продажам", "продажам"])} за ${Math.round(c.data.hours)} ч наблюдений`, life && life < 12 ? "up" : "down"]);
  }
  why.push([`Этот предмет покупают примерно ${n1(c.per_day)} раз в сутки`, c.per_day >= 10 ? "up" : c.per_day < 2 ? "down" : ""]);
  why.push([c.comp ? `Рядом по цене ещё ${c.comp} ${plural(c.comp, ["продавец", "продавца", "продавцов"])}` : "Ты будешь самым дешёвым продавцом", c.comp ? "down" : "up"]);
  if (c.need > 1) why.push([`Чтобы продать весь лот, понадобится ~${c.need} ${plural(c.need, ["покупатель", "покупателя", "покупателей"])} (обычно берут по ${Math.round(c.size)} шт)`, "down"]);
  if (c.trend_f < 1) why.push(["Цена за сутки падает", "down"]); else if (c.trend_f > 1) why.push(["Цена за сутки растёт", "up"]);
  if (c.stale_f < 1) why.push(["Лот давно висит со скидкой, а его не берут — возможно, есть подвох", "down"]);
  if (c.supply_days !== null && c.supply_days !== undefined && c.supply_days >= 3) why.push([`На аукционе похожих лотов примерно на ${n1(c.supply_days)} дн. продаж`, "down"]);
  return `<div class="sect">
    <h3>Шанс продать за сутки</h3>
    <div class="cv ${cls}">${chanceWords(c.chance)} — ${p}%<span>${c.hours !== null && c.hours !== undefined ? "обычно за " + fmtHours(c.hours).replace("~", "") : ""}</span></div>
    <div class="cbar ${cls}" style="color:var(--${cls === "hi" ? "good" : cls === "mid" ? "warn" : "bad"})"><i style="width:${p}%"></i></div>
    <ul class="reasons">${why.map(([t, k]) => `<li class="${k}">${esc(t)}</li>`).join("")}</ul>
    <div class="kv">
      <span>Нужно покупателей</span><span>${c.need}</span>
      <span>Сделок в сутки</span><span>${n1(c.per_day)}</span>
      <span>Платили не меньше этой цены</span><span>${Math.round(c.share * 100)}%</span>
      <span>Конкуренты рядом по цене</span><span>${c.comp}</span>
      ${c.data ? `<span>По наблюдениям трекера</span><span>${Math.round(c.data.p * 100)}% · вес ${Math.round(c.data.weight * 100)}%</span>` : `<span>Свои наблюдения</span><span>пока копятся</span>`}
      <span>По формуле</span><span>${Math.round((c.model || 0) * 100)}%</span>
      ${c.week !== undefined ? `<span>Шанс за неделю</span><span>${Math.round(c.week * 100)}%</span>` : ""}
    </div>
    <div class="muted small" style="margin-top:9px">Это оценка, а не гарантия: API не показывает, сколько людей хотят купить. Чем дольше трекер работает, тем больше она опирается на то, как лоты продаются на самом деле.</div>
  </div>`;
}

// ---------- графики в карточке ----------
function priceChart(series, d) {
  const pts = (series || []).filter((x) => x.p > 0);
  if (pts.length < 2) return `<div class="muted">Мало сделок для графика — трекер ещё копит историю.</div>`;
  const W = 400, H = 132, L = 4, R = 116, T = 10, B = 22;
  const xs = pts.map((x) => x.t), lo = Math.min(...pts.map((x) => x.p), d.unit), hi = Math.max(...pts.map((x) => x.p), d.market);
  const pad = (hi - lo) * 0.12 || hi * 0.05, y0 = lo - pad, y1 = hi + pad;
  const X = (t) => L + (t - xs[0]) / Math.max(1, xs[xs.length - 1] - xs[0]) * (W - L - R);
  const Y = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
  const line = pts.map((x, i) => (i ? "L" : "M") + X(x.t).toFixed(1) + " " + Y(x.p).toFixed(1)).join(" ");
  const area = line + ` L${X(xs[xs.length - 1]).toFixed(1)} ${H - B} L${X(xs[0]).toFixed(1)} ${H - B} Z`;
  const lvl = (v, color, label) => `<line x1="${L}" x2="${W - R + 4}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}" stroke="${color}" stroke-width="1.5" stroke-dasharray="4 4"/><text x="${W - R + 10}" y="${(Y(v) + 4).toFixed(1)}" fill="${color}" font-size="12.5" font-weight="600">${label}</text>`;
  const day = (t) => new Date(t * 1000).toLocaleDateString("ru-RU", {day: "2-digit", month: "2-digit"});
  const short = (v) => v >= 1e6 ? n1(v / 1e6) + " млн" : v >= 1e4 ? Math.round(v / 1e3) + " тыс." : Math.round(v).toLocaleString("ru-RU");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Цена за неделю: сейчас ${esc(rub(pts[pts.length - 1].p))} за штуку">
    <path d="${area}" fill="var(--surface-2)"/>
    <path d="${line}" fill="none" stroke="var(--muted)" stroke-width="2" stroke-linejoin="round"/>
    ${lvl(d.market, "var(--amber-text)", "продать " + short(d.market))}
    ${lvl(d.unit, "var(--good)", "купить " + short(d.unit))}
    <text x="${L}" y="${H - 4}" fill="var(--faint)" font-size="12">${day(xs[0])}</text>
    <text x="${W - R}" y="${H - 4}" fill="var(--faint)" font-size="12" text-anchor="end">сейчас</text>
  </svg><div class="cap">Медиана сделок за штуку${isArtefact(d) ? " — того же качества и заточки" : ""}, по 12 часов.</div>`;
}
function hoursChart(hours) {
  const total = (hours || []).reduce((a, b) => a + b, 0);
  if (total < 12) return "";
  const W = 400, H = 76, B = 18, max = Math.max(...hours), bw = W / 24;
  let best = 0, at = 0;
  for (let h = 0; h < 24; h++) { const s = hours[h] + hours[(h + 1) % 24] + hours[(h + 2) % 24]; if (s > best) { best = s; at = h; } }
  const hot = new Set([at, (at + 1) % 24, (at + 2) % 24]);
  const bars = hours.map((v, h) => { const bh = Math.max(2, v / max * (H - B - 4)); return `<rect x="${(h * bw + 1.5).toFixed(1)}" y="${(H - B - bh).toFixed(1)}" width="${(bw - 3).toFixed(1)}" height="${bh.toFixed(1)}" rx="2" fill="${hot.has(h) ? "var(--amber)" : "var(--line-2)"}"/>`; }).join("");
  const ticks = [0, 6, 12, 18].map((h) => `<text x="${(h * bw + bw / 2).toFixed(1)}" y="${H - 3}" fill="var(--faint)" font-size="12" text-anchor="middle">${h}</text>`).join("");
  return `<h3>Когда покупают</h3><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Сделки по часам суток">${bars}${ticks}</svg>
    <div class="cap">Чаще всего — с ${at} до ${(at + 3) % 24} ч (по времени этого компьютера, сделки за 2 недели). Выставляй лот перед этим.</div>`;
}
async function loadItemStats(d) {
  let q = "";
  if (isArtefact(d) && d.quality !== null && d.quality !== undefined) q = `&q=${d.quality}&p=${d.ptn ?? 0}`;
  try {
    const r = await api(`/api/item_stats?id=${encodeURIComponent(d.item_id)}${q}`);
    if (selected !== d.id || !$("dChart")) return;
    $("dChart").innerHTML = "<h3>Цена за неделю</h3>" + priceChart(r.series, d);
    $("dHours").innerHTML = hoursChart(r.hours);
  } catch (e) { if ($("dChart")) $("dChart").innerHTML = ""; }
}

function rareMarks() { return (S.settings.rare_items || []).map((x) => String(x).toLowerCase().replace(/ё/g, "е")); }
function isStarred(id, name) { const m = rareMarks(); return m.includes(String(id).toLowerCase()) || (name && m.includes(name.toLowerCase().replace(/ё/g, "е").replace(/[«»]/g, ""))); }
async function toggleStar(id, name) {
  let list = (S.settings.rare_items || []).slice();
  const marks = rareMarks(), on = isStarred(id, name);
  if (on) list = list.filter((x, i) => marks[i] !== String(id).toLowerCase() && marks[i] !== (name || "").toLowerCase().replace(/ё/g, "е").replace(/[«»]/g, ""));
  else list.push(id || name);
  const r = await api("/api/settings", {rare_items: list});
  toast(r.ok ? (on ? "Звёздочка снята: " : "★ Особо редкий: ") + (name || id) : r.message, !r.ok);
  await refresh();
}
function openDrawer(id) {
  const d = S.deals.find((x) => x.id === id); if (!d) return;
  selected = id; renderDeals(true);
  const bid = d.kind === "bid", star = isStarred(d.item_id, d.name);
  const sub = [gradeText(d), rankText(d), d.cat && CATNAMES[d.cat] ? CATNAMES[d.cat] : "", d.amount + " шт"].filter(Boolean).join(" · ");
  $("drawer").innerHTML = `
    <button class="close" id="dClose" aria-label="Закрыть">✕</button>
    <div class="dhead">${slot(d.item_id, d.name, tone(d), "lg")}<div style="min-width:0">
      <h2>${esc(d.name)}</h2>
      <div class="muted">${esc(sub)}</div>
      <div class="tags" style="margin-top:6px">${dealTags(d, S.now)}</div>
    </div></div>
    <div class="bigprofit num">+${rub(d.profit)}</div>
    <div class="muted">возможная прибыль · ${Math.round(d.roi)}% к вложенному · дешевле рынка на ${Math.round(d.pct)}%</div>
    <div class="calc num">
      <div><span>${bid ? (d.has_bids ? "Текущая ставка" : "Стартовая цена") : "Купить"}<small>${d.amount} шт по ${rub(d.unit)}</small></span><span>${rub(d.cost)}</span></div>
      <div><span>Продать<small>по ~${rub(d.market)} за шт</small></span><span>${rub(d.resale)}</span></div>
      <div><span>Комиссия аукциона 5%</span><span>−${rub(d.resale * 0.05)}</span></div>
      <div><span>Прибыль</span><span>+${rub(d.profit)}</span></div>
    </div>
    ${d.bought ? `<div class="note ok">✓ Отмечено как купленное — цена и шанс продажи теперь во вкладке «Мои покупки».</div>`
      : `<div class="buybox"><input class="field num" id="dPaid" value="${Math.round(d.cost)}" title="Сколько заплатил за весь лот"><button class="btn primary" id="dBuy">✓ Я купил</button></div>
         <div class="muted small" style="margin-top:6px">Впиши, сколько реально заплатил, — трекер будет следить за ценой и считать прибыль.</div>`}
    ${d.fate === "sold" ? `<div class="note warn">Этот лот уже купили — в истории есть сделка ровно на него.</div>`
      : d.gone && !d.bought ? `<div class="note warn">Этого лота больше нет на аукционе${d.fate === "removed" ? " — его сняли" : d.fate === "expired" ? " — время вышло" : " — сверяю с историей сделок, купили его или сняли"}.</div>` : ""}
    ${d.stale && !d.gone ? `<div class="note warn">${esc(d.stale)}</div>` : ""}
    ${bid ? `<div class="note">Ставь не выше <b>${rub(d.max_bid)}</b> за весь лот — тогда прибыль будет не меньше минимальной из настроек.</div>` : ""}
    ${chanceBlock(d.chance_info)}
    <div class="sect chart" id="dChart"><h3>Цена за неделю</h3><div class="muted">Загружаю…</div></div>
    <div class="sect chart" id="dHours"></div>
    <div class="facts">
      <div class="fact"><div class="l">Цена по сделкам${d.window_h ? " за " + fmtWindow(d.window_h) : ""}</div><div class="v num">${rub(d.hist)}/шт</div></div>
      <div class="fact"><div class="l">${d.exact ? "Такой же или лучше" : "Дешевле всего"} на аукционе</div><div class="v num">${d.floor ? rub(d.floor) + "/шт" : "нет"}</div></div>
      <div class="fact"><div class="l">Выставлен</div><div class="v">${ago(d.listed, S.now)}</div></div>
      <div class="fact"><div class="l">Активен до</div><div class="v">${until(d.ends)}</div></div>
      <div class="fact"><div class="l">Сделок в расчёте</div><div class="v num">${d.n_sales}</div></div>
      <div class="fact"><div class="l">Цена за сутки</div><div class="v num" style="color:${d.trend == null ? "inherit" : d.trend <= -5 ? "var(--bad)" : d.trend >= 5 ? "var(--good)" : "inherit"}">${d.trend == null ? "мало данных" : (d.trend > 0 ? "+" : d.trend < 0 ? "−" : "") + Math.abs(Math.round(d.trend)) + "% к прошлым дням"}</div></div>
    </div>
    <div class="note">${d.floor && d.floor * 0.99 < d.hist
      ? "Перепродать дороже самого дешёвого такого же лота не выйдет, поэтому цена продажи — чуть ниже него, а не по прошлым сделкам."
      : d.floor ? "Цена продажи — по прошлым сделкам: такие же лоты на аукционе сейчас дороже."
      : "Такого же или лучше лота на аукционе сейчас нет — цена продажи только по прошлым сделкам, это менее надёжно."} Данные API запаздывают — проверь лот в игре перед покупкой.</div>
    ${isArtefact(d) ? `<div class="note">Артефакт: цена зависит ещё от процента качества и доп. свойств — сравни лот в игре с другими того же качества и заточки.</div>` : ""}
    ${["armor", "weapon"].includes(d.cat) ? `<div class="note">Цена брони и оружия сильно зависит от заточки и состояния — сравни лот в игре с такими же.</div>` : ""}
    <div class="actions"><button class="btn primary" id="dCopy">Скопировать название</button><button class="btn" id="dStar">${star ? "★ Особо редкий" : "☆ Особо редкий"}</button><button class="btn ghost" id="dHide">Скрыть находку</button></div>`;
  $("drawer").classList.add("on");
  $("dClose").onclick = closeDrawer;
  $("dCopy").onclick = () => copyText(d.name);
  $("dStar").onclick = async () => { await toggleStar(d.item_id, d.name); openDrawer(d.id); };
  $("dHide").onclick = async () => { await api("/api/deals/remove", {id: d.id}); closeDrawer(); refresh(); };
  if ($("dBuy")) $("dBuy").onclick = async () => {
    const r = await api("/api/purchases/add", {deal_id: d.id, paid: $("dPaid").value.replace(/\s/g, "").replace(",", ".")});
    toast(r.message, !r.ok); await refresh(); if (r.ok) openDrawer(d.id);
  };
  loadItemStats(d);
}
function closeDrawer() { $("drawer").classList.remove("on"); if (selected !== null) { selected = null; if (S) renderDeals(true); } }
function copyText(t, msg) {
  const done = () => toast(msg || "Скопировано — вставь в поиск аукциона в игре");
  if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(t).then(done, () => fallback()); } else fallback();
  function fallback() { const a = document.createElement("textarea"); a.value = t; document.body.appendChild(a); a.select(); try { document.execCommand("copy"); done(); } catch (e) {} a.remove(); }
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

// ---------- предметы ----------
function watch() { return S ? S.settings.watch.slice() : []; }
async function saveWatch(list, msg, warn) { const r = await api("/api/settings", {watch: list}); toast(r.ok ? (msg || "Список обновлён") : r.message, !r.ok || !!warn); await refresh(); }
const normName = (n) => String(n || "").toLowerCase().replace(/ё/g, "е").replace(/[«»]/g, "").trim();
function entryName(w) { return CATMAP[w] ? CATMAP[w].name : w; }
function inWatch(e) { return watch().some((w) => w === e.id || normName(w) === normName(e.name)); }
function addItem(name, unknown) {
  name = (name || "").trim(); if (!name) return;
  const list = watch();
  if (list.some((x) => normName(entryName(x)) === normName(name))) { toast("Уже в списке"); return; }
  list.push(name);
  saveWatch(list, unknown ? "«" + name + "» нет в базе игры — проверь написание" : "Добавлено: " + name, unknown);
}
function addEntry(e) {
  const list = watch();
  if (inWatch(e)) { toast("Уже в списке"); return; }
  // одинаковые названия бывают у разных предметов — тогда храним id
  const dup = CAT && CAT.filter((x) => normName(x.name) === normName(e.name)).length > 1;
  list.push(dup ? e.id : e.name);
  saveWatch(list, "Добавлено: " + e.name);
}
function removeEntry(e) { saveWatch(watch().filter((w) => w !== e.id && normName(w) !== normName(e.name)), "Убрано: " + e.name); }
function autoCount() { return (S.auto_cats || []).reduce((s, c) => s + (S.cat_counts[c] || (c === "artefact" ? S.artifacts : 0) || 0), 0); }
function watchTotal() { return watch().length + (S ? autoCount() : 0); }
function entryTone(e) { return e.rank && RANK_Q[e.rank] && e.cat !== "artefact" ? `var(--q${RANK_Q[e.rank]})` : "var(--q0)"; }
async function loadCatalog() {
  if (CAT || Date.now() - catLoading < 4000) return;
  catLoading = Date.now();
  try {
    const r = await api("/api/catalog");
    if (r.items && r.items.length) {
      CAT = r.items; CATNAMES = r.names || {}; CATMAP = {};
      CAT.forEach((e) => { CATMAP[e.id] = e; e._k = searchKey(e.name, (CATNAMES[e.cat] || "") + " " + (RANK_RU[e.rank] || "") + (e.barter ? " бартер" : "")); });
      renderCatalog(true); renderChips(true);
    }
  } catch (e) {}
}
function renderTabs() {
  const counts = {};
  const visible = (CAT || []).filter((e) => e.trade && (showBarter || !e.barter));
  visible.forEach((e) => counts[e.cat] = (counts[e.cat] || 0) + 1);
  const order = ["all", "artefact", "armor", "weapon", "parts", "tools", "attachment", "misc", "supply", "bullet", "containers", "backpacks", "grenade", "other"];
  $("catTabs").innerHTML = order.filter((c) => c === "all" || counts[c]).map((c) =>
    `<button data-c="${c}" class="${c === catTab ? "on" : ""}">${c === "all" ? "Все" : esc(CATNAMES[c] || c)}<span>${c === "all" ? visible.length : counts[c]}</span></button>`).join("")
    + `<button id="barterBtn" class="${showBarter ? "on" : ""}" title="Предметы, которые получают бартером у торговцев">${showBarter ? "Бартерные показаны" : "+ бартерные"}</button>`;
  $("barterBtn").onclick = () => { showBarter = !showBarter; store.set("showBarter", showBarter); renderCatalog(true); };
  $("catTabs").querySelectorAll("button[data-c]").forEach((b) => b.onclick = () => { catTab = b.dataset.c; store.set("catTab", catTab); renderCatalog(); $("catResults").scrollTop = 0; });
}
let lastCatSig = "";
function renderCatalog(force) {
  if (!CAT) return;
  const sig = [catTab, showBarter, $("catSearch").value, watch().join("|"), (S.settings.rare_items || []).join("|")].join("#");
  if (!force && sig === lastCatSig) return;
  lastCatSig = sig;
  renderTabs();
  const qv = prepQuery($("catSearch").value);
  let list = CAT.filter((e) => e.trade && (showBarter || !e.barter) && (catTab === "all" || e.cat === catTab));
  if (qv) list = list.map((e) => [matchScore(qv, e._k), e]).filter((x) => x[0] > 0)
    .sort((a, b) => b[0] - a[0] || a[1].name.localeCompare(b[1].name, "ru")).map((x) => x[1]);
  else list.sort((a, b) => a.name.localeCompare(b.name, "ru"));
  const shown = list.slice(0, 120);
  $("catResults").innerHTML = shown.map((e) => {
    const on = inWatch(e), star = isStarred(e.id, e.name);
    return `<div class="res">${slot(e.id, e.name, entryTone(e), "sm")}
      <span class="n">${esc(e.name)}</span>${e.rank && RANK_RU[e.rank] && e.cat !== "artefact" ? `<span class="rk" style="color:${entryTone(e)}">${RANK_RU[e.rank]}</span>` : ""}
      ${e.barter ? `<span class="tag" title="Получают бартером у торговцев">бартер</span>` : ""}<span class="tag cat">${esc(CATNAMES[e.cat] || e.cat)}</span>
      <button class="star${star ? " on" : ""}" data-star="${e.id}" title="Особо редкий — отдельное уведомление">${star ? "★" : "☆"}</button>
      <button class="btn sm${on ? " done" : ""}" data-add="${e.id}">${on ? "✓ В списке" : "+ Следить"}</button></div>`;
  }).join("") || `<div class="res muted">Ничего не нашёл — попробуй часть названия или другую вкладку.</div>`;
  $("catMore").textContent = list.length > shown.length ? `Показано ${shown.length} из ${list.length} — уточни поиск.` : (list.length ? `Найдено: ${list.length}` : "");
  $("catResults").querySelectorAll("[data-add]").forEach((b) => b.onclick = () => { const e = CATMAP[b.dataset.add]; inWatch(e) ? removeEntry(e) : addEntry(e); });
  $("catResults").querySelectorAll("[data-star]").forEach((b) => b.onclick = async () => { const e = CATMAP[b.dataset.star]; await toggleStar(e.id, e.name); renderCatalog(); });
}
$("catSearch").oninput = () => { clearTimeout(renderCatalog.t); renderCatalog.t = setTimeout(() => renderCatalog(), 90); };
$("catSearch").onkeydown = (e) => {
  if (e.key !== "Enter" || !CAT) return;
  const qv = prepQuery($("catSearch").value); if (!qv) return;
  let best = null, score = 0;   // Enter — добавить лучшее совпадение
  CAT.forEach((x) => { if (!x.trade) return; const sc = matchScore(qv, x._k); if (sc > score) { score = sc; best = x; } });
  if (best) addEntry(best); else toast("Не нашёл такого предмета", true);
};
let lastChipsSig = "";
function renderChips(force) {
  const list = watch(), cats = S.auto_cats || [];
  const sig = JSON.stringify([list, S.settings.rare_items || [], !!CAT]);
  if (force || sig !== lastChipsSig) {
    lastChipsSig = sig;
    $("chips").innerHTML = list.map((w, i) => {
      const e = CATMAP[w] || (CAT || []).find((x) => normName(x.name) === normName(w));
      const name = e ? e.name : w, star = isStarred(e ? e.id : w, name);
      return `<span class="chip">${e ? slot(e.id, name, entryTone(e), "xs") : ""}<button class="star${star ? " on" : ""}" data-s="${i}" title="Особо редкий">${star ? "★" : "☆"}</button>${esc(name)}${e && e.cat !== "artefact" && CATNAMES[e.cat] ? ` <span class="muted small">${esc(CATNAMES[e.cat])}</span>` : ""}<button title="Убрать" data-i="${i}">✕</button></span>`;
    }).join("");
    $("chips").querySelectorAll("[data-i]").forEach((b) => b.onclick = () => { const l = watch(); l.splice(+b.dataset.i, 1); saveWatch(l, "Убрано"); });
    $("chips").querySelectorAll("[data-s]").forEach((b) => b.onclick = () => {
      const w = watch()[+b.dataset.s], e = CATMAP[w] || (CAT || []).find((x) => normName(x.name) === normName(w));
      toggleStar(e ? e.id : w, e ? e.name : w);
    });
  }
  $("chipsEmpty").style.display = list.length ? "none" : "block";
  $("chipsEmpty").textContent = cats.length === 1 && cats[0] === "artefact" ? "Свой список пуст — проверяются только все артефакты."
    : cats.length ? "Свой список пуст — проверяются только категории целиком." : "Список пуст.";
  $("watchCnt").textContent = list.length ? "· " + list.length : "";
  $("cntItems").textContent = watchTotal() || "";
  document.querySelectorAll("[data-cat]").forEach((el) => el.checked = cats.includes(el.dataset.cat));
  const arts = S.cat_counts.artefact || S.artifacts;
  $("artSub").textContent = arts ? `все ${arts} ${plural(arts, ["артефакт", "артефакта", "артефактов"])} из базы игры` : "все артефакты из базы игры";
  document.querySelectorAll("[data-cnt]").forEach((el) => {
    const n = S.cat_counts[el.dataset.cnt];
    el.textContent = n ? `${n} ${plural(n, ["предмет", "предмета", "предметов"])}${n > 100 ? " · круг станет длиннее на ~" + Math.max(1, Math.round(n * 1.1 / 380 * 60)) + " с" : ""}` : "";
  });
  if (CAT && view === "items") renderCatalog();
}
document.querySelectorAll("[data-cat]").forEach((el) => el.onchange = async () => {
  const cats = [...document.querySelectorAll("[data-cat]")].filter((x) => x.checked).map((x) => x.dataset.cat);
  const r = await api("/api/settings", {auto_categories: cats});
  const name = el.closest(".catrow").querySelector("b").textContent;
  if (!r.ok) toast(r.message, true);
  else toast(el.checked ? (el.dataset.cat === "artefact" ? "Все артефакты включены" : name + ": включено целиком") : (el.dataset.cat === "artefact" ? "Все артефакты выключены" : name + ": выключено"));
  refresh();
});
// ---------- мои покупки ----------
$("bSeg").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; bFilter = b.dataset.b; store.set("bFilter", bFilter); renderPurchases(true); };
function pUnit(p) { return p.cur_market || p.target; }
function pExpected(p) { return pUnit(p) * p.amount * (1 - S.settings.fee) - p.paid; }
const STATUS_RU = {holding: "в инвентаре", listed: "выставлен", sold: "продан"};
let lastBuysSig = "";
function renderPurchases(force) {
  const all = S.purchases || [];
  [...$("bSeg").children].forEach((x) => x.classList.toggle("on", x.dataset.b === bFilter));
  const open = all.filter((p) => p.status !== "sold"), sold = all.filter((p) => p.status === "sold");
  const sum = (a, f) => a.reduce((s, p) => s + f(p), 0);
  $("bInv").textContent = rub(sum(open, (p) => p.paid)); $("bInvS").textContent = open.length + " " + plural(open.length, ["покупка", "покупки", "покупок"]) + " не продано";
  const exp = sum(open, pExpected); $("bExp").textContent = (exp >= 0 ? "+" : "−") + rub(Math.abs(exp));
  $("bExp").className = "v num " + (exp >= 0 ? "good" : "neg");
  const earn = sum(sold, (p) => p.profit || 0); $("bEarn").textContent = (earn >= 0 ? "+" : "−") + rub(Math.abs(earn));
  $("bEarn").className = "v num " + (earn >= 0 ? "good" : "neg");
  $("bSold").textContent = sold.length; $("bSoldS").textContent = sold.length ? `в плюс — ${sold.filter((p) => (p.profit || 0) > 0).length}` : "сделок";
  $("cntBuys").textContent = open.length || "";
  const list = all.filter((p) => bFilter === "all" || (bFilter === "open" ? p.status !== "sold" : p.status === "sold"));
  if (document.activeElement && $("bRows").contains(document.activeElement) && document.activeElement.tagName === "INPUT") return;
  const sig = JSON.stringify([list, sellOpen, bFilter, Math.floor(S.now / 60)]);
  if (!force && sig === lastBuysSig) return;
  lastBuysSig = sig;
  $("bRows").innerHTML = list.map((p) => {
    const unit = pUnit(p), profit = p.status === "sold" ? (p.profit || 0) : pExpected(p);
    const c = p.cur_chance;
    const fresh = p.cur_at ? `<small class="muted" style="display:block;font-size:12px">${p.cur_market ? "цена " + ago(new Date(p.cur_at * 1000).toISOString(), S.now) : "рынка сейчас нет"}</small>` : `<small class="muted" style="display:block;font-size:12px">на момент покупки</small>`;
    const actions = p.status === "sold" ? `<button class="btn sm" data-reopen="${p.id}">Вернуть</button>`
      : sellOpen === p.id ? `<span class="inline"><input class="field num" id="sellPrice" value="${Math.round(unit * p.amount)}" title="За сколько продал весь лот"><button class="btn sm primary" data-sold="${p.id}">Сохранить</button></span>`
      : `${p.status === "holding" ? `<button class="btn sm" data-listed="${p.id}">Выставил</button>` : `<button class="btn sm" data-hold="${p.id}">Снял</button>`}<button class="btn sm" data-sell="${p.id}">Продал…</button>`;
    return `<tr><td><div class="item">${slot(p.item_id, p.name, tone(p), "sm")}<div><span class="n">${esc(p.name)}</span><div class="tags"><span class="status ${p.status}">${STATUS_RU[p.status] || p.status}</span>${p.rare ? `<span class="tag rare">💎</span>` : ""}${gradeTag(p)}</div><span class="when">куплено ${ago(new Date(p.bought_at * 1000).toISOString(), S.now)}</span></div></div></td>
      <td class="num">${p.amount} шт</td>
      <td class="num">${rub(p.paid)}<small class="muted" style="display:block;font-size:12px">${rub(p.unit_paid)}/шт</small></td>
      <td class="num">${p.status === "sold" ? rub(p.sold_price) + `<small class="muted" style="display:block;font-size:12px">продал за весь лот</small>` : rub(unit) + "/шт" + fresh}</td>
      <td class="num ${profit >= 0 ? "profit" : "neg"}" style="font-size:16px">${profit >= 0 ? "+" : "−"}${rub(Math.abs(profit))}</td>
      <td>${p.status === "sold" ? "" : chanceCell(c ? c.chance : null, c ? c.hours : null)}</td>
      <td><span class="inline">${actions}<button class="btn sm ghost" data-del="${p.id}" title="Удалить запись">✕</button></span></td></tr>`
      + (p.status === "sold" ? "" : sellHelp(p));
  }).join("");
  const empty = !list.length;
  $("bEmpty").style.display = empty ? "grid" : "none";
  if (empty && all.length) { $("bEmptyH").textContent = bFilter === "sold" ? "Пока ничего не продано" : "Всё продано"; $("bEmptyT").textContent = "Переключи фильтр сверху, чтобы увидеть остальные."; }
  else if (empty) { $("bEmptyH").textContent = "Пока нет покупок"; $("bEmptyT").textContent = "Купил лот из находок — открой его и нажми «Я купил». Трекер будет следить за его ценой и шансом продажи."; }
  const upd = async (body) => { const r = await api("/api/purchases/update", body); if (!r.ok) toast(r.message, true); else sellOpen = null; await refresh(); renderPurchases(true); };
  $("bRows").querySelectorAll("[data-listed]").forEach((b) => b.onclick = () => { const f = document.querySelector(`[data-lp="${b.dataset.listed}"]`); if (f) { f.focus(); f.select(); } else upd({id: b.dataset.listed, status: "listed"}); });
  $("bRows").querySelectorAll("[data-opt]").forEach((b) => b.onclick = () => { const f = document.querySelector(`[data-lp="${b.dataset.opt}"]`); if (f) { f.value = b.dataset.total; f.focus(); } });
  $("bRows").querySelectorAll("[data-list]").forEach((b) => b.onclick = () => {
    const f = document.querySelector(`[data-lp="${b.dataset.list}"]`);
    upd({id: b.dataset.list, list_price: (f ? f.value : "").replace(/\s/g, "").replace(",", ".")});
  });
  $("bRows").querySelectorAll("[data-hold]").forEach((b) => b.onclick = () => upd({id: b.dataset.hold, status: "holding"}));
  $("bRows").querySelectorAll("[data-reopen]").forEach((b) => b.onclick = () => upd({id: b.dataset.reopen, status: "holding"}));
  $("bRows").querySelectorAll("[data-sell]").forEach((b) => b.onclick = () => { sellOpen = b.dataset.sell; renderPurchases(true); const f = $("sellPrice"); if (f) { f.focus(); f.select(); } });
  $("bRows").querySelectorAll("[data-sold]").forEach((b) => b.onclick = () => upd({id: b.dataset.sold, status: "sold", sold_price: $("sellPrice").value.replace(/\s/g, "").replace(",", ".")}));
  $("bRows").querySelectorAll("[data-del]").forEach((b) => b.onclick = async () => { const r = await api("/api/purchases/remove", {id: b.dataset.del}); toast(r.message, !r.ok); await refresh(); renderPurchases(true); });
}

// ---------- помощник продажи: за сколько выставить, перебили ли ----------
const OPT_RU = {fast: "Быстро", best: "Выгодно", slow: "Дороже"};
function sellHelp(p) {
  const opts = p.options || [], ls = p.list_state, many = p.amount > 1;
  const per = (x) => rub(x) + (many ? "/шт" : "");
  const chips = opts.map((o) => `<button class="opt ${o.key}" data-opt="${p.id}" data-total="${Math.round(o.total)}" title="Подставить цену">
      <b>${OPT_RU[o.key] || ""}: ${per(o.unit)}</b><span>шанс ${Math.round(o.chance * 100)}%${o.hours ? " · " + fmtHours(o.hours) : ""} · ${o.profit >= 0 ? "+" : "−"}${rub(Math.abs(o.profit))}</span></button>`).join("");
  let state = "";
  if (p.status === "listed" && p.list_price) {
    const mine = p.list_price / p.amount;
    if (p.undercut || (ls && ls.cheaper)) {
      const best = (p.undercut && p.undercut.best) || (ls && ls.best), sug = (p.undercut && p.undercut.suggest) || (ls && ls.suggest);
      state = `<div class="ls bad">Твой лот перебили: есть лот за ${per(best)} (у тебя ${per(mine)}).${sug ? ` Чтобы продать первым — ${per(sug)}.` : ""}</div>`;
    } else if (ls && ls.own) state = `<div class="ls good">Твой лот за ${per(mine)} — самый дешёвый среди таких же. Трекер скажет, если его перебьют или он продастся.</div>`;
    else state = `<div class="ls">Выставлен за ${rub(p.list_price)}${many ? " за весь лот" : ""}. Трекер ещё не видел его на аукционе — новые лоты появляются в API примерно через 10 минут.</div>`;
  }
  if (!opts.length && !state) return `<tr class="sellrow"><td colspan="7"><span class="muted small">${p.cur_at ? "Подсказать цену не по чему: мало сделок по этому предмету." : "Подсказка, за сколько выставить, появится, когда поиск проверит этот предмет."}</span></td></tr>`;
  const listVal = Math.round(p.list_price || (opts.find((o) => o.key === "best") || opts[0] || {}).total || p.paid);
  return `<tr class="sellrow"><td colspan="7"><div class="sell">
    ${state}
    ${opts.length ? `<div class="opts"><span class="muted small">${p.status === "listed" ? "Перевыставить:" : "За сколько выставить:"}</span>${chips}</div>` : ""}
    <span class="inline"><input class="field num" data-lp="${p.id}" value="${listVal}" title="Цена за весь лот"><button class="btn sm${p.status === "listed" ? "" : " primary"}" data-list="${p.id}">${p.status === "listed" ? "Перевыставил" : "Выставил за эту цену"}</button></span>
  </div></td></tr>`;
}
function renderAccuracy() {
  const a = S.status.accuracy, sold = (S.purchases || []).filter((p) => p.status === "sold");
  let html = "";
  if (sold.length) {
    const exp = sold.reduce((x, p) => x + (p.expected || 0), 0), got = sold.reduce((x, p) => x + (p.profit || 0), 0);
    html += `<p>Твои продажи: трекер обещал <b class="num">${exp >= 0 ? "+" : "−"}${rub(Math.abs(exp))}</b>, вышло <b class="num ${got >= 0 ? "pos" : "neg"}">${got >= 0 ? "+" : "−"}${rub(Math.abs(got))}</b> по ${sold.length} ${plural(sold.length, ["сделке", "сделкам", "сделкам"])}.</p>`;
  }
  if (!a) html += `<p class="muted">Сверка по рынку появится через несколько часов работы поиска: нужно, чтобы после находок прошли продажи таких же лотов.</p>`;
  else {
    const pct = Math.round(a.ratio * 100), hit = Math.round(a.hit * 100);
    html += `<p>По ${a.n} ${plural(a.n, ["находке", "находкам", "находкам"])} за неделю такие же лоты потом продавали в среднем за <b>${pct}%</b> от оценки трекера; оценка сбылась у <b>${hit}%</b>.
      ${a.factor < 0.995 ? `Поэтому оценка перепродажи сейчас снижена на <b>${Math.round((1 - a.factor) * 100)}%</b>${S.settings.calibrate === false ? " — но поправка выключена в «Настройках»" : ""}.` : a.n < 15 ? "Для поправки нужно хотя бы 15 сверенных находок." : "Поправка не нужна."}</p>`;
    html += `<div class="accrows">${a.rows.map((r) => { const d = Math.round((r.fact / r.pred - 1) * 100);
      return `<div><span>${esc(r.name)}${r.kind === "near" ? ' <span class="muted small">(почти находка)</span>' : ""}</span><span class="num muted">оценка ${rub(r.pred)}</span><span class="num ${d >= -3 ? "pos" : "neg"}">факт ${rub(r.fact)} (${d > 0 ? "+" : ""}${d}%)</span></div>`; }).join("")}</div>`;
  }
  const sig = JSON.stringify([a && a.at, sold.length, S.settings.calibrate]);
  if (sig !== renderAccuracy.sig) { renderAccuracy.sig = sig; $("accBody").innerHTML = html; }
}

// ---------- что приносят предметы списка ----------
async function loadYield() {
  loadYield.at = Date.now();
  let r;
  try { r = await api("/api/yield"); } catch (e) { return; }
  if (!r || !r.ok) return;
  const rows = r.rows, empty = rows.filter((x) => x.status === "empty"), good = rows.filter((x) => x.status === "good");
  $("yieldBox").hidden = !rows.length;
  if (!rows.length) return;
  const share = r.total ? Math.round(empty.length / r.total * 100) : 0;
  $("yieldSub").textContent = good.length || empty.length
    ? `За неделю: ${good.length} ${plural(good.length, ["предмет дал", "предмета дали", "предметов дали"])} находки, на которые можно было успеть; ${empty.length} — ни одного лота дешевле рынка.`
    : "Нужны хотя бы сутки поиска, чтобы понять, какие предметы приносят находки.";
  const line = (x) => `<div class="yrow"><span class="n">${esc(x.name)}</span><span class="muted small num">${x.status === "good"
      ? `${x.catch} ${plural(x.catch, ["лот успеть", "лота успеть", "лотов успеть"])}${x.deal ? ` · находок ${x.deal}` : ""}`
      : `${x.lots} ${plural(x.lots, ["лот", "лота", "лотов"])} за ${Math.round(x.hours)} ч — дешевле рынка ни одного`}</span></div>`;
  $("yieldBody").innerHTML = (good.length ? `<div class="ylist"><b class="small">Приносят больше всего</b>${good.slice(0, 8).map(line).join("")}</div>` : "")
    + (empty.length ? `<div class="ylist"><b class="small">Пустые</b>${empty.slice(0, 8).map(line).join("")}${empty.length > 8 ? `<div class="muted small">и ещё ${empty.length - 8}</div>` : ""}</div>
      <div class="linkrow"><button class="btn" id="yieldDrop">Убрать пустые (${empty.length})</button><span class="muted small">круг станет короче примерно на ${share}% — остальные предметы будут проверяться чаще</span></div>` : "");
  const b = $("yieldDrop");
  if (b) b.onclick = async () => {
    const res = await api("/api/watch/remove", {ids: empty.map((x) => x.id)});
    toast(res.message, !res.ok); await refresh(); loadYield();
  };
}

// ---------- калькулятор крафта ----------
let CR = null;
const FEAT_RU = {workbench: "верстак", centrifuge: "центрифуга", tool_trolley: "тележка с инструментами", laboratory_table: "лабораторный стол",
  rotary_evaporator: "роторный испаритель", chemical_reactor: "химический реактор", precise_tools: "точные инструменты", cnc: "станок ЧПУ",
  flasks_kit: "набор колб", hoods: "вытяжка", kitchen_items: "кухонная утварь", stove: "плита", welding_equipment: "сварка", lathe: "токарный станок",
  fermentation_container: "ёмкость для брожения", precise_powertools: "точный электроинструмент", sterilization_system: "стерилизатор",
  chromatographic_equipment: "хроматограф", kitchen_table: "кухонный стол", electronics_kit: "набор электроники", gauze_filter: "марлевый фильтр",
  laminar_box: "ламинарный бокс", calipers_kit: "штангенциркули", scalpels_kit: "скальпели", screwdrivers: "отвёртки", wrenches_kit: "гаечные ключи",
  laser_level: "лазерный уровень", generator_energy_source_battery: "генератор: аккумулятор", water_collector: "сборщик воды",
  generator_energy_source_anomal: "генератор: аномальный источник"};
async function loadCraft() {
  loadCraft.at = Date.now();
  let r;
  try { r = await api("/api/craft"); } catch (e) { return; }
  if (!r.ok) { $("advice").innerHTML = `<div class="muted">${esc(r.message || "Не получилось загрузить рецепты")}</div>`; return; }
  CR = r; renderSkills(); renderCraft();
}
function renderSkills() {
  if (!CR || document.activeElement && $("skills").contains(document.activeElement)) return;
  $("skills").innerHTML = CR.perks.map((p) => `<label class="skill"><span>${esc(p.name)}</span><select class="field" data-perk="${p.id}">${[0, 1, 2, 3, 4, 5].map((l) => `<option value="${l}"${l === p.level ? " selected" : ""}>${l || "нет"}</option>`).join("")}</select></label>`).join("");
  $("skills").querySelectorAll("select").forEach((sel) => sel.onchange = async () => {
    const skills = {}; $("skills").querySelectorAll("select").forEach((x) => skills[x.dataset.perk] = +x.value);
    const res = await api("/api/settings", {skills}); if (!res.ok) toast(res.message, true);
    sel.blur(); loadCraft();
  });
}
function crName(id) { return (CR.names && CR.names[id]) || id; }
function renderCraft() {
  if (!CR) return;
  const q = normQ($("crSearch").value), mine = $("crMine").checked, key = $("crSort").value;
  const perkName = Object.fromEntries(CR.perks.map((p) => [p.id, p.name]));
  let rows = CR.rows.filter((r) => (!mine || r.available) && (!q || [...r.result, ...r.ingredients].some(([i]) => normQ(crName(i)).includes(q))));
  const v = (r) => key === "energy" ? (r.per_energy ?? -1e12) : key === "name" ? 0 : (r.profit ?? -1e12);
  rows.sort((a, b) => key === "name" ? crName(a.result[0][0]).localeCompare(crName(b.result[0][0]), "ru") : v(b) - v(a));
  const total = Object.keys(CR.names).length, priced = Object.keys(CR.prices).length;
  $("crPrices").textContent = `цены есть у ${priced} из ${total} предметов` + (CR.queued || S.status.craft_left ? ` · узнаю ещё ${CR.queued || S.status.craft_left}` : "");
  const ing = (r) => r.ingredients.map(([i, n]) => `<span class="${CR.prices[i] ? "" : "noprice"}" title="${CR.prices[i] ? rub(CR.prices[i][0]) + "/шт по " + CR.prices[i][1] + " сделкам" : CR.trade[i] === false ? "не продаётся на аукционе" : "нет цены — нажми «Узнать цены»"}">${esc(crName(i))} ×${n}</span>`).join(", ");
  $("crRows").innerHTML = rows.slice(0, 200).map((r) => {
    const [rid, rn] = r.result[0];
    const need = Object.entries(r.need || {}).map(([k, l]) => `<span class="tag bad">${esc(perkName[k] || k)} ${l}</span>`).join("");
    const req = Object.entries(r.perks).filter(([k]) => !(k in (r.need || {}))).map(([k, l]) => `<span class="tag">${esc(perkName[k] || k)} ${l}</span>`).join("");
    const feats = r.features.map((f) => FEAT_RU[f] || f).join(", ");
    const money = (x) => x == null ? `<span class="muted">—</span>` : (x >= 0 ? "+" : "−") + rub(Math.abs(x));
    return `<tr${r.profit != null && r.profit <= 0 ? ' class="loss"' : ""}>
      <td><div class="item">${slot(rid, crName(rid), "var(--q0)", "sm")}<div><span class="n">${esc(crName(rid))}${rn > 1 ? ` ×${rn}` : ""}</span><div class="tags">${need}${req}</div>${feats ? `<span class="when">нужно в убежище: ${esc(feats)}</span>` : ""}</div></div></td>
      <td class="small">${ing(r)}${r.missing.length ? `<div class="muted small">нет цены: ${r.missing.slice(0, 3).map((i) => esc(crName(i))).join(", ")}${r.missing.length > 3 ? "…" : ""}</div>` : ""}</td>
      <td class="num">${r.cost == null ? "—" : rub(r.cost)}</td>
      <td class="num">${r.value == null ? "—" : rub(r.value)}</td>
      <td class="num ${r.profit == null ? "" : r.profit >= 0 ? "profit" : "neg"}">${money(r.profit)}</td>
      <td class="num">${money(r.per_energy)}<small class="muted" style="display:block;font-size:12px">энергия ${Math.round(r.energy)}</small></td></tr>`;
  }).join("") || `<tr><td colspan="6" class="muted">${mine ? "По твоим навыкам рецептов не нашлось — поставь уровни слева или сними «Только доступные мне»." : "Ничего не найдено."}</td></tr>`;
  $("advice").innerHTML = CR.advice.filter((a) => a.best).slice(0, 6).map((a) => `<div class="adv"><b>${esc(a.name)} ${a.level} → ${a.level + 1}</b>
      <span>откроет ${a.count} ${plural(a.count, ["прибыльный рецепт", "прибыльных рецепта", "прибыльных рецептов"])}; лучший — ${esc(crName(a.best.result[0][0]))}: <b class="num pos">+${rub(a.best.profit)}</b> за крафт</span></div>`).join("")
    || `<div class="muted">${priced < total / 3 ? "Мало цен, чтобы советовать: нажми «Узнать цены» — трекер узнает их во время поиска." : "Следующие уровни навыков пока не открывают прибыльных рецептов по нынешним ценам."}</div>`;
}
$("crSearch").oninput = () => renderCraft();
$("crMine").onchange = () => renderCraft();
$("crSort").onchange = () => renderCraft();
$("crFetch").onclick = async () => { const r = await api("/api/craft/fetch", {only_available: $("crMine").checked}); toast(r.message, !r.ok); loadCraft(); };

// ---------- настройки ----------
function fillForm() {
  const c = S.settings;
  $("sDemo").checked = S.demo; $("sClientId").value = c.client_id || ""; $("sClientSecret").value = c.client_secret || "";
  $("sKeys").value = (c.extra_keys || []).map((k) => `${k.id} ${"•".repeat(10)}`).join("\n");
  $("sDiscount").value = Math.round(c.discount * 100); $("sMinProfit").value = Math.round(c.min_profit);
  $("sBids").checked = c.bids !== false; $("sBidWindow").value = c.bid_window_minutes ?? 60; $("sBidMin").value = c.bid_min_left_minutes ?? 3;
  $("sTgToken").value = c.telegram_token || ""; $("sTgChat").value = c.telegram_chat_id || ""; $("sSound").checked = store.get("sound", true);
  $("appVer").textContent = S.version || ""; $("dataDir").textContent = S.data_dir || "";
  $("sRare").checked = c.rare_enabled !== false; $("sRareQ").value = String(c.rare_quality ?? 4);
  $("sRareProfit").value = Math.round(c.rare_min_profit ?? 5000);
  $("sTheme").value = c.theme || store.get("theme", "system");
  $("sUi").value = c.ui || "new";
  $("sAutostart").checked = !!c.autostart;
}
document.querySelectorAll("#view-settings input, #view-settings select, #view-settings textarea").forEach((el) => el.addEventListener("input", () => {
  if (el.id === "sTheme" || el.id === "sSound" || el.id === "sUi") return;
  formDirty = true; $("saveHint").textContent = "Есть несохранённые изменения";
}));
$("sTheme").onchange = () => { store.set("theme", $("sTheme").value); applyTheme($("sTheme").value); api("/api/settings", {theme: $("sTheme").value}); };
$("sUi").onchange = async () => { const r = await api("/api/settings", {ui: $("sUi").value}); if (r.ok) location.reload(); else toast(r.message, true); };
$("tgTestBtn").onclick = async () => {
  toast("Отправляю тестовое сообщение…");
  const r = await api("/api/telegram/test", {telegram_token: $("sTgToken").value, telegram_chat_id: $("sTgChat").value});
  toast(r.message, !r.ok);
};
$("sSound").onchange = () => store.set("sound", $("sSound").checked);
$("openDataBtn").onclick = async () => { const r = await api("/api/open_data", {}); if (!r.ok) toast("Не получилось открыть — путь указан выше", true); };
$("updCheckBtn").onclick = async () => {
  if (formDirty) { toast("Сначала нажми «Сохранить»", true); return; }
  await api("/api/update/check", {}); toast("Проверяю обновления…"); setTimeout(refresh, 1500);
};
$("updBtn").onclick = async () => { await api("/api/update/apply", {}); toast("Скачиваю обновление…"); refresh(); };
$("saveBtn").onclick = async () => {
  const num = (id) => $(id).value.replace(/\s/g, "").replace(",", ".");
  const r = await api("/api/settings", {
    demo: $("sDemo").checked, client_id: $("sClientId").value, client_secret: $("sClientSecret").value,
    extra_keys: $("sKeys").value.split("\n"),
    discount_pct: num("sDiscount"), min_profit: num("sMinProfit"),
    bids: $("sBids").checked, bid_window_minutes: num("sBidWindow"), bid_min_left_minutes: num("sBidMin"),
    telegram_token: $("sTgToken").value, telegram_chat_id: $("sTgChat").value,
    rare_enabled: $("sRare").checked, rare_quality: $("sRareQ").value, rare_min_profit: num("sRareProfit"),
    autostart: $("sAutostart").checked, autorun_search: $("sAutostart").checked,
  });
  toast(r.ok ? "Настройки сохранены" : r.message, !r.ok);
  if (r.ok) { formDirty = false; $("saveHint").textContent = ""; }
  refresh();
};

// ---------- доступ ----------
document.querySelectorAll("[data-opendata]").forEach((b) => b.onclick = () => api("/api/open_data", {}));
$("accCopyId").onclick = () => copyText((S.access || {}).request || $("accMachine").textContent, "Код запроса скопирован — отправь его владельцу");
$("lockCopy").onclick = () => copyText((S.access || {}).request || $("lockMachine").textContent, "Код запроса скопирован — отправь его владельцу");
async function enterCode(text) {
  const r = await api("/api/access/enter", {code: text});
  toast(r.message, !r.ok);
  refresh();
  return r.ok;
}
$("lockBtn").onclick = () => enterCode($("lockCode").value);
$("accCodeBtn").onclick = async () => { if (await enterCode($("accCode").value)) $("accCode").value = ""; };
$("osCreate").onclick = async () => { const r = await api("/api/access/owner_key", {}); toast(r.message, !r.ok); refresh(); };
$("osCopy").onclick = () => copyText($("osPub").value, "Открытый ключ скопирован");
$("isBtn").onclick = async () => {
  const r = await api("/api/access/issue", {name: $("isName").value, machine: $("isMachine").value, days: $("isDays").value, seats: $("isSeats").value});
  toast(r.message, !r.ok);
  if (r.ok) { showInvite(r.code, +$("isDays").value || 0); $("isName").value = ""; $("isMachine").value = ""; }
  refresh();
};
function inviteText(code, days) {
  return `Доступ к STALZONE Трекеру${days ? ` на ${days} дн.` : ""}:\n1. Скачай программу: ${RELEASES_URL}\n2. Запусти и вставь этот код:\n${code}\n\nКлючи EXBO не нужны — находки приходят с моего сервера.`;
}
function showInvite(code, days) {
  $("isCode").value = code; $("isMsg").value = inviteText(code, days); $("isResult").hidden = false;
}
$("isCopy").onclick = () => copyText($("isMsg").value, "Сообщение скопировано — отправь его подписчику");
$("isCopyCode").onclick = () => copyText($("isCode").value, "Код скопирован");
let funnelLink = null;
$("srvFunnel").onclick = async () => {
  toast("Открываю доступ через Tailscale…");
  const r = await api("/api/server/funnel", {});
  toast(r.message, !r.ok);
  funnelLink = r.link || null; $("srvLink").hidden = !funnelLink;
  if (r.ok) srvDirty = false;
  refresh();
};
$("srvLink").onclick = () => { if (funnelLink) api("/api/open", {url: funnelLink}); };
let srvDirty = false;
$("srvSave").onclick = async () => {
  const r = await api("/api/settings", {server_enabled: $("srvOn").checked, server_url: $("srvUrl").value});
  toast(r.ok ? ($("srvOn").checked ? "Сервер включён" : "Сервер выключен") : r.message, !r.ok); srvDirty = false; refresh();
};
$("srvTest").onclick = async () => { toast("Проверяю адрес из интернета…"); const r = await api("/api/server/test", {}); toast(r.message, !r.ok); };
$("srvOn").onchange = () => { srvDirty = true; };
$("srvUrl").oninput = () => { srvDirty = true; };
function onlineText(t) {
  if (!t) return `<span class="dotx"></span><span class="muted">не подключался</span>`;
  const m = (S.now - t) / 60;
  return m < 2 ? `<span class="dotx on"></span>онлайн` : `<span class="dotx"></span><span class="muted">${ago(new Date(t * 1000).toISOString(), S.now)}</span>`;
}
function renderAccess() {
  const a = S.access || {};
  const locked = !!(a.required && !a.ok);
  $("lockOverlay").hidden = !locked;
  if (locked) { $("lockReason").textContent = a.reason || ""; $("lockMachine").textContent = a.machine || "—"; }
  $("accMachine").textContent = a.machine || "—";
  $("accStatus").textContent = !a.required ? "Закрытый доступ ещё не включён — программа открыта всем."
    : a.mode === "owner" ? "Ты владелец программы — код доступа тебе не нужен."
    : a.ok ? (a.server ? `Подписка: ${a.name}, оплачено до ${a.expires_text}. Находки приходят с сервера владельца — ключи EXBO не нужны.`
      : `Доступ открыт: ${a.name}, срок — ${a.expires_text}. Номер кода: ${a.code_id}.` + (a.shared_api ? " Ключ API — владельца (вложен в код): свои ключи не нужны." : "")) : (a.reason || "");
  $("accCodeBox").hidden = !a.required || a.mode === "owner";
  const setup = !a.embedded;                     // ключ ещё не вписан в программу
  $("ownerSetup").hidden = !(setup || a.owner);
  $("osNoKey").hidden = !setup || a.has_owner_key || !a.has_crypto;
  $("osHasKey").hidden = !(setup && a.has_owner_key);
  $("osPub").value = a.owner_public || "";
  $("sharedNote").hidden = !S.shared_api;
  $("osSub").textContent = setup ? "Закрытый доступ включается один раз: владелец создаёт личный ключ, а его открытая часть вписывается в программу."
    : "Закрытый доступ включён. Ты владелец: коды выдаёшь в карточке «Выдать доступ».";
  $("osWarn").hidden = !a.has_owner_key || !(setup || a.owner);
  const owner = a.owner && a.embedded;
  $("ownerIssue").hidden = !owner; $("ownerList").hidden = !owner; $("serverCard").hidden = !owner;
  const sv = S.server || {};
  const kw = keyLoad();
  $("keyWarn").hidden = !kw;
  if (kw) {
    const names = (a.issued || []).filter((d) => d.shared && !d.renewed && !d.expired).map((d) => d.name);
    $("keyWarnText").textContent = `Сейчас твоим ключом пользуется ещё кто-то: ~${kw.others} запросов в минуту из ${kw.limit}. Твой поиск от этого медленнее. `
      + (names.length ? `Коды с твоим ключом: ${names.join(", ")}. ` : "Так бывает, если ключ вписан во вторую копию программы или на сайт. ")
      + "Как вернуть скорость: смени Client Secret в @stalzone_api_bot и впиши новый в «Настройки» — старые коды с ключом сразу перестанут работать. Подписчикам выдай новые коды: они получают находки с твоего сервера и лимит не тратят.";
  }
  $("isWarn").hidden = !owner || !!(sv.enabled && sv.url);
  if (owner) {
    if (!srvDirty) { $("srvOn").checked = !!sv.enabled; $("srvUrl").value = sv.url || ""; }
    $("funnelCmd").textContent = "tailscale funnel --bg " + (sv.port || 8790);
    $("srvStatus").innerHTML = !sv.enabled ? "Выключен. Подписчики не получают находки."
      : sv.running ? `Работает на этом компьютере (порт ${sv.port}). Подписчиков онлайн: <b>${sv.online}</b> · в ленте находок: <b>${sv.feed}</b>`
        + `<br>Подписчики выбирают предметы сами — сервер проверяет и их${sv.sub_items ? ` (ещё <b>${sv.sub_items}</b>${(sv.sub_cats || []).length ? " и категории целиком" : ""})` : ""}. Каждая новая находка — сначала одному подписчику на 2 минуты, по очереди, потом всем.`
        + (S.status.running ? "" : `<br><b style="color:var(--amber-text)">Нажми «Начать поиск» — без проверки аукциона лента пустая.</b>`)
        + (sv.url ? "" : `<br><b style="color:var(--amber-text)">Впиши публичный адрес — без него подписчики не найдут сервер.</b>`)
      : `Не запустился: ${esc(sv.error || "")}`;
    const list = (a.issued || []).filter((d) => !d.renewed || d.blocked);
    $("issuedList").innerHTML = list.length ? ["<span class='muted'>Кто</span><span class='muted'>Оплачено до</span><span class='muted'>Сейчас</span><span></span>"]
      .concat(list.map((d) => `<span>${esc(d.name)} <span class="muted">${d.machine === "*" ? `мест занято ${d.taken || 0} из ${d.seats || 1}` : esc(d.machine)} · № ${esc(d.id)}</span>${d.shared ? ` <span class="tag bad" title="Код с твоим ключом API: его программа тратит твой лимит. Смени Client Secret, и такой код перестанет работать">ключ API — тратит твой лимит</span>` : ""}${d.blocked ? ` <span class="tag" style="color:var(--bad)">отключён</span>` : ""}</span>`
        + `<span style="${d.expired ? "color:var(--bad)" : ""}">${esc(d.expires_text)}</span><span>${onlineText(d.last_seen)}</span>`
        + `<span class="act"><button class="btn sm" data-renew="${esc(d.id)}">+30 дн.</button>${d.machine === "*" && d.taken ? `<button class="btn sm ghost" data-free="${esc(d.id)}" title="Подписчик сменил компьютер — место освободится, привяжется заново">Освободить</button>` : ""}<button class="btn sm ghost" data-block="${esc(d.id)}" data-on="${d.blocked ? 0 : 1}">${d.blocked ? "Включить" : "Отключить"}</button></span>`)).join("")
      : "<span class='muted' style='grid-column:1/-1'>Пока никому не выдавал.</span>";
    $("issuedList").querySelectorAll("[data-renew]").forEach((b) => b.onclick = async () => {
      const r = await api("/api/access/renew", {id: b.dataset.renew, days: 30});
      if (r.ok) { showInvite(r.code, 30); copyText($("isMsg").value, "Новый код и сообщение скопированы — отправь подписчику"); } else toast(r.message, true);
      refresh();
    });
    $("issuedList").querySelectorAll("[data-free]").forEach((b) => b.onclick = async () => {
      const r = await api("/api/access/free_seats", {id: b.dataset.free}); toast(r.message, !r.ok); refresh();
    });
    $("issuedList").querySelectorAll("[data-block]").forEach((b) => b.onclick = async () => {
      const r = await api("/api/access/block", {id: b.dataset.block, blocked: b.dataset.on === "1"}); toast(r.message, !r.ok); refresh();
    });
  }
  const sub = sv.role === "subscriber";
  $("feedNote").hidden = !sub; $("subItemsNote").hidden = !sub;
}

function renderKeys() {
  const st = (S && S.status) || {}, n = (S.settings.extra_keys || []).length;
  $("keysInfo").textContent = !n ? "" : st.keys_total
    ? `Ключей в работе: ${st.keys} из ${st.keys_total}` + (st.keys < st.keys_total ? " — какой-то EXBO не пустила, смотри «Журнал»" : " — до " + (st.keys * 380) + " запросов в минуту")
    : `Ещё ключей: ${n} — заработают после «Начать поиск»`;
}
function keyLoad() {
  const st = (S && S.status) || {}, o = st.key_others, lim = st.key_limit || 400;
  return o != null && o >= lim * 0.1 ? {others: Math.round(o), limit: lim} : null;
}
// ---------- состояние: одно понятное предложение вместо приборной панели ----------
function renderStatus() {
  const st = S.status, run = st.running, sv = st.server;
  const subscriber = S.server && S.server.role === "subscriber";
  $("dot").classList.toggle("live", run);
  let txt = "Поиск остановлен";
  if (run) txt = st.starting ? "Запускаю…" : subscriber ? (sv && !sv.ok ? "Нет связи с сервером" : "Беру находки с сервера")
    : st.progress ? `Ищу · ${st.progress.done} из ${st.progress.total}` : "Ищу";
  $("stateTxt").textContent = txt;
  const btn = $("runBtn"); btn.textContent = run ? "Остановить" : "Начать поиск"; btn.classList.toggle("stop", run);
  $("modeLbl").innerHTML = "Регион RU · " + (S.demo ? "<b>ДЕМО-режим</b>" : "боевой API") + (S.version ? "<br>Версия " + esc(S.version) : "");
  $("onboard").hidden = S.configured;
  $("demoNote").hidden = !S.demo;
  $("demoNoteSub").innerHTML = S.has_keys
    ? "<b>Ключи у тебя уже есть — выключи демо-режим.</b> Находки здесь ненастоящие."
    : "Находки здесь ненастоящие — режим нужен, только чтобы проверить, что приложение работает.";
  const active = S.deals.filter((d) => !d.gone && (!d.ends || Date.parse(d.ends) / 1000 > S.now));
  const total = active.reduce((s, d) => s + d.profit, 0);
  const items = st.total || (st.progress && st.progress.total) || watchTotal();
  let h, sub;
  const near = (S.near || []).filter((r) => !r.gone);
  if (active.length) h = `${active.length} ${plural(active.length, ["находка", "находки", "находок"])} — вместе до <span class="good">+${rub(total)}</span>`;
  else h = run ? (near.length ? "По твоим порогам пока ничего — ищу дальше" : "Пока ничего выгодного — ищу дальше") : "Поиск остановлен";
  if (subscriber) sub = !sv ? "Находки придут с сервера владельца после «Начать поиск»." : sv.ok ? `Сервер владельца на связи${sv.server_pass ? ", его последняя проверка " + ago(new Date(sv.server_pass * 1000).toISOString(), S.now) : ""}.` : (sv.error || "Сервер владельца не отвечает.");
  else if (run) {
    sub = `Проверяю ${items} ${plural(items, ["предмет", "предмета", "предметов"])} по кругу${st.took ? `, круг занимает ~${Math.max(1, Math.round(st.took))} с` : ""}.`;
    if (st.delay !== null && st.delay !== undefined) sub += ` Новые лоты аукцион отдаёт через API примерно через ${Math.max(1, Math.round(st.delay))} мин после выставления — так у всех, кто смотрит через API.`;
    const kl = keyLoad();
    if (kl) sub += ` Твоим ключом API пользуется ещё кто-то (~${kl.others} запр./мин) — поиск медленнее, подробнее во вкладке «Доступ».`;
    if (!active.length && near.length) sub = `Дешевле рынка есть ${near.length} ${plural(near.length, ["лот", "лота", "лотов"])} с меньшей выгодой, чем в твоих порогах, — смотри «Почти находки» ниже. ` + sub;
  }
  else sub = active.length ? "Это находки с прошлого поиска. Нажми «Начать поиск», чтобы искать дальше." : "Нажми «Начать поиск» — трекер будет проверять аукцион без остановки и покажет здесь лоты дешевле рынка.";
  $("sumH").innerHTML = h; $("sumS").textContent = sub;
  $("kBar").style.width = run && st.progress && st.progress.total ? (st.progress.done / st.progress.total * 100) + "%" : "0";
  $("cntDeals").textContent = active.length || "";
  const up = S.update || {}, busy = up.status === "downloading";
  $("updNote").hidden = !(up.status === "available" || busy);
  $("updTitle").textContent = busy ? up.message : `Доступна версия ${up.version || ""}`;
  $("updSub").textContent = busy ? "Не закрывай программу — она перезапустится сама."
    : ((up.notes || "").split("\n").find((l) => l.trim()) || "Скачается и установится само, программа перезапустится.");
  $("updBtn").hidden = up.status !== "available";
  $("updInfo").textContent = up.message || (up.repo ? "" : "Обновления не настроены — укажи репозиторий и сохрани.");
  $("restartOverlay").hidden = up.status !== "restarting";
  const db = st.db;
  if (db && db.sales) {
    const n = (x) => String(x).replace(".", ",");
    $("dbInfo").textContent = `База сделок: ${db.sales.toLocaleString("ru-RU")} сделок по ${db.items} предм. за ${n(db.days)} дн. · ${n(db.mb)} МБ`;
  }
  if (st.error && st.error_id !== lastErr) { lastErr = st.error_id; toast(st.error, true); }
  const logCls = (m) => /ОШИБКА|ошибка/.test(m) ? "e" : /^⚠/.test(m) ? "w" : /^Найдено/.test(m) ? "f" : "";
  if (view === "log" || firstLoad) $("log").innerHTML = S.log.map((l) => `<div><span class="t">${l.t}</span>  <span class="${logCls(l.m)}">${esc(l.m)}</span></div>`).join("");
}
async function refresh() {
  try { S = await api("/api/state"); } catch (e) { $("stateTxt").textContent = "Нет связи с программой"; return; }
  const fresh = S.deals.filter((d) => !knownIds.has(d.id));
  fresh.forEach((d) => knownIds.add(d.id));
  const loud = fresh.filter((d) => d.notify !== false);  // о старых находках из прошлых запусков — тихо
  if (!firstLoad && loud.length) { beep(loud.some((d) => d.rare)); loud.slice(0, 3).forEach(notifyDesktop); }
  if (firstLoad || !formDirty) fillForm();
  if (!CAT) loadCatalog();
  renderStatus(); renderDeals(); renderNear(); renderChips(); renderPurchases(); renderAccuracy(); renderAccess(); renderKeys();
  if (view === "items" && Date.now() - (loadYield.at || 0) > 300000) loadYield();
  if (view === "craft" && Date.now() - (loadCraft.at || 0) > (S.status.craft_left ? 20000 : 120000)) loadCraft();
  firstLoad = false;
}
document.querySelector('.nav button[data-view="log"]').addEventListener("click", () => { if (S) renderStatus(); });
refresh(); setInterval(refresh, 2000);
</script>
</body>
</html>
"""


# ==== НОВЫЙ ВИД: начало ====
# Новый вид (2.6): как программы Windows 11 — системный шрифт, цвет акцента Windows, навигация как в «Параметрах».
# Сервер подставляет __TOKEN__, __THEME__ и /*__ACCENT__*/.
UI_NEW_HTML = r"""<!doctype html>
<html lang="ru" data-theme="__THEME__" data-scale="__SCALE__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>STALZONE Трекер</title>
<script>(function(){var r=document.documentElement,m=matchMedia("(prefers-color-scheme: dark)"),t=r.dataset.theme;function a(){r.classList.toggle("dark",t==="dark"||(t!=="light"&&m.matches))}window.__setTheme=function(x){t=x;r.dataset.theme=x;a()};a();try{m.addEventListener("change",a)}catch(e){}var Z={s:0.9,m:1,l:1.15};function f(){var z=Z[r.dataset.scale]||1,w=innerWidth/z,was=r.classList.contains("w1180");r.style.zoom=z;r.style.setProperty("--z",z);[1360,1180,1100].forEach(function(b){r.classList.toggle("w"+b,w<=b)});if(was!==r.classList.contains("w1180"))dispatchEvent(new Event("narrowchange"))}window.__setScale=function(x){r.dataset.scale=x;f()};f();addEventListener("resize",f)})()</script>
<style>
/* Новый вид: как программы Windows 11 — системный шрифт, цвет акцента Windows, «Параметры»-навигация.
   Тёмная тема — класс .dark на <html> (его ставит скрипт в <head> до отрисовки, поэтому ничего не мигает). */
:root{
  --font:"Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;
  --font-d:"Segoe UI Variable Display","Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;
  --mono:"Cascadia Mono",Consolas,"Courier New",monospace;
  --acc-l:#005fb8; --acc-l-t:#003e92; --acc-l-on:#ffffff;
  --acc-d:#60cdff; --acc-d-t:#99ebff; --acc-d-on:#000000;
  --mica:#f3f3f3; --layer:#f9f9f9; --card:#ffffff; --ctrl:#fdfdfd; --ctrl-h:#f6f6f6; --ctrl-p:#f1f1f1;
  --hover:rgba(0,0,0,.037); --press:rgba(0,0,0,.024); --sel:rgba(0,0,0,.056);
  --stroke:#e5e5e5; --divider:#ebebeb; --ctrl-b:#e1e1e1; --ctrl-bb:#c4c4c4; --input-bb:#868686;
  --text:#1a1a1a; --text-2:#5d5d5d; --text-3:#8b8b8b; --text-dis:#a8a8a8;
  --accent:var(--acc-l); --accent-t:var(--acc-l-t); --on-accent:var(--acc-l-on);
  --good:#0f7b0f; --good-bg:#dff6dd; --warn:#9d5d00; --warn-bg:#fff4ce; --bad:#c42b1c; --bad-bg:#fde7e9;
  --q0:#6e6e6e; --q1:#2f7d32; --q2:#1f6bc1; --q3:#7b3fbf; --q4:#c0392b; --q5:#b4710a;
  --shadow:0 8px 16px rgba(0,0,0,.14); --shadow-2:0 32px 64px rgba(0,0,0,.19),0 2px 21px rgba(0,0,0,.15);
  --smoke:rgba(0,0,0,.3); --scroll:#8b8b8b;
  color-scheme:light;
}
:root.dark{
  --mica:#202020; --layer:#272727; --card:#2b2b2b; --ctrl:#2d2d2d; --ctrl-h:#323232; --ctrl-p:#282828;
  --hover:rgba(255,255,255,.055); --press:rgba(255,255,255,.035); --sel:rgba(255,255,255,.083);
  --stroke:#363636; --divider:#323232; --ctrl-b:#3b3b3b; --ctrl-bb:#2f2f2f; --input-bb:#9a9a9a;
  --text:#ffffff; --text-2:#c8c8c8; --text-3:#9d9d9d; --text-dis:#6f6f6f;
  --accent:var(--acc-d); --accent-t:var(--acc-d-t); --on-accent:var(--acc-d-on);
  --good:#6ccb5f; --good-bg:#2c3a22; --warn:#fce100; --warn-bg:#433519; --bad:#ff99a4; --bad-bg:#442726;
  --q0:#b0b0b0; --q1:#6ccb5f; --q2:#6aa8ff; --q3:#c39bff; --q4:#ff8a80; --q5:#f2c05c;
  --shadow:0 8px 16px rgba(0,0,0,.36); --shadow-2:0 32px 64px rgba(0,0,0,.37),0 2px 21px rgba(0,0,0,.37);
  --smoke:rgba(0,0,0,.5); --scroll:#9d9d9d;
  color-scheme:dark;
}
:root{--accent-h:color-mix(in srgb,var(--accent) 90%,var(--card));--accent-p:color-mix(in srgb,var(--accent) 80%,var(--card));
  --accent-bg:color-mix(in srgb,var(--accent) 12%,var(--card))}
/*__ACCENT__*/

*{box-sizing:border-box}
[hidden]{display:none!important}
html,body{margin:0;height:100%}
body{background:var(--mica);color:var(--text);font:14px/20px var(--font);-webkit-font-smoothing:antialiased;overflow:hidden;
  user-select:none;cursor:default}
button,input,select,textarea{font:inherit;color:inherit;margin:0}
input,textarea,.selectable{user-select:text}
a{color:var(--accent-t);cursor:pointer;text-decoration:none}
a:hover{text-decoration:underline}
:focus{outline:none}
:focus-visible{outline:2px solid var(--text);outline-offset:1px}
.num{font-variant-numeric:tabular-nums}
svg{flex:none}
h1,h2,h3,p{margin:0}
::-webkit-scrollbar{width:12px;height:12px}
::-webkit-scrollbar-thumb{background:var(--scroll);background-clip:padding-box;border:4px solid transparent;border-radius:8px;min-height:40px}
::-webkit-scrollbar-thumb:hover{border-width:3px}
::-webkit-scrollbar-track,::-webkit-scrollbar-corner{background:transparent}

/* ---------- каркас ---------- */
.app{display:grid;grid-template-columns:240px minmax(0,1fr);height:calc(100vh / var(--z, 1))}   /* --z — размер интерфейса */
.pane{display:flex;flex-direction:column;padding:6px 4px 8px;min-height:0}
.who{display:flex;align-items:center;gap:12px;padding:12px 12px 16px}
.who img{width:32px;height:32px;flex:none}
.who b{display:block;font-weight:600;line-height:18px;white-space:nowrap}
.who small{display:block;color:var(--text-2);font-size:12px;line-height:16px;white-space:nowrap}
.nav{display:flex;flex-direction:column;gap:3px}
.nav button{all:unset;box-sizing:border-box;position:relative;display:flex;align-items:center;gap:14px;height:36px;padding:0 12px 0 14px;
  border-radius:4px;color:var(--text);white-space:nowrap}
.nav button:hover{background:var(--hover)}
.nav button:active{background:var(--press);color:var(--text-2)}
.nav button.on{background:var(--sel)}
.nav button.on:before{content:"";position:absolute;left:0;top:10px;height:16px;width:3px;border-radius:2px;background:var(--accent)}
.nav button:focus-visible{outline:2px solid var(--text);outline-offset:-2px}
.nav svg{width:16px;height:16px}
.nav .cnt{margin-left:auto;font-size:12px;color:var(--text-3)}
.nav .cnt:empty{display:none}
.nav .cnt.hot{min-width:18px;height:18px;padding:0 5px;border-radius:9px;background:var(--accent);color:var(--on-accent);
  font-size:11px;font-weight:600;line-height:18px;text-align:center}
.pane .foot{margin-top:auto}
.pane .ver{padding:8px 14px 0;color:var(--text-3);font-size:12px;line-height:16px}
.main{background:var(--layer);border-top:1px solid var(--stroke);border-left:1px solid var(--stroke);border-top-left-radius:8px;
  display:flex;min-width:0;min-height:0;overflow:hidden}
.page{flex:1;min-width:0;display:flex;flex-direction:column}
.head{display:flex;align-items:center;gap:16px;padding:20px 28px 12px;flex:none}
.head h1{font:600 28px/36px var(--font-d);white-space:nowrap}
.status{margin-left:auto;display:flex;align-items:center;gap:10px;color:var(--text-2);white-space:nowrap;min-width:0}
.status span:last-child{overflow:hidden;text-overflow:ellipsis}
.views{flex:1;min-height:0;overflow:auto;padding:0 28px 28px}
.view{display:none}
.view.on{display:block}

/* ---------- кнопки и поля ---------- */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;height:32px;padding:0 12px;border-radius:4px;
  border:1px solid var(--ctrl-b);border-bottom-color:var(--ctrl-bb);background:var(--ctrl);color:var(--text);white-space:nowrap;cursor:default}
.btn:hover{background:var(--ctrl-h)}
.btn:active{background:var(--ctrl-p);color:var(--text-2);border-bottom-color:var(--ctrl-b)}
.btn[disabled]{color:var(--text-dis);background:var(--ctrl);border-color:var(--ctrl-b)}
.btn.accent{background:var(--accent);border-color:transparent;color:var(--on-accent)}
.btn.accent:hover{background:var(--accent-h)}
.btn.accent:active{background:var(--accent-p)}
.btn.subtle{background:transparent;border-color:transparent}
.btn.subtle:hover{background:var(--hover)}
.btn.subtle:active{background:var(--press)}
.btn.sm{height:28px;padding:0 10px}
.btn.wide{width:100%}
.btn svg{width:16px;height:16px}
.tbtn{display:inline-flex;align-items:center;gap:8px;height:32px;padding:0 12px;border-radius:4px;border:1px solid var(--ctrl-b);
  border-bottom-color:var(--ctrl-bb);background:var(--ctrl);white-space:nowrap;cursor:default}
.tbtn:hover{background:var(--ctrl-h)}
.tbtn.on{background:var(--accent);border-color:transparent;color:var(--on-accent)}
.tbtn.on:hover{background:var(--accent-h)}
.ib{width:32px;height:32px;border-radius:4px;display:inline-grid;place-items:center;color:var(--text-2);border:0;background:transparent;cursor:default;flex:none}
.ib:hover{background:var(--hover);color:var(--text)}
.ib:active{background:var(--press)}
.ib svg{width:16px;height:16px}
.field{height:32px;min-width:0;padding:0 11px;border:1px solid var(--ctrl-b);border-bottom-color:var(--input-bb);border-radius:4px;
  background:var(--ctrl);color:var(--text);outline:none}
.field:hover{background:var(--ctrl-h)}
.field:focus{background:var(--card);border-bottom-color:var(--accent);box-shadow:inset 0 -1px 0 var(--accent)}
.field::placeholder{color:var(--text-3)}
textarea.field{height:auto;min-height:72px;padding:6px 11px;resize:vertical;line-height:20px}
textarea.field.code{font:12px/18px var(--mono);word-break:break-all}
.field.num{text-align:right}
.combo{position:relative;display:inline-flex;min-width:0}
.combo select{appearance:none;-webkit-appearance:none;height:32px;width:100%;padding:0 34px 0 11px;border:1px solid var(--ctrl-b);
  border-bottom-color:var(--ctrl-bb);border-radius:4px;background:var(--ctrl);color:var(--text);outline:none;cursor:default;text-overflow:ellipsis}
.combo select:hover{background:var(--ctrl-h)}
.combo select option{background:var(--card);color:var(--text)}
.combo svg{position:absolute;right:11px;top:10px;width:12px;height:12px;color:var(--text-2);pointer-events:none}
.search{position:relative;display:inline-flex;min-width:0}
.search .field{width:100%;padding-right:34px}
.search svg{position:absolute;right:11px;top:9px;width:14px;height:14px;color:var(--text-2);pointer-events:none}
.unit{position:relative;display:inline-flex}
.unit .field{width:100%;padding-right:30px}
.unit i{position:absolute;right:11px;top:6px;font-style:normal;color:var(--text-3);pointer-events:none}
.unit.wide .field{padding-right:44px}
.toggle{display:inline-flex;align-items:center;gap:12px;cursor:default;white-space:nowrap}
.toggle input{position:absolute;opacity:0;width:0;height:0}
.toggle .tr-st{color:var(--text);min-width:40px;text-align:right}
.toggle i{position:relative;width:40px;height:20px;border-radius:10px;border:1px solid var(--input-bb);background:var(--ctrl);flex:none}
.toggle i:after{content:"";position:absolute;width:12px;height:12px;border-radius:50%;background:var(--text-2);top:3px;left:3px;transition:left .12s,transform .12s}
.toggle:hover i:after{transform:scale(1.15)}
.toggle input:checked + i{background:var(--accent);border-color:var(--accent)}
.toggle input:checked + i:after{background:var(--on-accent);left:23px}
.toggle input:focus-visible + i{outline:2px solid var(--text);outline-offset:2px}
@media (prefers-reduced-motion:reduce){.toggle i:after{transition:none}}
.range{width:160px;accent-color:var(--accent)}
.grow{flex:1}
.muted{color:var(--text-2)}
.faint{color:var(--text-3)}
.small{font-size:12px;line-height:16px}
.good{color:var(--good)}
.bad{color:var(--bad)}
.warn{color:var(--warn)}

/* ---------- кольцо и полоса ожидания ---------- */
.ring{width:16px;height:16px;flex:none}
.ring circle{fill:none;stroke:var(--accent);stroke-width:2;stroke-linecap:round;stroke-dasharray:28 60;transform-origin:50% 50%;animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){.ring circle{animation:none}}
.dotst{width:8px;height:8px;border-radius:50%;background:var(--text-3);flex:none}

/* ---------- плашки, карточки ---------- */
.infobar{display:flex;align-items:center;gap:12px;border-radius:4px;padding:8px 8px 8px 14px;border:1px solid transparent;margin-bottom:12px;min-height:48px}
.infobar .ic{width:16px;height:16px;flex:none}
.infobar .tx{flex:1;min-width:0}
.infobar .tx b{font-weight:600;margin-right:6px}
.infobar.info{background:var(--accent-bg);border-color:color-mix(in srgb,var(--accent) 20%,transparent)}
.infobar.info .ic{color:var(--accent)}
.infobar.ok{background:var(--good-bg);border-color:color-mix(in srgb,var(--good) 20%,transparent)}
.infobar.ok .ic{color:var(--good)}
.infobar.warn{background:var(--warn-bg);border-color:color-mix(in srgb,var(--warn) 22%,transparent)}
.infobar.warn .ic{color:var(--warn)}
.infobar.err{background:var(--bad-bg);border-color:color-mix(in srgb,var(--bad) 20%,transparent)}
.infobar.err .ic{color:var(--bad)}
.card{background:var(--card);border:1px solid var(--stroke);border-radius:8px;padding:16px 18px}
.card h2{font-size:14px;line-height:20px;font-weight:600}
.card .sub{color:var(--text-2);font-size:12px;line-height:16px;margin-top:2px}
.cols{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:12px;align-items:start}
.stack{display:flex;flex-direction:column;gap:12px;min-width:0}
.tag{display:inline-block;font-size:12px;line-height:18px;padding:0 6px;border-radius:4px;background:var(--sel);color:var(--text-2);white-space:nowrap;font-weight:400}
.tag.new{background:var(--accent-bg);color:var(--accent-t)}
.tag.me{background:var(--warn-bg);color:var(--warn)}
.tag.bid{background:color-mix(in srgb,var(--q2) 14%,transparent);color:var(--q2)}
.tag.rare{background:color-mix(in srgb,var(--q3) 15%,transparent);color:var(--q3)}
.tag.mine{background:var(--good-bg);color:var(--good)}
.tag.bad{background:var(--bad-bg);color:var(--bad)}
.tag.stale{background:var(--warn-bg);color:var(--warn)}
.slot{width:40px;height:40px;border-radius:4px;flex:none;display:grid;place-items:center;position:relative;
  background:color-mix(in srgb,var(--rc) 13%,transparent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--rc) 38%,transparent)}
.slot:before{content:attr(data-l);font-weight:600;color:var(--rc)}
.slot.ok:before{content:none}
.slot img{position:absolute;left:3px;top:3px;width:calc(100% - 6px);height:calc(100% - 6px);object-fit:contain}
.slot.sm{width:28px;height:28px}
.slot.sm img{left:2px;top:2px;width:24px;height:24px}
.slot.lg{width:64px;height:64px;border-radius:6px}
.slot.lg:before{font-size:22px}
.g{font-size:12px;font-weight:600;color:var(--rc)}

/* ---------- строка итогов на «Находках» ---------- */
.lead{display:flex;flex-wrap:wrap;align-items:center;gap:6px 0;margin-bottom:14px}
.lead .st{display:flex;align-items:baseline;gap:8px;padding:0 20px;border-left:1px solid var(--divider);white-space:nowrap}
.lead .st:first-child{padding-left:0;border-left:0}
.lead .st b{font:600 18px/24px var(--font-d)}
.lead .st span{color:var(--text-2)}
.lead .why{flex-basis:100%;color:var(--text-2);font-size:12px;line-height:16px;margin-top:2px}

/* ---------- панель команд ---------- */
.cmdbar{display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.cmdbar .search{width:240px}
.cmdbar.one{flex-wrap:nowrap}
.cmdbar.one .search{flex:0 1 240px;width:auto;min-width:150px}

/* ---------- таблица находок ---------- */
.table{background:var(--card);border:1px solid var(--stroke);border-radius:8px;overflow:hidden}
.thead,.tr{display:grid;grid-template-columns:minmax(0,1fr) 108px 108px 92px 132px 40px;gap:12px;align-items:center;padding:0 8px 0 12px}
.thead{height:34px;font-size:12px;color:var(--text-2);border-bottom:1px solid var(--divider)}
.thead button{all:unset;display:flex;align-items:center;gap:4px;height:34px;cursor:default;white-space:nowrap}
.thead button:hover{color:var(--text)}
.thead .r{justify-content:flex-end}
.thead .on{color:var(--text);font-weight:600}
.thead svg{width:10px;height:10px}
.tr{position:relative;min-height:60px;border-bottom:1px solid var(--divider);outline-offset:-2px}
.tr:last-child{border-bottom:0}
.tr:hover{background:var(--hover)}
.tr.sel{background:var(--sel)}
.tr.sel:before{content:"";position:absolute;left:0;top:50%;margin-top:-10px;height:20px;width:3px;border-radius:2px;background:var(--accent)}
.tr.old{color:var(--text-3)}
.tr.old .slot img{opacity:.45}
.tr.old .p{color:var(--text-3)}
.tr.mine .p:after{content:" ✓";color:var(--good)}
.it{display:flex;align-items:center;gap:12px;min-width:0}
.it .t{min-width:0}
.n{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.m{display:flex;align-items:center;gap:6px;font-size:12px;line-height:16px;color:var(--text-2);margin-top:3px;white-space:nowrap;overflow:hidden}
.r{text-align:right}
.v{white-space:nowrap}
.s{font-size:12px;line-height:16px;color:var(--text-2);white-space:nowrap}
.ch .v{display:flex;justify-content:space-between;align-items:baseline;gap:6px}
.ch .v small{font-size:12px;color:var(--text-3)}
.bar{display:block;height:4px;border-radius:2px;background:var(--divider);margin-top:6px;overflow:hidden}
.bar b{display:block;height:100%;border-radius:2px;background:var(--good)}
.mid .bar b{background:var(--warn)}
.lo .bar b{background:var(--bad)}
.p{font-weight:600;font-size:15px;color:var(--good);white-space:nowrap}
.p.neg{color:var(--bad)}
.empty{display:flex;flex-direction:column;align-items:center;text-align:center;gap:6px;padding:44px 24px;color:var(--text-2)}
.empty h3{font-size:16px;line-height:22px;font-weight:600;color:var(--text)}
.empty p{max-width:56ch}
.empty .ring{width:28px;height:28px;margin-bottom:6px}
.table + .expander,.expander + .expander{margin-top:12px}

/* ---------- раскрывающаяся карточка ---------- */
.expander{background:var(--card);border:1px solid var(--stroke);border-radius:8px}
.expander > summary{list-style:none;display:flex;align-items:center;gap:14px;padding:12px 16px;min-height:56px;cursor:default}
.expander > summary::-webkit-details-marker{display:none}
.expander > summary:hover{background:var(--hover);border-radius:8px}
.expander > summary .chev{width:12px;height:12px;color:var(--text-2);transition:transform .15s}
.expander[open] > summary .chev{transform:rotate(90deg)}
.expander > summary b{display:block;font-weight:600;line-height:18px}
.expander > summary span{font-size:12px;line-height:16px;color:var(--text-2)}
.expander .body{border-top:1px solid var(--divider)}
.nr{display:grid;grid-template-columns:minmax(0,1fr) 108px 108px 132px 40px;gap:12px;align-items:center;padding:8px 8px 8px 16px;border-bottom:1px solid var(--divider)}
.nr:last-child{border-bottom:0}
.nr .why{font-size:12px;line-height:16px;color:var(--warn);white-space:normal}
.nr.old{color:var(--text-3)}
.nr.old .n{text-decoration:line-through}

/* ---------- панель справа: находка или рецепт ---------- */
.detail{width:340px;flex:none;background:var(--card);border-left:1px solid var(--stroke);overflow:auto;padding:20px 20px 28px;position:relative}
.detail .x{display:none;position:absolute;right:10px;top:10px}
.dh{display:flex;gap:14px;align-items:center;padding-right:28px}
.dh h2{font:600 20px/26px var(--font-d)}
.dh .tags{margin-top:6px;display:flex;flex-wrap:wrap;gap:6px}
.hero{margin-top:18px;font:600 28px/36px var(--font-d);color:var(--good)}
.hero.neg{color:var(--bad)}
.hero-s{color:var(--text-2);font-size:12px;line-height:16px}
.kv{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 12px;margin-top:14px;padding:12px 0;border-top:1px solid var(--divider);border-bottom:1px solid var(--divider)}
.kv > span{color:var(--text-2)}
.kv > b{font-weight:400;text-align:right;white-space:nowrap}
.kv > b.good{color:var(--good);font-weight:600}
.kv > b.bad{color:var(--bad);font-weight:600}
.kv small{display:block;font-size:12px;line-height:16px;color:var(--text-3)}
.buy{display:flex;gap:8px;margin-top:14px}
.buy .unit{flex:1;min-width:0}
.sec{margin-top:20px}
.sec h3{font-size:14px;line-height:20px;font-weight:600;margin-bottom:6px}
.big{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.big b{font:600 20px/28px var(--font-d)}
.big span{color:var(--text-2)}
.reasons{list-style:none;margin:10px 0 0;padding:0;display:flex;flex-direction:column;gap:6px;color:var(--text-2)}
.reasons li{display:flex;gap:8px}
.reasons li:before{content:"";flex:none;width:6px;height:6px;border-radius:50%;margin-top:7px;background:var(--text-3)}
.reasons li.up:before{background:var(--good)}
.reasons li.down:before{background:var(--warn)}
.facts{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:16px}
.fact{background:var(--layer);border:1px solid var(--divider);border-radius:6px;padding:8px 10px}
.fact .l{font-size:12px;line-height:16px;color:var(--text-2)}
.fact .v{margin-top:2px;font-weight:600;white-space:normal}
.note{margin-top:12px;font-size:12px;line-height:16px;color:var(--text-2);background:var(--layer);border:1px solid var(--divider);border-radius:6px;padding:8px 10px}
.note.warn{background:var(--warn-bg);border-color:transparent;color:var(--text)}
.note.ok{background:var(--good-bg);border-color:transparent;color:var(--text)}
.chart svg{display:block;width:100%;height:auto;overflow:visible}
.chart .cap{font-size:12px;line-height:16px;color:var(--text-3);margin-top:4px}
.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.ing{display:grid;grid-template-columns:28px minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid var(--divider)}
.ing:last-child{border-bottom:0}
.ing .n{font-weight:400}
.ing .s{white-space:normal}
.ing .pr{text-align:right;white-space:nowrap}
.ing .pr b{font-weight:600}
.pill{display:inline-block;font-size:12px;line-height:18px;padding:0 6px;border-radius:4px;white-space:nowrap}
.pill.good{background:var(--good-bg);color:var(--good)}
.pill.warn{background:var(--warn-bg);color:var(--warn)}
.pill.bad{background:var(--bad-bg);color:var(--bad)}
.opts{display:flex;gap:8px;flex-wrap:wrap}
.opt{all:unset;box-sizing:border-box;display:flex;gap:10px;align-items:flex-start;border:1px solid var(--ctrl-b);border-radius:6px;padding:9px 14px 9px 10px;
  background:var(--ctrl);min-width:150px;cursor:default}
.opt:hover{background:var(--ctrl-h)}
.opt.on{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.opt:focus-visible{outline:2px solid var(--text);outline-offset:1px}
.opt .radio{width:16px;height:16px;border-radius:50%;border:1px solid var(--input-bb);margin-top:2px;flex:none;background:var(--ctrl)}
.opt.on .radio{border:5px solid var(--accent);background:var(--on-accent)}
.opt b{display:block;font-weight:600}
.opt small{display:block;font-size:12px;line-height:16px;color:var(--text-2)}
.opt .k{font-size:12px;color:var(--text-2);line-height:16px}
.detail .opts{flex-direction:column}
.detail .opt{min-width:0;width:100%}

/* ---------- предметы ---------- */
.tabs{display:flex;gap:4px;flex-wrap:wrap;margin:12px 0 8px}
.tabs button{all:unset;position:relative;padding:5px 10px;border-radius:4px;color:var(--text-2);font-size:13px;white-space:nowrap;cursor:default}
.tabs button:hover{background:var(--hover);color:var(--text)}
.tabs button.on{color:var(--text);font-weight:600}
.tabs button.on:after{content:"";position:absolute;left:50%;bottom:0;width:16px;margin-left:-8px;height:3px;border-radius:2px;background:var(--accent)}
.tabs button span{color:var(--text-3);margin-left:5px;font-weight:400}
.tabs button:focus-visible{outline:2px solid var(--text);outline-offset:-2px}
.results{max-height:560px;overflow:auto;border:1px solid var(--divider);border-radius:6px;background:var(--card)}
.res{display:flex;align-items:center;gap:10px;padding:6px 8px 6px 10px;border-bottom:1px solid var(--divider);min-height:44px}
.res:last-child{border-bottom:0}
.res:hover{background:var(--hover)}
.res .n{flex:1;min-width:0;font-weight:400}
.star{all:unset;width:28px;height:28px;border-radius:4px;display:grid;place-items:center;color:var(--text-3);font-size:16px;cursor:default;flex:none}
.star:hover{background:var(--hover);color:var(--q3)}
.star.on{color:var(--q3)}
.list-rows{display:flex;flex-direction:column}
.lrow{display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--divider);min-height:40px}
.lrow:last-child{border-bottom:0}
.lrow .n{flex:1;min-width:0;font-weight:400}
.srow{display:flex;align-items:center;gap:16px;padding:10px 0;border-bottom:1px solid var(--divider)}
.srow:last-child{border-bottom:0}
.srow .tx{flex:1;min-width:0}
.srow .tx small{display:block;color:var(--text-2);font-size:12px;line-height:16px}
.yrow{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid var(--divider)}
.yrow:last-child{border-bottom:0}

/* ---------- мои покупки ---------- */
.profit{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:12px;margin-bottom:12px}
.pmain{display:flex;flex-direction:column;gap:6px}
.pmain .top{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.pmain .top h2{margin-right:auto}
.earned{font:600 34px/42px var(--font-d)}
.earned.good{color:var(--good)}
.earned.bad{color:var(--bad)}
.pline{color:var(--text-2)}
.pside{display:flex;flex-direction:column;gap:8px}
.kpi{background:var(--card);border:1px solid var(--stroke);border-radius:8px;padding:10px 14px}
.kpi span{font-size:12px;line-height:16px;color:var(--text-2)}
.kpi b{display:block;font:600 18px/24px var(--font-d)}
.kpi small{display:block;font-size:12px;line-height:16px;color:var(--text-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.selector{display:flex;gap:2px}
.selector button{all:unset;position:relative;padding:5px 10px;border-radius:4px;color:var(--text-2);white-space:nowrap;cursor:default}
.selector button:hover{background:var(--hover);color:var(--text)}
.selector button.on{color:var(--text);font-weight:600}
.selector button.on:after{content:"";position:absolute;left:50%;bottom:0;width:16px;margin-left:-8px;height:3px;border-radius:2px;background:var(--accent)}
.selector button em{font-style:normal;color:var(--text-3);margin-left:6px;font-weight:400}
.selector button:focus-visible{outline:2px solid var(--text);outline-offset:-2px}
.days{min-height:20px}
.days svg{display:block;margin-top:6px;overflow:visible}
.pbar{cursor:pointer;outline:none}
.pbar:hover rect:not(.hit){filter:brightness(1.12)}
.pbar.on rect.hit,.pbar:focus-visible rect.hit{fill:var(--hover)}
.kbtn{all:unset;box-sizing:border-box;display:block;cursor:pointer;background:var(--card);border:1px solid var(--stroke);border-radius:8px;padding:10px 14px}
.kbtn:hover{background:var(--ctrl-h)}
.kbtn:focus-visible{outline:2px solid var(--text);outline-offset:1px}
.daychip{display:inline-flex;align-items:center;gap:4px;padding:0 2px 0 10px;height:30px;border-radius:15px;background:var(--accent-bg);color:var(--accent-t);white-space:nowrap}
.daychip .ib{width:26px;height:26px;color:var(--accent-t)}
.pcard.hl{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.pcard{background:var(--card);border:1px solid var(--stroke);border-radius:8px;margin-bottom:8px}
.prow{display:grid;grid-template-columns:minmax(0,1fr) 116px 136px 128px auto;gap:16px;align-items:center;padding:12px 12px 12px 16px}
.lbl{font-size:12px;color:var(--text-2);line-height:16px;white-space:nowrap}
.pst{font-size:12px;line-height:18px;padding:0 6px;border-radius:4px;white-space:nowrap}
.pst.listed{background:var(--accent-bg);color:var(--accent-t)}
.pst.holding{background:var(--sel);color:var(--text-2)}
.pst.sold{background:var(--good-bg);color:var(--good)}
.acts{display:flex;gap:6px;align-items:center;justify-content:flex-end}
.pfoot{border-top:1px solid var(--divider);padding:12px 16px 14px 68px;display:flex;flex-direction:column;gap:10px}
.pfoot .infobar{margin:0}
.listrow{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.listrow .unit{width:170px}
.acc p{margin:8px 0 0;color:var(--text-2)}
.acc p b{color:var(--text)}
.accrows{margin-top:10px;border-top:1px solid var(--divider)}
.accrows div{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:14px;padding:6px 0;border-bottom:1px solid var(--divider);font-size:13px}

/* ---------- крафт ---------- */
.skills{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px 20px;margin-top:12px}
.skill{display:flex;align-items:center;justify-content:space-between;gap:10px;min-width:0}
.skill > span:first-child{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.skill .combo{width:92px;flex:none}
.advice{display:flex;flex-direction:column;gap:10px;margin-top:12px}
.adv b{font-weight:600}
.adv span{display:block;color:var(--text-2);font-size:12px;line-height:16px}
.ctable .thead,.ctable .tr{grid-template-columns:minmax(0,1.3fr) minmax(0,1.2fr) 100px 100px 112px 110px}
.ctable .tr{min-height:56px;padding-top:6px;padding-bottom:6px;align-items:start;cursor:default}
.ctable .tr > div{padding-top:4px}
.ctable .tr.loss{color:var(--text-3)}
.ctable .ingl{font-size:12px;line-height:16px;color:var(--text-2);white-space:normal}
.ctable .ingl .np{color:var(--text-3)}
.ctable .tags{display:flex;flex-wrap:wrap;gap:4px;margin-top:3px}

/* ---------- настройки, как в «Параметрах» Windows ---------- */
.settings{max-width:1000px}
.group{margin-bottom:24px}
.group > h2{font-size:14px;line-height:20px;font-weight:600;margin-bottom:8px}
.scard{display:flex;align-items:center;gap:16px;min-height:64px;padding:10px 16px;background:var(--card);border:1px solid var(--stroke);border-radius:4px;margin-bottom:3px}
.scard > svg{width:20px;height:20px;color:var(--text);flex:none}
.scard .tx{flex:1;min-width:0}
.scard .tx > div{line-height:20px}
.scard .tx small{display:block;font-size:12px;line-height:16px;color:var(--text-2)}
.scard .ctl{display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end;min-width:0}
.scard .ctl .field{width:260px}
.scard .ctl .unit{width:140px}
.scard .ctl .combo{width:240px}
.scard.col{flex-direction:column;align-items:stretch;gap:8px}
.scard.col .row1{display:flex;align-items:center;gap:16px}
.scard.flash{animation:flash 1.8s ease}
@keyframes flash{0%,55%{background:var(--accent-bg)}100%{background:var(--card)}}
details.sexp{margin-bottom:3px}
details.sexp > summary{list-style:none;display:flex;align-items:center;gap:16px;min-height:64px;padding:10px 16px;background:var(--card);border:1px solid var(--stroke);border-radius:4px;cursor:default}
details.sexp > summary::-webkit-details-marker{display:none}
details.sexp > summary:hover{background:var(--ctrl-h)}
details.sexp > summary > svg:first-child{width:20px;height:20px}
details.sexp > summary .chev{width:12px;height:12px;color:var(--text-2);transition:transform .15s}
details.sexp[open] > summary{border-bottom-left-radius:0;border-bottom-right-radius:0}
details.sexp[open] > summary .chev{transform:rotate(180deg)}
details.sexp .inner{background:var(--card);border:1px solid var(--stroke);border-top:0;border-radius:0 0 4px 4px;padding:4px 16px 12px 52px}
details.sexp .srow .field{width:260px}
.sounds{display:flex;flex-direction:column;gap:8px}

/* ---------- доступ ---------- */
.idrow{display:flex;align-items:center;gap:12px;margin:12px 0;flex-wrap:wrap}
.idrow b{font:600 20px/26px var(--font-d);letter-spacing:.04em}
.issued{display:grid;grid-template-columns:minmax(0,1fr) auto auto auto;gap:0 14px;margin-top:10px;align-items:center}
.issued > span{padding:8px 0;border-bottom:1px solid var(--divider)}
.issued .act{display:flex;gap:6px;justify-content:flex-end}
.dotx{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--text-3);margin-right:6px}
.dotx.on{background:var(--good)}
.howto ol{margin:8px 0 6px 18px;padding:0}
.howto li{margin:4px 0}
code{font:12px/18px var(--mono);background:var(--sel);padding:1px 5px;border-radius:4px}
.frow{display:flex;flex-direction:column;gap:4px;margin-top:12px}
.frow label{font-weight:400}
.frow small{color:var(--text-2);font-size:12px;line-height:16px}
.frow .field{width:100%}
.linkrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.tgstate{margin-top:10px;padding:8px 12px;border-radius:6px;background:var(--sel);color:var(--text-2)}
.tgstate.warn{background:var(--warn-bg);color:var(--text)}
.tg-help{margin-top:10px}
.srow .combo select:disabled{opacity:.5}
.field:disabled{opacity:.5;cursor:default}

/* ---------- журнал ---------- */
.log{background:var(--card);border:1px solid var(--stroke);border-radius:8px;padding:8px 0;font-size:13px;line-height:20px}
.log div{display:grid;grid-template-columns:76px minmax(0,1fr);gap:8px;padding:2px 16px}
.log div:hover{background:var(--hover)}
.log .t{color:var(--text-3);font-variant-numeric:tabular-nums}
.log .e{color:var(--bad)}
.log .w{color:var(--warn)}
.log .f{color:var(--good);font-weight:600}

/* ---------- окна поверх и подсказки ---------- */
.overlay{position:fixed;inset:0;z-index:50;display:grid;place-items:center;background:var(--smoke)}
.dialog{width:min(540px,92vw);background:var(--card);border:1px solid var(--stroke);border-radius:8px;box-shadow:var(--shadow-2);overflow:hidden}
.dialog .db{padding:24px}
.dialog h2{font:600 20px/28px var(--font-d);margin-bottom:8px}
.dialog .df{display:flex;justify-content:flex-end;gap:8px;padding:20px 24px;background:var(--layer);border-top:1px solid var(--stroke)}
.dialog .dc{display:flex;align-items:center;gap:14px}
.dialog .dc .ring{width:28px;height:28px}
.toast{position:fixed;bottom:24px;left:50%;transform:translate(-50%,16px);background:var(--card);color:var(--text);border:1px solid var(--stroke);
  box-shadow:var(--shadow);padding:10px 16px;border-radius:8px;opacity:0;transition:opacity .18s,transform .18s;pointer-events:none;z-index:60;max-width:min(560px,90vw)}
.toast.on{opacity:1;transform:translate(-50%,0)}
.toast.err{border-color:color-mix(in srgb,var(--bad) 40%,var(--stroke));background:var(--bad-bg)}
@media (prefers-reduced-motion:reduce){.toast{transition:none}}

/* ---------- узкое окно ---------- */
/* окно уже 1360 px (с учётом размера интерфейса) — классы ставит скрипт в <head> */
:root.w1360 #dealsTable .thead,:root.w1360 #dealsTable .tr{grid-template-columns:minmax(0,1fr) 100px 100px 84px 124px 36px;gap:10px}
:root.w1360 .detail{width:310px}
:root.w1360 .cmdbar .search{width:200px}
/* окно уже 1180 px (с учётом размера интерфейса) — классы ставит скрипт в <head> */
:root.w1180 .detail{position:fixed;top:0;right:0;bottom:0;z-index:30;box-shadow:var(--shadow-2);transform:translateX(105%);transition:transform .2s ease;width:360px}
:root.w1180 .detail.open{transform:none}
:root.w1180 .detail .x{display:grid}
:root.w1180 .profit{grid-template-columns:1fr}
:root.w1180 .cols{grid-template-columns:1fr}
/* окно уже 1100 px (с учётом размера интерфейса) — классы ставит скрипт в <head> */
:root.w1100 .app{grid-template-columns:52px minmax(0,1fr)}
:root.w1100 .who{justify-content:center;padding:12px 0 16px}
:root.w1100 .who div,:root.w1100 .nav .lbl,:root.w1100 .pane .ver{display:none}
:root.w1100 .nav button{justify-content:center;padding:0}
:root.w1100 .nav .cnt{position:absolute;top:2px;right:2px;margin:0}
:root.w1100 .nav button.on:before{left:0}
:root.w1100 .prow{grid-template-columns:minmax(0,1fr) 110px 120px;}
:root.w1100 .prow .acts{grid-column:1/-1;justify-content:flex-start}
:root.w1100 .pfoot{padding-left:16px}
</style>
</head>
<body>
<div class="app">
  <aside class="pane">
    <div class="who"><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAPJ0lEQVR42tWbeZRV1ZWHv33uGwpKCqhiclaQQVE72ixBEDUORFA0nazCKWo7a0ScWgUVi0LBEdRgOi5XjDNKFTZqVnc0ihTikKTFGdPIUqMyQxVCkar37r3n7P7jvvfq1UQx1EvgrnX/qLVe3Xt+39l7n733OVfYwUsVobrc0Hu9wInsHlcNbOijlFc7EbQgr9Cqck+ryj1282tHxxnr8IEVFQZAJlRaAP3y/JLGWnekiBkU+GE/azUJouYfLNRFoxMxJkgWeWs99Mt4Fz6TI+duylkqFSJS6bb1HOmIpkyotgAN7517gqheEjpO9kT2TSY9jHT4iH/EnKMKad8SOl1rhJqEMU/ER859s6WGHQKQ/cfN75w/OCH2PlU5KxE3NKRC/MAp4IQC+dsOI0AAk4gZ6dolRmgdKK8FVm/tdvyLn24LgrQd6Mo9kWpb//aEc4zIY4m4133z1rRTRQUxIv/0aW8vQKuiDpDueyVMELoG65hUcsK8J9qDIO2Jr3uzfGJxV29OQyokDDUU6The7E6XU7WeMV73bnG2bg1u63Hy/Huy2vJ/Z1qZvVTbHxb+fEJxFzOnvsG3QegcQkw1svc94lYQES+0Tjdt8cO9imMza//488tFqm3LFUKaZr7CQKVurikfIKofWnXFQaiIiEGVPfISwTnVeExcPGbC0NrhpScv+CTfHUyL32sQhA8lE6ab7zsHGHVuz5n5lrdziCB+aIl5krSWOaoIyw7TZhaQJVL71vhRHvF3GtPW5WZepKBRK0u+oO8QQVVtt64xL+27sWWnLngtq7lZYNPQXJUoMjSmQqcQASiU+UfmGQUiAwV1M1U0WrHVqv4SeI3yyApEFRFBN/7ptJKgLvFlzJO+oVXX0j06cc1GAOuU4iIPEWFrY4hnCruyqqKeJ6KqW4rjOqjbKb9fpxUVxlBdbgBMfdGRiZj0TQdWnapxqhTiRhU/tJSWJHj9T2t4ZfFKSksSBKFDC/ROpwqoBKF1RUlT0qgyDIBpX0gsqurAOTu4KBmjIR06gYIVPYF1lJYkefPPa7jhoaX4oSMRF8aP3pfazWliXmGqisgBcHFPTKpRhwD/Tc16ycUA32q/IjSTWhfGH8OM+IUfrOXq+/4XgKKEx6RZS1GF8aP3KSwEBXWK4vq1qgZtYBOqHqqFF//L+z9AHSQTkVDnhOtmLwWUM44rHITIAxXFJdoqh1VVCwIgtEppSYK3PljHNQ9E4ouSHlv+HqAKJcUxwHHd7A9RLRyELABUtA0AURDqbAD54ic+uBTnoEuRx7raNGefsh9FSY+n/+db+vRMgm+5/qGP8iD4xDzpdADOudYNEecy/tFJAAQIrFKWEX/trA9z4jdsSjN+9N7MuPoIYp4h5TuqFn5P755JSFtuePhjFDhj1N6dCiFnAW11hFwnWoBEQTUSv3R9K/FnjNqbWdf9C35gSaUt9159OIIyb+HKHIQbH/4YVDm9EyHkLEDbsABc7he7nOQEWbNfup5Jsz9qJv70UXvz4KQjCUOHtQ4QGlIhM646HICqhSvplYXwyCdoBkJdZ0BQopzAtdkT3HkL0BZm37MkzltL13PdQx83Fz+yHw9OPIIwdAShwxgBlNAqjSnl7iuHokB1HoSb5nwKwLiR/XIQdHv6ee0NVJX8RlazGJDNmmQXfL5nSZyapRuY9PCnaAvxD0w8gtBG4mOeYEymVvGEMHQRhCsOA1Wq31pFrx5J8B03zfkUVWXcsf2o29IEQXfSAmwmCNa0tIBdcYFIfIKaDzdw/cOfoU5z4seN7Mf9Ew/PiTdGKC7yuP3xL2hIWx685gganSO0jlSaCALkQVBufvSzCMLIDISdqR20ddHVfBXYSRcI88Tf8MhnuJx4PxJ/zdBmZl9c5DH9d/9H1cJVqEIyZph++aGoWoLQoqrR38D8DIS077jl158DMPbYvjsHQUHVRWI7KwZk1/nFH27ghl993iT+B59xx/bhvqsPayV+xlPLefoP31FakkAkmmlVmH75kDwIjumXDQGF+YsyEALlll9/jqoydkRf6up3EEJ2FWhzYyRnAW67w0tWfM1HG7mxhfixI/pw79WHtTL7GU8v55k/RBWgzfQDyronmL9oFaBMvywLIZqQ6ZcNBpT5i1ZHELDc+p/LQJXTdhRCdoLbWgZ3NA/IF3/TnM+bov0PPmNH9Obeqw7Nifcy4mc+8yXPvLaS0pJ4Tnz2WRGE1aBQedngZhAqLx0MkAfBcetvvkCBscN7U1sfbB+EjD7n2rMAOqgDM92T0Dp6douz+KON3PTospz4jT/4jB3em3uvjMSHoWIMdC3ymPnMCp59fSWl3ZqLbwVh8WqUSLRq9IxGtUy7ZBCqykuL19Cre5I0yuTffIHqoZw2vA+b6n08z9BRG6/l/DazAOcc6lz7DxDBZsS//XEdNz36Bc5FJe36ujRjj+3DPVcOIbCO0CqeEfbq4jHz2RU8+/qqdsU3g1CS4L8WrwWg8tJBpH0lsI7GtEYQgJcWraFXjwQ+yuTH/hoFxhG9qdsSRLmFc+1bgHM4bDubox1Yv7OOLkmP1/68ntsfX44gJBOG+saQn53QjzsvHogfOpxTREBEqHjiS+bXrOlQfPMVJc6Ct9eSDhx3XjQQI2CtoyHlmHbxQIoShpdq1lLcxUMwTH7srzSmQ8aO6ENjymYSrA53Vlu7gIvCJK793RZASaUtoVWSccnl18mEwTOQdi5nZuocDWm7w43f7E8bUhanDkEy8QmMQFHC5BI6YyBMK41pG409u4PTjgW4bRVDdOACJtPAPHNUH5Jxw5THlxPzDN26xnjhzdWkfUfFxYeQ8iMrMAIzLh9IIiYseHsdpSVxQrttK4h5Qt2WgJ8c04uZVwzGuiiQikBxlxj3PPcVz/1xFWWZVSSVdky7ZCA/O74vdfUBnmzbBXAODV0bW2PZRHCbW06RqI2bfU4dVsaMywZhrcMPld49kry8ZC3Tn1xBMi6IgB86GlOWqRcN4N9G96VuS7DNgiZf/N2XDyQILenAAVEH+f7nv2buG6vp1T0j3ndM/fcB/PS4Pmzc7GOkKZBv63a7Wg57Bmq3+Iw5pgxlIFN/u4I0UNY9yYIl61Fg6kUDcgFM08odF/VHgZeXrKNnSRzbwhKy4scc04u7LjskSp5sBLy4KMZ9c79m7htrclaU8i1TLzqEn47uQ222Puho7Dl9btdTYc9A7WafMcPKQJWpT3xFGkdZ9wQvL1kPwB0X9kfzIVx4MKC8vGQ9PfOCYswT6uoDxhxTxl2XDmgSbyLx97/wTSvxd1w4gLOO65XrFWzXuLNtcjopFc5awqnDSlGFqb/7ClpAuP2Cg5tBuP2Cg0GVl9/ZQM+SOALU1YeMGVbGXRc3ifcMFCdjPPDCN8x9c22eeMftF/TnrON6U7c5wNte8fmJkHZiMRRBCDh1WE+gP3c++TXpoAmCquYghBkIt11wMAr8/r2NAIwZVsr0S/oT2CbxXZMxHnjxb7zQSvzBGfH+jonPrPOa3xCp6aSGSBbCKf/aE9WDqXjym5w7vPLOBgBu+8VBpPMg3HHBQfiBo9F3kfjczAtdk4YH533bSvxtvziIM0eVUbfFxzOyE2PNWEBbDZFdbYnFDNTlIMC0p77Bx1HWPZ6DMOX8A0kHEYSUD5PPOxBVmlWLXZPCrHnf8cLCdS3EH8hZo8qo2xJE+4g7NU7NLYXtrgJuF3qCXg5CD+Agpj31t0y1F0FQ1QiCU/zA5jZE02EU7bsmDbOqvufFluLPP4Azj+1FbZ54t5NNwXYTIVxTprezO2OaB+Hko3ugeiCVT3+bg/Dqu5HPTznvAFK+5lYByYifXfU9Ly5qLn7K+Qcw/tgyarNl7y5t3EWlsLpOKIe3xxJOPrpHVNTkQ3hvIyhMPm9/Gv0obS4u8phdvZJ5izZQ2q1J/OTz9mf8iNJcubvrY2utL1bTLBN0nbYx4hmoqw846ajuqB7A9Ge+iyCUxHn1/VoUZfK5++MZYXb191TVbKS0W6xJ/LmdLT4vCLbfEDGdujXmSXMIdz2bhRDj1XdrKYobkgnDvEUbKMsz+1vP2Y8zRpRGuX2niW9jGWy7Jda5e4OewKb6gJOOKgHdn7ue/x4NoLR7nFfeqwVoZva3nLMfp48opa7e72TxHSyDTp10tgU0VZERhB8fVYKyH3c/txIh8n0gV9jccva+nD68J5vqA6LmTmePRTP7n1baaogEhdoez4dw0o9KUN2XGc+vQgAxkPIdN0/Yh3HNxBfkiES2Jxg0AchEwbin69Qp6lQKdWotFxN+VALAjOdXEfrKLWfvw+nDe+TEF+oIdq5QVtblAJw4tI8CBKGsUBxOMQYt2DHwfAiptCUdaEZ8mDkux04mOR13mRyYIHAYo8ubLKC82gGEW80nrjjYEPOkd2jRQp0Ij5IlyQVGIXKNbB+vUOCdop7BNKTtVjX6QVQLLXYxEbSqHG/0lM82vfurIYuK4lK+1VqrrrCnw0WEhlTULzRGmmVnBQLvknHPpH19d9S1y1drBUYqcVFLrLw8Mk/VxwLrRF10iEZVC3aaW1URojvb8CzMuzIanIKqqLjHABha3vx7l4oKTGUlbslDg97okjCnbG20Vozs9h9JbdfsO7Vdi4yXDvQva/b9cuSyZWhlZRRqck3RadlYofb6ILSNxiDOOdVM8bBH3upwzqkRxTkNPU+vnTABO/SLponPAZBKXFUVZvSNXy0LnU4sTooR1Gbb/Hvi7RwqqN2rq/Ea0+6WkZNW/EWryr0J1U1bQ60/manCkwnYxbMGTClOmpn1KYdzakX2MHdQtYiYHsVG/p6yM0bf+PUdiyqI/biSsK1NmGZXVRXehAnYmgcHXBH3eMQzFG1NucxXYmKQgp7w3+nlNUpfolKva9LznLrQWr31+P/4ZnZGk2u50rarIwth8ewBR3viHjAiJwlCynfYaL/K7WbijWfEFCVMdBxf3btgbj7uhq/eryqnmdlvF4B8CADvP9x/XBjqFaFyfNyjZ9zbvWwgdIof6JaYkXc8cb8dedO3C/JduqN9yPbpVmCYhmY/Sl48+4C9VeUoLENCZW+BBPJP+oBSEVQDY1gbE295POF/NOK6VSvzxy6VnWSpVVV4WoHZ3WNfRQWmqmr7v3eQnXnB0KFI72Un7FY+cOLQxTotL8HZ3uv/AQYWESZbCLZ4AAAAAElFTkSuQmCC" alt=""><div><b>STALZONE Трекер</b><small id="modeLbl">аукцион, сервер RU</small></div></div>
    <nav class="nav" aria-label="Разделы">
      <button data-view="deals" class="on"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="7" cy="7" r="4.6"/><path d="m10.4 10.4 3.6 3.6"/></svg><span class="lbl">Находки</span><span class="cnt hot" id="cntDeals"></span></button>
      <button data-view="items"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="2" y="2" width="5" height="5" rx="1"/><rect x="9" y="2" width="5" height="5" rx="1"/><rect x="2" y="9" width="5" height="5" rx="1"/><path d="M11.5 9v5M9 11.5h5"/></svg><span class="lbl">Предметы</span><span class="cnt" id="cntItems"></span></button>
      <button data-view="buys"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M2.8 5.2h10.4l-.9 8a1 1 0 0 1-1 .9H4.7a1 1 0 0 1-1-.9z"/><path d="M5.8 5.2V4.4a2.2 2.2 0 0 1 4.4 0v.8"/></svg><span class="lbl">Мои покупки</span><span class="cnt" id="cntBuys"></span></button>
      <button data-view="craft"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M6 1.8h4M6.6 1.8v4.3L2.9 12.6a1 1 0 0 0 .9 1.6h8.4a1 1 0 0 0 .9-1.6L9.4 6.1V1.8M4.6 10h6.8"/></svg><span class="lbl">Крафт</span></button>
      <button data-view="access"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="6" cy="5.5" r="2.5"/><path d="M1.8 13.5c.5-2.4 2.1-3.6 4.2-3.6s3.7 1.2 4.2 3.6M11 4.5h4M13 2.5v4"/></svg><span class="lbl">Доступ</span><span class="cnt" id="cntAccess"></span></button>
      <button data-view="log"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M3 4h10M3 8h10M3 12h6"/></svg><span class="lbl">Журнал</span></button>
    </nav>
    <div class="foot nav">
      <button data-view="settings"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M8 5.6a2.4 2.4 0 1 0 0 4.8 2.4 2.4 0 0 0 0-4.8z"/><path d="M6.9 1.6h2.2l.4 1.7 1.2.7 1.7-.5 1.1 1.9-1.3 1.2v1.4l1.3 1.2-1.1 1.9-1.7-.5-1.2.7-.4 1.7H6.9l-.4-1.7-1.2-.7-1.7.5-1.1-1.9 1.3-1.2V7.4L2.5 6.2l1.1-1.9 1.7.5 1.2-.7z"/></svg><span class="lbl">Настройки</span></button>
      <div class="ver" id="verLbl"></div>
    </div>
  </aside>

  <div class="main">
    <section class="page">
      <header class="head">
        <h1 id="viewTitle">Находки</h1>
        <div class="status"><svg class="ring" id="ring" viewBox="0 0 16 16" hidden><circle cx="8" cy="8" r="6.5"/></svg><span class="dotst" id="dot"></span><span id="stateTxt">Поиск остановлен</span></div>
        <button class="btn accent" id="runBtn">Начать поиск</button>
      </header>
      <div class="views" id="views">

        <!-- ============ НАХОДКИ ============ -->
        <div class="view on" id="view-deals">
          <div class="infobar ok" id="updNote" hidden>
            <svg class="ic" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 1 1 0 14A7 7 0 0 1 8 1zm0 3.5a.7.7 0 0 0-.5.2L5.2 7a.7.7 0 0 0 1 1l1.1-1.1V11a.7.7 0 0 0 1.4 0V6.9L9.8 8a.7.7 0 0 0 1-1L8.5 4.7a.7.7 0 0 0-.5-.2z"/></svg>
            <div class="tx"><b id="updTitle">Доступна новая версия</b><span id="updSub"></span></div>
            <button class="btn accent" id="updBtn">Обновить</button>
          </div>
          <div class="infobar warn" id="demoNote" hidden>
            <svg class="ic" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 1 1 0 14A7 7 0 0 1 8 1zm0 3.2a.8.8 0 0 0-.8.8v3.6a.8.8 0 0 0 1.6 0V5a.8.8 0 0 0-.8-.8zm0 6.2a.9.9 0 1 0 0 1.8.9.9 0 0 0 0-1.8z"/></svg>
            <div class="tx"><b>Демо-режим: тестовые данные EXBO, а не настоящий аукцион.</b><span id="demoNoteSub"></span></div>
            <button class="btn" id="demoOffBtn">Выключить</button>
          </div>
          <div class="card" id="onboard" hidden style="margin-bottom:12px">
            <h2>Подключи доступ к API — это займёт пару минут</h2>
            <div class="sub">Без ключей трекер не видит аукцион. Ключи бесплатно выдаёт сама EXBO.</div>
            <div class="list-rows" style="margin-top:8px">
              <div class="srow"><div class="tx"><div>1. Подай заявку</div><small>Отправь /newapp боту EXBO и войди через свой аккаунт</small></div><button class="btn" data-open="api_bot">Открыть @stalzone_api_bot</button></div>
              <div class="srow"><div class="tx"><div>2. Вставь ключи</div><small>После одобрения бот пришлёт Client ID и Client Secret</small></div><button class="btn" data-goto="settings">Перейти в настройки</button></div>
              <div class="srow"><div class="tx"><div>3. Проверь на демо</div><small>Пока ждёшь одобрения, включи демо: ключи для него встроены</small></div><button class="btn" id="demoOnBtn">Включить демо</button></div>
            </div>
          </div>
          <div class="lead" id="lead">
            <div class="st"><b class="num" id="sumN">0</b><span id="sumNl">находок</span></div>
            <div class="st" id="sumAllBox"><b class="num good" id="sumAll">0 ₽</b><span>если купить всё</span></div>
            <div class="st" id="sumExpBox"><b class="num" id="sumExp">0 ₽</b><span>с учётом шанса продать</span></div>
            <div class="why" id="sumS"></div>
          </div>
          <div class="cmdbar one">
            <label class="search"><input class="field" id="search" placeholder="Найти в находках" autocomplete="off" spellcheck="false"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="7" cy="7" r="4.6"/><path d="m10.4 10.4 3.6 3.6"/></svg></label>
            <span class="combo" title="Порядок"><select id="fSort">
              <option value="exp">Выгодные с учётом шанса</option><option value="profit">Самые прибыльные</option><option value="chance">Надёжные</option>
              <option value="listed">Свежие</option><option value="pct">С большей скидкой</option><option value="cost">Дешёвые</option><option value="name">По названию</option>
            </select><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></span>
            <button class="tbtn" id="fRare" aria-pressed="false" title="Только особо редкие находки">Только редкие</button>
            <button class="tbtn on" id="hideOld" aria-pressed="true" title="Не показывать лоты, которых уже нет на аукционе">Скрыть ушедшие</button>
            <span class="grow"></span>
            <button class="ib" id="clearBtn" title="Очистить список находок"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M3 4.5h10M6.2 4.5V3h3.6v1.5M4.5 4.5l.6 9h5.8l.6-9"/></svg></button>
          </div>
          <div class="table" id="dealsTable">
            <div class="thead" id="dealsHead">
              <button data-sort="name">Предмет</button><button class="r" data-sort="cost">Купить</button><span class="r">Продать</span><button data-sort="chance">Шанс</button><button class="r" data-sort="exp" title="Щёлкни ещё раз — по прибыли без учёта шанса">Прибыль</button><span></span>
            </div>
            <div id="rows" role="listbox" aria-label="Находки"></div>
            <div class="empty" id="empty"><svg class="ring" id="emptyRing" viewBox="0 0 16 16" hidden><circle cx="8" cy="8" r="6.5"/></svg><h3 id="emptyH">Пока ничего не найдено</h3><p id="emptyT">Нажми «Начать поиск» — трекер начнёт проверять аукцион.</p></div>
          </div>
          <details class="expander" id="nearBox" hidden>
            <summary><svg class="chev" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m4.5 2.5 3.5 3.5-3.5 3.5"/></svg><div><b id="nearTitle">Почти находки</b><span>Дешевле рынка, но не прошли твои пороги — видно, что именно отсеяно. Пороги — в <a href="#" data-goto="settings">«Настройках»</a>.</span></div></summary>
            <div class="body" id="nearRows"></div>
          </details>
        </div>

        <!-- ============ ПРЕДМЕТЫ ============ -->
        <div class="view" id="view-items">
          <div class="cols">
            <div class="card">
              <h2>Каталог предметов</h2>
              <div class="sub">Найди предмет и нажми «Следить». Звёздочка — особо редкий: о нём придёт отдельное уведомление.</div>
              <label class="search" style="width:100%;margin-top:12px"><input class="field" id="catSearch" placeholder="Например: Морфин, вихрь, запчасти, броня" autocomplete="off" spellcheck="false"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="7" cy="7" r="4.6"/><path d="m10.4 10.4 3.6 3.6"/></svg></label>
              <div class="tabs" id="catTabs"></div>
              <div class="results" id="catResults"><div class="res faint">Загружаю базу предметов…</div></div>
              <div class="small faint" id="catMore" style="margin-top:8px"></div>
            </div>
            <div class="stack">
              <div class="card" id="yieldBox" hidden>
                <h2>Что приносит находки</h2>
                <div class="sub" id="yieldSub"></div>
                <div id="yieldBody" style="margin-top:8px"></div>
              </div>
              <div class="card">
                <h2>Мой список <span class="faint" id="watchCnt" style="font-weight:400"></span></h2>
                <div class="note ok" id="subItemsNote" hidden>Подписка: список и категории — это фильтр. Показываю находки сервера только по ним, а если пусто — все.</div>
                <div class="list-rows" id="chips" style="margin-top:6px"></div>
                <div class="faint" id="chipsEmpty" style="margin-top:8px">Список пуст.</div>
              </div>
              <div class="card">
                <h2>Категории целиком</h2>
                <div class="sub">Трекер сам проверит все предметы категории, даже если их нет в твоём списке.</div>
                <div class="list-rows" style="margin-top:4px">
                  <label class="srow"><div class="tx"><div>Артефакты</div><small id="artSub">все артефакты из базы игры</small></div><span class="toggle"><span class="tr-st"></span><input type="checkbox" data-cat="artefact" id="sAllArts"><i></i></span></label>
                  <label class="srow"><div class="tx"><div>Броня</div><small data-cnt="armor"></small></div><span class="toggle"><span class="tr-st"></span><input type="checkbox" data-cat="armor"><i></i></span></label>
                  <label class="srow"><div class="tx"><div>Оружие</div><small data-cnt="weapon"></small></div><span class="toggle"><span class="tr-st"></span><input type="checkbox" data-cat="weapon"><i></i></span></label>
                  <label class="srow"><div class="tx"><div>Запчасти</div><small data-cnt="parts"></small></div><span class="toggle"><span class="tr-st"></span><input type="checkbox" data-cat="parts"><i></i></span></label>
                  <label class="srow"><div class="tx"><div>Инструменты</div><small data-cnt="tools"></small></div><span class="toggle"><span class="tr-st"></span><input type="checkbox" data-cat="tools"><i></i></span></label>
                </div>
                <div class="note">Каждый предмет — 1–2 запроса к API за круг (лимит EXBO — 400 в минуту на ключ). Чем больше предметов, тем длиннее круг. Цена брони и оружия зависит от заточки — такие находки проверяй в игре.</div>
              </div>
            </div>
          </div>
        </div>

        <!-- ============ МОИ ПОКУПКИ ============ -->
        <div class="view" id="view-buys">
          <div class="profit">
            <div class="card pmain">
              <div class="top"><h2>Заработано</h2>
                <div class="selector" id="pPeriod"><button data-p="day">Сегодня</button><button data-p="week">7 дней</button><button data-p="month">30 дней</button><button data-p="all">Всё время</button></div></div>
              <div class="earned num" id="pEarned">0 ₽</div>
              <div class="pline" id="pLine">Пока ничего не продано.</div>
              <div class="days" id="pDays"></div>
            </div>
            <div class="pside">
              <div class="kpi"><span>В товаре сейчас</span><b class="num" id="bInv">0 ₽</b><small id="bInvS">ещё не продано</small></div>
              <div class="kpi"><span>Ожидается ещё</span><b class="num good" id="bExp">0 ₽</b><small>по ценам рынка, после комиссии</small></div>
              <button class="kpi kbtn" id="bBestBox" title="Показать эту продажу"><span>Лучшая сделка</span><b class="num" id="bBest">—</b><small id="bBestS">появится после первой продажи</small></button>
            </div>
          </div>
          <div class="cmdbar">
            <div class="selector" id="bSeg"><button data-b="open" class="on">Не проданы<em id="bCntOpen"></em></button><button data-b="sold">Проданы<em id="bCntSold"></em></button><button data-b="all">Все<em id="bCntAll"></em></button></div>
            <span class="daychip" id="bDayBox" hidden><span id="bDayTxt"></span><button class="ib" id="bDayClear" title="Показать все продажи">✕</button></span>
            <span class="grow"></span>
            <span class="small faint">Купил лот из находок — выбери его и нажми «Я купил».</span>
          </div>
          <div id="bRows"></div>
          <div class="card empty" id="bEmpty"><h3 id="bEmptyH">Пока нет покупок</h3><p id="bEmptyT">Купил лот из находок — выбери его и нажми «Я купил». Трекер будет следить за его ценой и подскажет, за сколько выставить.</p></div>
          <div class="card acc" id="accBox" style="margin-top:12px">
            <h2>Сбываются ли прогнозы</h2>
            <div class="sub" id="accSub">Трекер запоминает свою оценку каждой находки и через несколько часов сравнивает её с тем, за сколько такие лоты реально продавали.</div>
            <div id="accBody"></div>
          </div>
        </div>

        <!-- ============ КРАФТ ============ -->
        <div class="view" id="view-craft">
          <div class="cols">
            <div class="card">
              <h2>Мои навыки в убежище</h2>
              <div class="sub">По уровням видно, какие рецепты тебе доступны. Сохраняются сами.</div>
              <div class="skills" id="skills"></div>
            </div>
            <div class="card">
              <h2>Какой навык качать</h2>
              <div class="sub">Что откроет следующий уровень каждого навыка — по сегодняшним ценам аукциона.</div>
              <div class="advice" id="advice"><div class="faint">Загружаю рецепты…</div></div>
            </div>
          </div>
          <div class="cmdbar" style="margin-top:16px">
            <label class="search"><input class="field" id="crSearch" placeholder="Найти рецепт или ингредиент" autocomplete="off" spellcheck="false"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="7" cy="7" r="4.6"/><path d="m10.4 10.4 3.6 3.6"/></svg></label>
            <button class="tbtn on" id="crMine" aria-pressed="true">Только доступные мне</button>
            <span class="combo"><select id="crSort"><option value="profit">Самые прибыльные</option><option value="energy">Больше прибыли на 1000 энергии</option><option value="name">По названию</option></select><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></span>
            <span class="grow"></span>
            <span class="small faint" id="crPrices"></span>
            <button class="btn" id="crFetch">Узнать цены</button>
          </div>
          <div class="table ctable">
            <div class="thead"><span>Что получится</span><span>Из чего</span><span class="r">Стоимость</span><span class="r">Продать за</span><span class="r">Прибыль</span><span class="r">На 1000 энергии</span></div>
            <div id="crRows"></div>
          </div>
          <div class="small faint" style="margin-top:10px">Щёлкни рецепт — справа будет, за сколько выставлять готовое и до какой цены брать каждый ингредиент. Цены — медиана сделок за неделю из твоей базы, продажа — после комиссии 5%.</div>
        </div>

        <!-- ============ НАСТРОЙКИ ============ -->
        <div class="view" id="view-settings">
          <div class="settings">
            <div class="group"><h2>Что считать находкой</h2>
              <div class="scard"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M5 15 15 5"/><circle cx="6" cy="6" r="2"/><circle cx="14" cy="14" r="2"/></svg><div class="tx"><div>Дешевле рынка минимум на</div><small>Лот дороже — не находка</small></div><div class="ctl"><span class="unit"><input class="field num" id="sDiscount" inputmode="numeric"><i>%</i></span></div></div>
              <div class="scard"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="2.5" y="5" width="15" height="10" rx="1.5"/><circle cx="10" cy="10" r="2.2"/></svg><div class="tx"><div>Минимальная прибыль</div><small>После комиссии аукциона 5%</small></div><div class="ctl"><span class="unit"><input class="field num" id="sMinProfit" inputmode="numeric"><i>₽</i></span></div></div>
              <details class="sexp" id="bidExp">
                <summary><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M5.5 2.5h9M5.5 17.5h9M6.5 2.5c0 4.5 7 4.5 7 7.5s-7 3-7 7.5M13.5 2.5c0 4.5-7 4.5-7 7.5s7 3 7 7.5"/></svg><div class="tx" style="flex:1;min-width:0"><div>Лоты со ставками</div><small class="muted" id="bidSum"></small></div><svg class="chev" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></summary>
                <div class="inner">
                  <div class="srow"><div class="tx"><div>Искать лоты со ставками</div><small>Торги скоро закончатся, а ставка намного ниже рынка. Ставку делаешь сам в игре</small></div><label class="toggle"><span class="tr-st"></span><input type="checkbox" id="sBids"><i></i></label></div>
                  <div class="srow"><div class="tx"><div>Сообщать, если до конца торгов меньше</div><small>От 5 до 720 минут</small></div><span class="unit wide" style="width:130px"><input class="field num" id="sBidWindow" inputmode="numeric"><i>мин</i></span></div>
                  <div class="srow"><div class="tx"><div>Но не меньше</div><small>Чтобы не приходило то, что уже не успеть</small></div><span class="unit wide" style="width:130px"><input class="field num" id="sBidMin" inputmode="numeric"><i>мин</i></span></div>
                  <div class="small faint" style="margin-top:6px">Для ставок действует «Минимальная прибыль», а «Дешевле рынка» — нет. В сообщении о находке — предельная ставка: выше неё прибыль будет меньше минимальной.</div>
                </div>
              </details>
            </div>

            <div class="group"><h2>Вид</h2>
              <div class="scard"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="10" cy="10" r="7"/><path d="M10 3a7 7 0 0 1 0 14z" fill="currentColor"/></svg><div class="tx"><div>Тема</div><small>Рамка окна меняется вместе с ней</small></div><div class="ctl"><span class="combo"><select id="sTheme"><option value="system">Как в Windows</option><option value="light">Светлая</option><option value="dark">Тёмная</option></select><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></span></div></div>
              <div class="scard"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M3 15.5 7.5 4h1L13 15.5M4.6 11.5h6.8M13.5 15.5l2.25-6h.5l2.25 6M14.2 13.7h3.1"/></svg><div class="tx"><div>Размер интерфейса</div><small>Текст, кнопки и таблицы — меньше или крупнее. Меняется сразу</small></div><div class="ctl"><span class="combo"><select id="sScale"><option value="s">Маленький</option><option value="m">Средний</option><option value="l">Крупный</option></select><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></span></div></div>
              <div class="scard"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="2.5" y="3.5" width="15" height="13" rx="1.5"/><path d="M7 3.5v13"/></svg><div class="tx"><div>Вид программы</div><small>Классический — как было в версии 2.5. Переключается сразу, находки и настройки не теряются</small></div><div class="ctl"><span class="combo"><select id="sUi"><option value="new">Новый</option><option value="old">Классический</option></select><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></span></div></div>
            </div>

            <div class="group"><h2>Доступ к API</h2>
              <div class="note ok" id="sharedNote" hidden style="margin:0 0 6px">Работает ключ API владельца из кода доступа — свои ключи не нужны. Впишешь свои — будут использоваться они.</div>
              <div class="note ok" id="feedNote" hidden style="margin:0 0 6px">Подписка: находки приходят с сервера владельца — ключи EXBO не нужны.</div>
              <div class="scard" id="demoRow"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M4 4h12v9H8l-4 3z"/></svg><div class="tx"><div>Демо-режим</div><small>Тестовые данные EXBO вместо настоящего аукциона, ключи не нужны</small></div><div class="ctl"><label class="toggle"><span class="tr-st"></span><input type="checkbox" id="sDemo"><i></i></label></div></div>
              <details class="sexp" id="keysExp">
                <summary><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="7" cy="10" r="3.5"/><path d="M10.5 10H18M15 10v3M17.5 10v2"/></svg><div class="tx" style="flex:1;min-width:0"><div>Ключи EXBO</div><small class="muted" id="keysSum">Client ID и Client Secret от @stalzone_api_bot</small></div><svg class="chev" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></summary>
                <div class="inner">
                  <div class="srow"><div class="tx"><div>Client ID</div></div><input class="field" id="sClientId" autocomplete="off" spellcheck="false"></div>
                  <div class="srow"><div class="tx"><div>Client Secret</div></div><input class="field" id="sClientSecret" type="password" autocomplete="off"></div>
                  <div class="frow"><label for="sKeys">Ещё ключи API</label><small>Необязательно. По одному в строке: Client ID, пробел, Client Secret. Запросы делятся между ключами, каждый добавляет 400 в минуту. Сохранённые секреты показаны точками.</small>
                    <textarea class="field code" id="sKeys" placeholder="4729 секрет&#10;4730 секрет" autocomplete="off" spellcheck="false"></textarea><small id="keysInfo"></small></div>
                  <div class="linkrow"><button class="btn" data-open="api_bot">Получить доступ</button><button class="btn subtle" data-open="docs">Документация</button></div>
                </div>
              </details>
            </div>

            <div class="group"><h2>Уведомления</h2>
              <div class="scard"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M4 8h3l4-3.5v11L7 12H4z"/><path d="M14 7.5a3.5 3.5 0 0 1 0 5"/></svg><div class="tx"><div>Звук при находке</div><small>Играет, когда появляется новая находка</small></div><div class="ctl"><label class="toggle"><span class="tr-st"></span><input type="checkbox" id="sSoundOn"><i></i></label></div></div>
              <details class="sexp" id="soundExp">
                <summary><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M7 14.5V5l9-2v9.5"/><circle cx="5" cy="14.5" r="2"/><circle cx="14" cy="12.5" r="2"/></svg><div class="tx" style="flex:1;min-width:0"><div>Какой звук</div><small class="muted" id="soundSum"></small></div><svg class="chev" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></summary>
                <div class="inner">
                  <div class="srow"><div class="tx"><div>Обычная находка</div></div><span class="combo" style="width:260px"><select id="sSound"></select><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></span><button class="btn" data-play="sSound" title="Прослушать"><svg viewBox="0 0 16 16" fill="currentColor"><path d="M5 3.5v9l7-4.5z"/></svg>Прослушать</button></div>
                  <div class="srow"><div class="tx"><div>Особо редкая находка</div></div><span class="combo" style="width:260px"><select id="sSoundRare"></select><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></span><button class="btn" data-play="sSoundRare" title="Прослушать"><svg viewBox="0 0 16 16" fill="currentColor"><path d="M5 3.5v9l7-4.5z"/></svg>Прослушать</button></div>
                  <div class="srow"><div class="tx"><div>Громкость</div></div><input type="range" class="range" id="sVolume" min="0" max="100" step="5"><span class="num" id="sVolumeV" style="width:40px;text-align:right"></span></div>
                  <div class="srow"><div class="tx"><div>Свой звук с компьютера</div><small>wav, mp3, ogg или m4a, до 4 МБ. Сохранится в папке данных программы</small></div><button class="btn" id="soundPick">Выбрать файл…</button><input type="file" id="soundFile" accept=".wav,.mp3,.ogg,.m4a,audio/*" hidden></div>
                  <div class="list-rows" id="customSounds"></div>
                </div>
              </details>
              <details class="sexp" id="tgExp">
                <summary><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><path d="m3 9.5 13.5-5.5-2.5 12-4-3.5-2 2.5v-4l6-5.5"/></svg><div class="tx" style="flex:1;min-width:0"><div>Telegram</div><small class="muted" id="tgSum">Сообщение о каждой находке и о важном: продано, перебили, поиск встал</small></div><svg class="chev" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></summary>
                <div class="inner">
                  <div class="srow"><div class="tx"><div>Токен бота</div><small>Создай бота у @BotFather</small></div><input class="field" id="sTgToken" type="password" autocomplete="off"></div>
                  <div class="srow"><div class="tx"><div>Chat ID</div><small>Напиши своему боту «Start» в Telegram и нажми «Найти» — трекер узнает его сам</small></div><input class="field" id="sTgChat" autocomplete="off" style="width:150px"><button class="btn" id="tgFindBtn">Найти</button></div>
                  <div class="linkrow"><button class="btn" id="tgTestBtn">Проверить Telegram</button><button class="btn subtle" data-open="botfather">Открыть @BotFather</button></div>
                  <div class="tgstate small" id="tgState" hidden></div>
                  <div class="srow"><div class="tx"><div>Кнопки и команды</div><small>Под находкой — «Купил», «Скрыть», «Тишина на час»; команды /status, /finds, /profit, /buys, /stop, /go, /mute, /min</small></div><label class="toggle"><span class="tr-st"></span><input type="checkbox" id="sTgControl"><i></i></label></div>
                  <div class="srow"><div class="tx"><div>Картинка предмета</div><small>Сообщение о находке — с изображением предмета</small></div><label class="toggle"><span class="tr-st"></span><input type="checkbox" id="sTgPhoto"><i></i></label></div>
                  <div class="srow"><div class="tx"><div>Тихие часы</div><small>Находки приходят без звука. Особо редкие — всё равно со звуком</small></div><span class="combo" style="width:96px"><select id="sTgQFrom"><option value="0">00:00</option><option value="1">01:00</option><option value="2">02:00</option><option value="3">03:00</option><option value="4">04:00</option><option value="5">05:00</option><option value="6">06:00</option><option value="7">07:00</option><option value="8">08:00</option><option value="9">09:00</option><option value="10">10:00</option><option value="11">11:00</option><option value="12">12:00</option><option value="13">13:00</option><option value="14">14:00</option><option value="15">15:00</option><option value="16">16:00</option><option value="17">17:00</option><option value="18">18:00</option><option value="19">19:00</option><option value="20">20:00</option><option value="21">21:00</option><option value="22">22:00</option><option value="23">23:00</option></select><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></span><span class="faint">–</span><span class="combo" style="width:96px"><select id="sTgQTo"><option value="0">00:00</option><option value="1">01:00</option><option value="2">02:00</option><option value="3">03:00</option><option value="4">04:00</option><option value="5">05:00</option><option value="6">06:00</option><option value="7">07:00</option><option value="8">08:00</option><option value="9">09:00</option><option value="10">10:00</option><option value="11">11:00</option><option value="12">12:00</option><option value="13">13:00</option><option value="14">14:00</option><option value="15">15:00</option><option value="16">16:00</option><option value="17">17:00</option><option value="18">18:00</option><option value="19">19:00</option><option value="20">20:00</option><option value="21">21:00</option><option value="22">22:00</option><option value="23">23:00</option></select><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></span><label class="toggle"><span class="tr-st"></span><input type="checkbox" id="sTgQuiet"><i></i></label></div>
                  <div class="srow"><div class="tx"><div>Итог дня</div><small>Сколько нашёл, купил, продал и заработал — одним сообщением</small></div><span class="combo" style="width:96px"><select id="sTgDailyH"><option value="0">00:00</option><option value="1">01:00</option><option value="2">02:00</option><option value="3">03:00</option><option value="4">04:00</option><option value="5">05:00</option><option value="6">06:00</option><option value="7">07:00</option><option value="8">08:00</option><option value="9">09:00</option><option value="10">10:00</option><option value="11">11:00</option><option value="12">12:00</option><option value="13">13:00</option><option value="14">14:00</option><option value="15">15:00</option><option value="16">16:00</option><option value="17">17:00</option><option value="18">18:00</option><option value="19">19:00</option><option value="20">20:00</option><option value="21">21:00</option><option value="22">22:00</option><option value="23">23:00</option></select><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></span><label class="toggle"><span class="tr-st"></span><input type="checkbox" id="sTgDaily"><i></i></label></div>
                  <div class="tg-help small faint">Купил по находке — нажми «Купил» прямо в Telegram: покупка появится в «Моих покупках», бот подскажет, за сколько выставить, и даст кнопку «Выставил за …». Лот ушёл — сообщение о находке само поменяется. Бот слушается только твоего Chat ID.</div>
                </div>
              </details>
              <details class="sexp" id="rareExp">
                <summary><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><path d="m10 2.5 2.3 4.8 5.2.7-3.8 3.6.9 5.2L10 14.3l-4.6 2.5.9-5.2L2.5 8l5.2-.7z"/></svg><div class="tx" style="flex:1;min-width:0"><div>Особо редкие</div><small class="muted">Отдельный звук, пометка и сообщение с заголовком «ОСОБО РЕДКИЙ»</small></div><svg class="chev" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></summary>
                <div class="inner">
                  <div class="srow"><div class="tx"><div>Отдельные уведомления</div></div><label class="toggle"><span class="tr-st"></span><input type="checkbox" id="sRare"><i></i></label></div>
                  <div class="srow"><div class="tx"><div>Артефакты от качества</div></div><span class="combo" style="width:200px"><select id="sRareQ"><option value="3">редкий</option><option value="4">исключительный</option><option value="5">легендарный</option></select><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></span></div>
                  <div class="srow"><div class="tx"><div>Минимальная прибыль для них</div><small>После комиссии — можно ниже обычной</small></div><span class="unit" style="width:140px"><input class="field num" id="sRareProfit" inputmode="numeric"><i>₽</i></span></div>
                  <div class="small faint" style="margin-top:6px">Ещё особо редкими считаются снаряжение ранга «Легенда» и всё, что отмечено звёздочкой во вкладке «Предметы».</div>
                </div>
              </details>
            </div>

            <div class="group"><h2>Запуск</h2>
              <div class="scard"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="11" y="3" width="6" height="6" rx="1"/><rect x="3" y="11" width="6" height="6" rx="1"/><rect x="11" y="11" width="6" height="6" rx="1"/></svg><div class="tx"><div>Запускать вместе с Windows</div><small>Окно откроется свёрнутым, поиск начнётся сам. Пока идёт поиск, компьютер не уснёт</small></div><div class="ctl"><label class="toggle"><span class="tr-st"></span><input type="checkbox" id="sAutostart"><i></i></label></div></div>
            </div>

            <div class="group"><h2>О программе</h2>
              <div class="scard"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="10" cy="10" r="7"/><path d="M10 9v5M10 6.2v.1"/></svg><div class="tx"><div>Версия <span id="appVer"></span></div><small id="updInfo"></small></div><div class="ctl"><button class="btn" id="updCheckBtn">Проверить обновления</button></div></div>
              <div class="scard"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M2.5 5.5a1 1 0 0 1 1-1h4l1.5 1.5h7.5a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1z"/></svg><div class="tx"><div>Папка с данными</div><small class="selectable" id="dataDir" style="word-break:break-all"></small><small id="dbInfo">База сделок пока пустая — начнёт копиться после запуска.</small></div><div class="ctl"><button class="btn" id="openDataBtn">Открыть папку</button></div></div>
            </div>
          </div>
        </div>

        <!-- ============ ДОСТУП ============ -->
        <div class="view" id="view-access">
          <div class="cols">
            <div class="stack">
              <div class="card">
                <h2>Этот компьютер</h2>
                <div class="sub">Вставь код от владельца — больше ничего не нужно: компьютер привяжется сам.</div>
                <div class="idrow"><b class="num selectable" id="accMachine">—</b><button class="btn" id="accCopyId">Копировать код запроса</button></div>
                <div class="small faint">Код запроса нужен, только если владелец сам его попросит.</div>
                <div class="note" id="accStatus"></div>
                <div id="accCodeBox">
                  <div class="frow"><label for="accCode">Новый код доступа</label><small>Если владелец прислал новый или продлил старый</small><textarea class="field code" id="accCode" placeholder="SZ1-…"></textarea></div>
                  <div class="linkrow"><button class="btn accent" id="accCodeBtn">Применить код</button></div>
                </div>
              </div>
              <div class="card" id="ownerSetup">
                <h2>Для владельца программы</h2>
                <div class="sub" id="osSub">Закрытый доступ включается один раз: владелец создаёт личный ключ, а его открытая часть вписывается в программу.</div>
                <div class="linkrow" id="osNoKey"><button class="btn accent" id="osCreate">Создать ключ владельца</button></div>
                <div id="osHasKey" hidden>
                  <div class="frow"><label for="osPub">Открытый ключ</label><small>Его не страшно показывать — по нему программа проверяет коды</small><textarea class="field code" id="osPub" readonly></textarea></div>
                  <div class="linkrow"><button class="btn" id="osCopy">Копировать ключ</button><button class="btn subtle" data-opendata="1">Открыть папку с ключом</button></div>
                </div>
                <div class="note warn" id="osWarn" hidden>Личный ключ — файл owner_key.pem в папке данных. Сделай копию (флешка, облако) и никому не отправляй: с ним можно выдавать коды от твоего имени.</div>
              </div>
            </div>
            <div class="stack">
              <div class="infobar err" id="keyWarn" hidden>
                <svg class="ic" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 1 1 0 14A7 7 0 0 1 8 1zm0 3.2a.8.8 0 0 0-.8.8v3.6a.8.8 0 0 0 1.6 0V5a.8.8 0 0 0-.8-.8zm0 6.2a.9.9 0 1 0 0 1.8.9.9 0 0 0 0-1.8z"/></svg>
                <div class="tx"><b>Твой ключ API тратит ещё кто-то.</b><span id="keyWarnText"></span>
                  <div class="linkrow" style="margin-top:8px"><button class="btn" data-open="api_bot">Открыть @stalzone_api_bot</button><button class="btn subtle" data-goto="settings">Вписать новый секрет</button></div></div>
              </div>
              <div class="card" id="serverCard" hidden>
                <h2>Сервер для подписчиков</h2>
                <div class="sub">Один поиск — для всех: твоя программа раздаёт найденное из памяти, подписчики лимит EXBO не тратят, и твой поиск не замедляется. Пока сервер работает, компьютер должен быть включён.</div>
                <div class="list-rows" style="margin-top:6px">
                  <label class="srow"><div class="tx"><div>Раздавать находки подписчикам</div></div><span class="toggle"><span class="tr-st"></span><input type="checkbox" id="srvOn"><i></i></span></label>
                </div>
                <div class="frow"><label for="srvUrl">Публичный адрес</label><small>Его даёт Tailscale Funnel, например https://мой-пк.xxxx.ts.net — он вписывается в новые коды</small><input class="field" id="srvUrl" placeholder="https://…ts.net" autocomplete="off" spellcheck="false"></div>
                <div class="note" id="srvStatus"></div>
                <div class="linkrow"><button class="btn accent" id="srvFunnel">Открыть доступ из интернета</button><button class="btn" id="srvLink" hidden>Открыть ссылку Tailscale</button></div>
                <div class="linkrow"><button class="btn" id="srvSave">Сохранить</button><button class="btn" id="srvTest">Проверить адрес</button></div>
                <details class="note howto"><summary style="cursor:default">Если кнопка не помогла — то же вручную</summary>
                  <ol>
                    <li>Скачай и установи Tailscale: tailscale.com/download → Windows. Войди через Google или Microsoft.</li>
                    <li>Открой «Командную строку» (Win+R → <b>cmd</b> → Enter) и выполни: <code class="selectable" id="funnelCmd">tailscale funnel --bg 8790</code></li>
                    <li>Если попросит — открой ссылку из окна и подтверди включение Funnel.</li>
                    <li>Команда покажет адрес вида https://имя.xxxx.ts.net — вставь его выше, нажми «Сохранить» и «Проверить адрес».</li>
                  </ol>
                  Флаг --bg оставляет сервер открытым и после перезагрузки. Закрыть: <code class="selectable">tailscale funnel --https=443 off</code></details>
              </div>
              <div class="card" id="ownerIssue" hidden>
                <h2>Выдать доступ</h2>
                <div class="sub">Код можно просто отправить: компьютер подписчика привяжется сам при первом подключении. Для группы или канала поставь больше мест — каждый новый компьютер займёт одно.</div>
                <div class="note warn" id="isWarn" hidden>Сервер ещё не открыт в интернет — по новому коду находки не придут. Нажми «Открыть доступ из интернета» в карточке сервера.</div>
                <div class="frow"><label for="isName">Кому</label><small>Имя человека или название группы — по нему потом можно отключить</small><input class="field" id="isName" autocomplete="off"></div>
                <div class="srow" style="margin-top:6px"><div class="tx"><div>Мест</div><small>1 — один человек; больше — один код на группу</small></div><input class="field num" id="isSeats" value="1" inputmode="numeric" style="width:100px"></div>
                <div class="srow"><div class="tx"><div>Срок, дней</div><small>0 — бессрочно</small></div><input class="field num" id="isDays" value="30" inputmode="numeric" style="width:100px"></div>
                <details class="note howto"><summary style="cursor:default">Привязать к конкретному компьютеру сразу</summary>
                  <div class="frow"><label for="isMachine">Код запроса</label><small>Подписчик копирует его в своей программе: «Копировать код запроса»</small><input class="field" id="isMachine" placeholder="SZR1-…" autocomplete="off"></div>
                </details>
                <div class="linkrow"><button class="btn accent" id="isBtn">Создать код</button></div>
                <div id="isResult" hidden>
                  <div class="frow"><label for="isMsg">Сообщение подписчику</label><small>Ссылка на программу, код и что сделать — отправь целиком</small><textarea class="field code" id="isMsg" readonly style="min-height:150px"></textarea></div>
                  <textarea id="isCode" hidden readonly></textarea>
                  <div class="linkrow"><button class="btn accent" id="isCopy">Скопировать сообщение</button><button class="btn" id="isCopyCode">Скопировать только код</button></div>
                </div>
              </div>
              <div class="card" id="ownerList" hidden>
                <h2>Подписчики</h2>
                <div class="sub">«+30 дн.» — новый код с продлением от конца оплаченного срока (места переходят на него). «Освободить» — если подписчик сменил компьютер. «Отключить» сразу закрывает находки.</div>
                <div class="issued" id="issuedList"></div>
                <div class="linkrow"><button class="btn" data-open="revoked_new">Создать revoked.txt</button><button class="btn" data-open="revoked_edit">Изменить revoked.txt</button></div>
                <div class="small faint" style="margin-top:6px">revoked.txt — для тех, кто пользуется программой без сервера: впиши имя или номер кода, программа у него закроется в течение трёх часов.</div>
              </div>
            </div>
          </div>
        </div>

        <!-- ============ ЖУРНАЛ ============ -->
        <div class="view" id="view-log"><div class="log selectable" id="log"></div></div>
      </div>
    </section>
    <aside class="detail" id="detail" hidden aria-label="Подробности"></aside>
  </div>
</div>

<div class="overlay" id="restartOverlay" hidden><div class="dialog"><div class="db"><div class="dc"><svg class="ring" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.5"/></svg><div><h2 style="margin:0">Устанавливаю обновление</h2><div class="muted">Программа закроется и через несколько секунд откроется уже новой версией.</div></div></div></div></div></div>
<div class="overlay" id="lockOverlay" hidden><div class="dialog">
  <div class="db">
    <h2>Закрытый доступ</h2>
    <div class="muted" id="lockReason"></div>
    <div class="idrow"><span class="muted">ID этого компьютера:</span><b class="num selectable" id="lockMachine">—</b></div>
    <div class="small muted">Отправь владельцу код запроса — кнопка «Копировать код запроса» скопирует его целиком. Владелец пришлёт код доступа — вставь его сюда:</div>
    <textarea class="field code" id="lockCode" placeholder="SZ1-…" style="width:100%;margin-top:10px"></textarea>
  </div>
  <div class="df"><button class="btn" id="lockCopy">Копировать код запроса</button><button class="btn accent" id="lockBtn">Открыть доступ</button></div>
</div></div>
<div class="toast" id="toast" role="status"></div>

<script>
const TOKEN = "__TOKEN__";
const QN = ["обычный","необычный","особый","редкий","исключительный","легендарный"];
const TITLES = {deals:"Находки", items:"Предметы", buys:"Мои покупки", craft:"Крафт в убежище", settings:"Настройки", access:"Доступ", log:"Журнал"};
const FILTER_CATS = ["artefact", "armor", "weapon", "parts", "tools"];
const RANK_RU = {RANK_NEWBIE: "Новичок", RANK_STALKER: "Сталкер", RANK_VETERAN: "Ветеран", RANK_MASTER: "Мастер", RANK_LEGEND: "Легенда"};
const RANK_Q = {RANK_NEWBIE: 1, RANK_STALKER: 2, RANK_VETERAN: 3, RANK_MASTER: 4, RANK_LEGEND: 5};
const RELEASES_URL = "https://github.com/Enotsbeye/stalzone-tracker-releases/releases/latest";
const SOUND_RU = {double: "Двойной сигнал", fanfare: "Фанфары", bell: "Колокольчик", drop: "Капля", sonar: "Сонар", coin: "Монетка", alarm: "Тревога"};
const IC = {
  copy: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="5.5" y="5.5" width="8" height="8" rx="1.2"/><path d="M10.5 5.5V3.7a1.2 1.2 0 0 0-1.2-1.2H3.7a1.2 1.2 0 0 0-1.2 1.2v5.6a1.2 1.2 0 0 0 1.2 1.2h1.8"/></svg>',
  del: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M3 4.5h10M6.2 4.5V3h3.6v1.5M4.5 4.5l.6 9h5.8l.6-9"/></svg>',
  close: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3"><path d="m4 4 8 8M12 4l-8 8"/></svg>',
  play: '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M5 3.5v9l7-4.5z"/></svg>',
  info: '<svg class="ic" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 1 1 0 14A7 7 0 0 1 8 1zm0 6a.75.75 0 0 0-.75.75v3.5a.75.75 0 0 0 1.5 0v-3.5A.75.75 0 0 0 8 7zm0-2.6a.9.9 0 1 0 0 1.8.9.9 0 0 0 0-1.8z"/></svg>',
  err: '<svg class="ic" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 1 1 0 14A7 7 0 0 1 8 1zm0 3.2a.8.8 0 0 0-.8.8v3.6a.8.8 0 0 0 1.6 0V5a.8.8 0 0 0-.8-.8zm0 6.2a.9.9 0 1 0 0 1.8.9.9 0 0 0 0-1.8z"/></svg>',
  ok: '<svg class="ic" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 1 1 0 14A7 7 0 0 1 8 1zm3.1 4.6a.7.7 0 0 0-1 0L7.2 8.5 5.9 7.2a.7.7 0 1 0-1 1l1.8 1.8a.7.7 0 0 0 1 0l3.4-3.4a.7.7 0 0 0 0-1z"/></svg>',
  ring: '<svg class="ring" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.5"/></svg>',
  sortDown: '<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m2 3.5 3 3 3-3"/></svg>',
  sortUp: '<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m2 6.5 3-3 3 3"/></svg>',
};
let S = null, view = "deals", selected = null, detailOpen = false;
let knownIds = new Set(), firstLoad = true, lastErr = 0;
const $ = (id) => document.getElementById(id);
const rubN = (x) => Math.round(x).toLocaleString("ru-RU").replace(/\s/g, "\u00a0");   // неразрывные пробелы: число не переносится
const rub = (x) => rubN(x) + "\u00a0₽";
const signed = (x) => (x >= 0 ? "+" : "−") + rub(Math.abs(x));
const signedN = (x) => (x >= 0 ? "+" : "−") + rubN(Math.abs(x));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const store = { get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
                set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} } };
let CAT = null, CATMAP = {}, CATNAMES = {}, catTab = store.get("catTab", "all"), catLoading = 0;
let F = Object.assign({rare: false, sort: "exp"}, store.get("filters2", {}));
let hideOld = store.get("hideOld2", true);
let bFilter = store.get("bFilter", "open"), sellOpen = null, showBarter = store.get("showBarter", false);
let pPeriod = store.get("pPeriod", "week");
const optPick = {};
// узкое окно (с учётом размера интерфейса): класс w1180 на <html> ставит скрипт в <head>
const narrowMQ = {get matches() { return document.documentElement.classList.contains("w1180"); },
                  addEventListener(_, fn) { window.addEventListener("narrowchange", fn); }};

async function api(path, body) {
  const opt = { headers: { "X-Token": TOKEN } };
  if (body !== undefined) { opt.method = "POST"; opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  const r = await fetch(path, opt);
  return r.json();
}
function toast(msg, err) {
  const t = $("toast"); t.textContent = msg; t.className = "toast on" + (err ? " err" : "");
  clearTimeout(toast.h); toast.h = setTimeout(() => t.className = "toast", err ? 4200 : 2600);
}
function plural(n, forms) {
  const a = Math.abs(n) % 10, b = Math.abs(n) % 100;
  return forms[a === 1 && b !== 11 ? 0 : a >= 2 && a <= 4 && (b < 12 || b > 14) ? 1 : 2];
}
function ago(iso, now) {
  if (!iso) return "—";
  const m = (now - Date.parse(iso) / 1000) / 60;
  if (m < 1) return "только что";
  if (m < 60) return Math.round(m) + " мин назад";
  if (m < 48 * 60) return Math.round(m / 60) + " ч назад";
  return Math.round(m / 1440) + " дн. назад";
}
const agoTs = (ts, now) => ago(new Date(ts * 1000).toISOString(), now);
function fmtWindow(h) { return h < 36 ? Math.round(h) + " ч" : Math.round(h / 24) + " дн."; }
function until(iso) {
  if (!iso) return "—";
  const d = new Date(iso), now = new Date();
  const hm = d.toLocaleTimeString("ru-RU", {hour: "2-digit", minute: "2-digit"});
  return d.toDateString() === now.toDateString() ? hm : d.toLocaleDateString("ru-RU", {day: "2-digit", month: "2-digit"}) + " " + hm;
}
function fmtHours(h) { if (h === null || h === undefined) return ""; if (h < 1) return "меньше часа"; if (h < 48) return "около " + Math.round(h) + " ч"; return "около " + Math.round(h / 24) + " дн."; }
function hoursShort(h) { if (!h) return ""; if (h < 1) return "< 1 ч"; if (h < 48) return "≈ " + Math.round(h) + " ч"; return "≈ " + Math.round(h / 24) + " дн."; }
function n1(x) { return (x >= 10 ? Math.round(x) : Math.round(x * 10) / 10).toLocaleString("ru-RU"); }
function short(v) { return v >= 1e6 ? n1(v / 1e6) + " млн" : v >= 1e4 ? Math.round(v / 1e3) + " тыс." : rubN(v); }

// ---------- ячейка предмета: картинка из базы игры, цвет редкости ----------
function letter(name) { return (String(name || "?").replace(/[«»"'\s]/g, "").charAt(0) || "?").toUpperCase(); }
function slot(id, name, color, size) {
  return `<span class="slot${size ? " " + size : ""}" data-l="${esc(letter(name))}" style="--rc:${color}"><img src="/icon/${encodeURIComponent(id || "")}.png" alt="" loading="lazy" onload="if(this.naturalWidth>4)this.parentNode.classList.add('ok');else this.remove()" onerror="this.remove()"></span>`;
}
function isArtefact(d) { return d.cat === "artefact" || (d.cat == null && d.quality !== null && d.quality !== undefined); }
function tone(d) {
  if (isArtefact(d) && d.quality !== null && d.quality !== undefined) return `var(--q${Math.max(0, Math.min(5, d.quality))})`;
  if (d.rank && RANK_Q[d.rank]) return `var(--q${RANK_Q[d.rank]})`;
  return "var(--q0)";
}
function gradeText(d) {
  if (!isArtefact(d)) return d.ptn ? "+" + d.ptn : "";
  if (d.quality === null || d.quality === undefined) return "";
  return (QN[d.quality] || d.quality) + " " + (d.exact ? "+" + d.ptn : d.ptn >= 15 ? "+15" : "+" + d.ptn + "…" + (d.ptn + 4));
}
function gradeTag(d) { const t = gradeText(d); return t ? `<span class="g" style="--rc:${tone(d)}">${esc(t)}</span>` : ""; }
function rankText(d) { return d.rank && RANK_RU[d.rank] && ["armor", "weapon", "attachment", "backpacks", "containers"].includes(d.cat) ? RANK_RU[d.rank] : ""; }
function rankTag(d) { const t = rankText(d); return t ? `<span class="g" style="--rc:${tone(d)}">${t}</span>` : ""; }

// ---------- звук ----------
let actx = null;
function audioCtx() {
  try { actx = actx || new (window.AudioContext || window.webkitAudioContext)(); if (actx.state === "suspended") actx.resume(); } catch (e) { actx = null; }
  return actx;
}
function note(c, t, f, dur, vol, type, glide) {
  const o = c.createOscillator(), g = c.createGain(), at = c.currentTime + t;
  o.type = type || "sine"; o.frequency.setValueAtTime(f, at);
  if (glide) o.frequency.exponentialRampToValueAtTime(glide, at + dur);
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(Math.max(0.0002, vol), at + 0.012);
  g.gain.exponentialRampToValueAtTime(0.0001, at + dur);
  o.connect(g).connect(c.destination); o.start(at); o.stop(at + dur + 0.05);
}
const SYNTH = {
  double: (c, v) => { note(c, 0, 880, 0.12, 0.2 * v); note(c, 0.13, 1180, 0.14, 0.2 * v); },
  fanfare: (c, v) => [[0, 784], [0.12, 988], [0.24, 1319], [0.42, 1568]].forEach(([t, f]) => note(c, t, f, 0.22, 0.24 * v, "triangle")),
  bell: (c, v) => { note(c, 0, 1318, 1.4, 0.2 * v); note(c, 0, 3638, 0.6, 0.05 * v); note(c, 0, 7117, 0.3, 0.02 * v); },
  drop: (c, v) => { note(c, 0, 1500, 0.18, 0.24 * v, "sine", 520); note(c, 0.17, 900, 0.12, 0.07 * v, "sine", 620); },
  sonar: (c, v) => { note(c, 0, 1046, 0.7, 0.22 * v); note(c, 0.42, 1046, 0.6, 0.07 * v); },
  coin: (c, v) => { note(c, 0, 1175, 0.08, 0.18 * v, "triangle"); note(c, 0.08, 1760, 0.34, 0.18 * v, "triangle"); },
  alarm: (c, v) => [0, 0.16, 0.32].forEach((t) => note(c, t, 1000, 0.1, 0.06 * v, "square")),
};
function playSound(id, vol) {
  if (!(vol > 0)) return;
  const s = String(id || "builtin:double"), i = s.indexOf(":"), kind = s.slice(0, i), name = s.slice(i + 1);
  if (kind === "builtin") { const c = audioCtx(); if (c && SYNTH[name]) SYNTH[name](c, vol); return; }
  try { const a = new Audio(`/sound/${kind}/${encodeURIComponent(name)}?t=${encodeURIComponent(TOKEN)}`); a.volume = Math.min(1, vol); a.play().catch(() => {}); } catch (e) {}
}
function beep(rare) {
  const c = S && S.settings; if (!c || c.sound_on === false) return;
  playSound(rare ? c.sound_rare : c.sound, (c.sound_volume ?? 70) / 100);
}
function notifyDesktop(d) {
  try {
    if ("Notification" in window && Notification.permission === "granted")
      new Notification((d.rare ? "Особо редкий: " : "") + d.name + " — прибыль ~" + rub(d.profit),
        { body: (d.kind === "bid" ? "Ставка, " : "Купить ") + d.amount + " шт за " + rub(d.cost) });
  } catch (e) {}
}

// ---------- умный поиск: опечатки, раскладка, латиница ----------
const KB_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`", KB_RU = "йцукенгшщзхъфывапролджэячсмитьбюё";
const KB = {};
[...KB_EN].forEach((c, i) => { KB[c] = KB_RU[i]; KB[KB_RU[i]] = c; });
const C2L = {а:"a",б:"b",в:"v",г:"g",д:"d",е:"e",ж:"zh",з:"z",и:"i",й:"y",к:"k",л:"l",м:"m",н:"n",о:"o",п:"p",р:"r",с:"s",т:"t",у:"u",ф:"f",х:"h",ц:"c",ч:"ch",ш:"sh",щ:"sch",ъ:"",ы:"y",ь:"",э:"e",ю:"yu",я:"ya"};
function normQ(s) { return String(s || "").toLowerCase().replace(/ё/g, "е").replace(/[«»"'`.,:;!?()\[\]\/\\_+-]+/g, " ").replace(/\s+/g, " ").trim(); }
function toLat(s) { return [...s].map((c) => C2L[c] ?? c).join(""); }
function lev(a, b, lim) {
  if (Math.abs(a.length - b.length) > lim) return lim + 1;
  let prev = Array.from({length: b.length + 1}, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i]; let best = i;
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      best = Math.min(best, cur[j]);
    }
    if (best > lim) return lim + 1;
    prev = cur;
  }
  return prev[b.length];
}
function searchKey(name, extra) {
  const n = normQ(name), l = toLat(n);
  return {n, l, w: n.split(" "), lw: l.split(" "), c: n.replace(/ /g, ""), lc: l.replace(/ /g, ""), x: normQ(extra || "")};
}
function prepQuery(text) {
  const n = normQ(text);
  if (!n) return null;
  const vs = [n], sw = normQ([...n].map((c) => KB[c] || c).join(""));
  if (sw && sw !== n) vs.push(sw);
  return vs.map((v) => ({n: v, w: v.split(" "), l: toLat(v), lw: toLat(v).split(" "), c: v.replace(/ /g, ""), lc: toLat(v).replace(/ /g, "")}));
}
function scoreOne(q, k) {
  let best = 0;
  for (const [qs, ks, qw, kw] of [[q.n, k.n, q.w, k.w], [q.l, k.l, q.lw, k.lw]]) {
    if (!qs) continue;
    if (ks === qs) return 1000;
    if (ks.startsWith(qs)) { best = Math.max(best, 900 - ks.length); continue; }
    if (qw.every((w) => kw.some((x) => x.startsWith(w)))) { best = Math.max(best, 700 - ks.length); continue; }
    if (qw.every((w) => ks.includes(w))) { best = Math.max(best, 500 - ks.length); continue; }
    const qc = qs === q.n ? q.c : q.lc, kc = ks === k.n ? k.c : k.lc;
    if (qc.length >= 3 && kc.startsWith(qc)) { best = Math.max(best, 850 - ks.length); continue; }
    if (qc.length >= 3 && kc.includes(qc)) { best = Math.max(best, 450 - ks.length); continue; }
    let ok = true, cost = 0;
    for (const w of qw) {
      if (kw.some((x) => x.startsWith(w)) || ks.includes(w)) continue;
      if (w.length < 3) { ok = false; break; }
      const lim = w.length >= 7 ? 2 : 1;
      let d = lim + 1;
      for (const x of kw) d = Math.min(d, lev(w, x.slice(0, w.length), lim), lev(w, x, lim));
      if (d > lim) { ok = false; break; }
      cost += d;
    }
    if (ok) best = Math.max(best, 300 - cost * 40 - ks.length);
  }
  if (!best && k.x && q.w.every((w) => k.x.split(" ").some((x) => x.startsWith(w)))) best = 150;
  return best;
}
function matchScore(qv, key) { let b = 0; for (const q of qv) b = Math.max(b, scoreOne(q, key)); return b; }

// ---------- навигация ----------
function go(v) {
  view = v;
  document.querySelectorAll(".nav button").forEach((b) => b.classList.toggle("on", b.dataset.view === v));
  document.querySelectorAll(".view").forEach((s) => s.classList.toggle("on", s.id === "view-" + v));
  $("viewTitle").textContent = TITLES[v];
  $("views").scrollTop = 0;
  detailOpen = false;
  if (v === "items" && CAT) renderCatalog(true);
  if (v === "items") loadYield();
  if (v === "craft") loadCraft();
  if (v === "log" && S) renderLog(true);
  if (v === "settings") loadSounds();
  syncDetail();
}
document.querySelectorAll(".nav button").forEach((b) => b.onclick = () => go(b.dataset.view));
document.querySelectorAll("[data-goto]").forEach((b) => b.onclick = (e) => { e.preventDefault(); go(b.dataset.goto); });
document.querySelectorAll("[data-open]").forEach((b) => b.onclick = (e) => { e.preventDefault(); api("/api/open", {link: b.dataset.open}); });
document.querySelectorAll("[data-opendata]").forEach((b) => b.onclick = () => api("/api/open_data", {}));
$("demoOnBtn").onclick = async () => {
  const r = await api("/api/settings", {demo: true});
  toast(r.ok ? "Демо-режим включён — нажми «Начать поиск»" : r.message, !r.ok);
  refresh();
};
$("demoOffBtn").onclick = () => {
  go("settings");
  const row = $("demoRow");
  row.classList.remove("flash"); void row.offsetWidth; row.classList.add("flash");
  row.scrollIntoView({block: "center"});
};

// ---------- панель справа (находка или рецепт) ----------
function syncDetail() {
  const pane = $("detail"), narrow = narrowMQ.matches;
  let on = false;
  if (view === "deals" && S) on = !!currentDeal() && (!narrow || detailOpen);
  else if (view === "craft") on = crSel !== null && (!narrow || detailOpen);
  pane.hidden = !on;
  pane.classList.toggle("open", on && narrow);
  if (on && view === "deals") renderDealDetail();
  if (on && view === "craft") renderCraftCard();
}
narrowMQ.addEventListener("change", () => syncDetail());
function closeDetail() {
  detailOpen = false;
  if (view === "craft") { crSel = null; renderCraft(); }
  syncDetail();
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("detail").hidden) closeDetail(); });

// ---------- запуск ----------
$("runBtn").onclick = async () => {
  audioCtx();   // звук можно включить только после нажатия — заодно «разбудим» его
  if (S && S.status.running) { await api("/api/stop", {}); toast("Останавливаю поиск…"); refresh(); return; }
  const r = await api("/api/start", {});
  if (!r.ok) { toast(r.message, true); if (!S.configured) go("settings"); else go("items"); }
  else toast("Поиск запущен");
  refresh();
};

// ---------- находки ----------
$("search").oninput = () => renderDeals(true);
$("hideOld").onclick = () => { hideOld = !hideOld; store.set("hideOld2", hideOld); syncFilters(); renderDeals(true); renderNear(true); };
$("clearBtn").onclick = async () => { await api("/api/deals/clear", {}); selected = null; refresh(); };
function saveFilters() { store.set("filters2", F); }
function syncFilters() {
  $("fSort").value = F.sort || "exp";
  $("fRare").classList.toggle("on", !!F.rare); $("fRare").setAttribute("aria-pressed", F.rare ? "true" : "false");
  $("hideOld").classList.toggle("on", hideOld); $("hideOld").setAttribute("aria-pressed", hideOld ? "true" : "false");
  document.querySelectorAll("#dealsHead [data-sort]").forEach((b) => {
    const on = b.dataset.sort === F.sort || (b.dataset.sort === "exp" && F.sort === "profit");
    b.classList.toggle("on", on);
    b.innerHTML = esc(b.textContent) + (on ? (F.sort === "name" || F.sort === "cost" ? IC.sortUp : IC.sortDown) : "");
  });
}
$("fSort").onchange = () => { F.sort = $("fSort").value; saveFilters(); syncFilters(); renderDeals(true); };
$("fRare").onclick = () => { F.rare = !F.rare; saveFilters(); syncFilters(); renderDeals(true); };
document.querySelectorAll("#dealsHead [data-sort]").forEach((b) => b.onclick = () => {
  F.sort = b.dataset.sort === "exp" && F.sort === "exp" ? "profit" : b.dataset.sort;
  saveFilters(); syncFilters(); renderDeals(true);
});
syncFilters();
function chanceCls(c) { return c >= 0.7 ? "hi" : c >= 0.4 ? "mid" : "lo"; }
function chanceWords(c) { return c >= 0.7 ? "Продастся быстро" : c >= 0.4 ? "Может повисеть" : "Продать будет трудно"; }
function fateTag(d) {
  if (d.bought) return `<span class="tag mine">куплено</span>`;
  if (d.fate === "sold") return `<span class="tag" title="Лот пропал, и в истории есть сделка ровно на него">уже купили</span>`;
  if (d.fate === "removed") return `<span class="tag" title="Лот пропал, а сделки по нему в истории нет">снят</span>`;
  if (d.fate === "expired") return `<span class="tag">истёк</span>`;
  if (d.gone) return `<span class="tag" title="Лота больше нет — сверяю с историей сделок, купили его или сняли">пропал</span>`;
  return "";
}
function dealTags(d, now) {
  const fresh = now - d.found < 300 && !d.gone;
  return (d.kind === "bid" ? `<span class="tag bid">ставка</span>` : "")
    + (d.rare ? `<span class="tag rare">особо редкий</span>` : "")
    + (fresh ? `<span class="tag new">новое</span>` : "")
    + (d.only_you_until && d.only_you_until > now && !d.gone ? `<span class="tag me" title="Сервер отдал эту находку сначала тебе — потом её увидят все">только тебе, ещё ${Math.max(1, Math.ceil((d.only_you_until - now) / 60))} мин</span>` : "")
    + fateTag(d)
    + (d.stale && !d.gone ? `<span class="tag stale" title="${esc(d.stale)}">давно висит</span>` : "");
}
function isOld(d, now) { return !d.bought && (d.gone || (d.ends && Date.parse(d.ends) / 1000 <= now)); }
function visibleDeals() {
  const qv = prepQuery($("search").value), now = S.now;
  let list = S.deals.filter((d) => (!qv || matchScore(qv, d._k || (d._k = searchKey(d.name, (CATNAMES[d.cat] || "") + " " + (RANK_RU[d.rank] || "")))) > 0)
    && (!F.rare || d.rare) && (!hideOld || d.bought || !isOld(d, now)));
  const key = F.sort || "exp";
  const val = (d) => key === "listed" ? Date.parse(d.listed || 0) : key === "chance" ? (d.chance == null ? -1 : d.chance)
    : key === "exp" ? (d.exp_profit == null ? d.profit * 0.3 : d.exp_profit) : key === "cost" ? -d.cost : key === "name" ? d.name : d[key];
  list.sort((a, b) => { const x = val(a), y = val(b); return key === "name" ? String(x).localeCompare(y, "ru") : (y - x); });
  return list;
}
function currentDeal() {
  if (!S) return null;
  const list = visibleDeals();
  let d = list.find((x) => x.id === selected);
  if (!d && selected !== null) d = S.deals.find((x) => x.id === selected);
  if (!d && !narrowMQ.matches) d = list[0] || null;
  return d || null;
}
function dealRow(d, now, sel) {
  const bid = d.kind === "bid", many = d.amount > 1, c = d.chance;
  const when = bid ? "торги до " + until(d.ends) : ago(d.listed, now);
  const meta = gradeTag(d) + rankTag(d) + dealTags(d, now) + (many || bid ? `<span>${when}</span>` : "");
  const pct = c == null ? null : Math.round(c * 100);
  return `<div class="tr${sel ? " sel" : ""}${isOld(d, now) ? " old" : ""}${d.bought ? " mine" : ""}" data-id="${d.id}" role="option" aria-selected="${sel}">
    <div class="it">${slot(d.item_id, d.name, tone(d))}<div class="t"><div class="n" title="${esc(d.name)}">${esc(d.name)}</div><div class="m">${meta}</div></div></div>
    <div class="r num"><div class="v">${rub(d.cost)}</div><div class="s" title="${bid ? "" : "Выставлен " + when}">${many ? `${d.amount} шт по ${rubN(d.unit)}` : bid ? "" : when}</div></div>
    <div class="r num"><div class="v">${rub(d.resale)}</div>${many ? `<div class="s">по ${rubN(d.market)}</div>` : ""}</div>
    <div class="ch ${c == null ? "" : chanceCls(c)} num" title="${c == null ? "Шанс не посчитан" : chanceWords(c) + ": шанс продать за сутки " + pct + "%" + (d.sell_hours ? ", обычно " + fmtHours(d.sell_hours) : "")}">${c == null
      ? `<div class="v faint">—</div>` : `<div class="v">${pct}%<small>${hoursShort(d.sell_hours)}</small></div><i class="bar"><b style="width:${pct}%"></b></i>`}</div>
    <div class="r num"><div class="p">+${rub(d.profit)}</div>${d.exp_profit != null ? `<div class="s" title="Прибыль × шанс продать за сутки">с шансом +${rubN(d.exp_profit)}</div>` : ""}</div>
    <button class="ib" data-copy="${d.id}" title="Скопировать название — вставь в поиск аукциона в игре">${IC.copy}</button>
  </div>`;
}
let lastDealsSig = "";
function renderDeals(force) {
  if (!S) return;
  const list = visibleDeals(), now = S.now, cur = currentDeal(), selId = cur ? cur.id : null;
  const sig = JSON.stringify([list.map((d) => [d.id, d.gone, d.fate, d.bought, d.chance, d.profit, d.stale ? 1 : 0, d.only_you_until ? 1 : 0]), selId, Math.floor(now / 30)]);
  if (force || sig !== lastDealsSig) {
    lastDealsSig = sig;
    const rows = $("rows");
    rows.innerHTML = list.map((d) => dealRow(d, now, d.id === selId)).join("");
    rows.querySelectorAll(".tr").forEach((el) => el.onclick = (e) => {
      if (e.target.closest("[data-copy]")) return;
      selected = +el.dataset.id; detailOpen = true; renderDeals(true); syncDetail(); rows.focus({preventScroll: true});
    });
    rows.querySelectorAll("[data-copy]").forEach((b) => b.onclick = () => {
      const d = S.deals.find((x) => x.id === +b.dataset.copy); if (d) copyText(d.name);
    });
  }
  const empty = list.length === 0;
  $("empty").hidden = !empty;
  $("rows").tabIndex = empty ? -1 : 0;
  if (empty) {
    const nearN = (S.near || []).filter((r) => !r.gone).length;
    let h, t, ring = false;
    if (S.status.running && !S.deals.length && nearN) { h = "По твоим порогам — пока ничего"; t = "Ниже лоты дешевле рынка, которые отсеяли пороги. Если их много, а находок нет, попробуй снизить «Минимальную прибыль»."; }
    else if (S.status.running && !S.deals.length) { h = "Ищу выгодные лоты…"; t = "Как только что-то найдётся — появится здесь, со звуком. Окно можно свернуть."; ring = true; }
    else if (S.deals.length) { h = "Под фильтры ничего не подходит"; t = "Очисти поиск или нажми «Скрыть ушедшие», чтобы увидеть и их."; }
    else { h = "Пока ничего не найдено"; t = "Нажми «Начать поиск» — трекер начнёт проверять аукцион."; }
    $("emptyH").textContent = h; $("emptyT").textContent = t; $("emptyRing").hidden = !ring;
  }
}
$("rows").addEventListener("keydown", (e) => {
  if (!S || !["ArrowDown", "ArrowUp", "Home", "End", "Enter"].includes(e.key)) return;
  const list = visibleDeals(); if (!list.length) return;
  e.preventDefault();
  const cur = currentDeal(), i = Math.max(0, list.findIndex((d) => cur && d.id === cur.id));
  if (e.key === "Enter") { detailOpen = true; syncDetail(); return; }
  const j = e.key === "Home" ? 0 : e.key === "End" ? list.length - 1 : Math.min(list.length - 1, Math.max(0, i + (e.key === "ArrowDown" ? 1 : -1)));
  selected = list[j].id; renderDeals(true); syncDetail();
  const el = $("rows").querySelector(`.tr[data-id="${selected}"]`); if (el) el.scrollIntoView({block: "nearest"});
});
document.addEventListener("keydown", (e) => {   // Ctrl+C — название выбранной находки (если текст не выделен)
  if (!(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== "c" && e.code !== "KeyC") return;
  if (view !== "deals" || /INPUT|TEXTAREA/.test((document.activeElement || {}).tagName || "") || String(getSelection())) return;
  const d = currentDeal(); if (d) { e.preventDefault(); copyText(d.name); }
});

// ---------- итог над таблицей ----------
function renderLead() {
  const st = S.status, run = st.running, now = S.now;
  const active = S.deals.filter((d) => !d.gone && (!d.ends || Date.parse(d.ends) / 1000 > now));
  const total = active.reduce((s, d) => s + d.profit, 0);
  const exp = active.reduce((s, d) => s + (d.exp_profit == null ? 0 : d.exp_profit), 0);
  const hasExp = active.some((d) => d.exp_profit != null);
  $("sumN").textContent = active.length; $("sumNl").textContent = plural(active.length, ["находка", "находки", "находок"]);
  $("sumAll").textContent = "+" + rub(total); $("sumAllBox").hidden = !active.length;
  $("sumExp").textContent = "≈ +" + rub(exp); $("sumExpBox").hidden = !active.length || !hasExp;
  const subscriber = S.server && S.server.role === "subscriber", sv = st.server;
  const items = st.total || (st.progress && st.progress.total) || watchTotal();
  let sub;
  if (subscriber) sub = !sv ? "Находки придут с сервера владельца после «Начать поиск»." : sv.ok ? `Сервер владельца на связи${sv.server_pass ? ", его последняя проверка " + agoTs(sv.server_pass, now) : ""}.` : (sv.error || "Сервер владельца не отвечает.");
  else if (run) {
    sub = `Проверяю ${items} ${plural(items, ["предмет", "предмета", "предметов"])} по кругу${st.took ? `, круг около ${Math.max(1, Math.round(st.took))} с` : ""}.`;
    if (st.delay !== null && st.delay !== undefined) sub += ` Новые лоты попадают в API примерно через ${Math.max(1, Math.round(st.delay))} мин после выставления — так у всех, кто смотрит через API.`;
    const kl = keyLoad();
    if (kl) sub += ` Твоим ключом API пользуется ещё кто-то (~${kl.others} запр./мин) — поиск медленнее, подробнее во вкладке «Доступ».`;
  } else sub = active.length ? "Это находки с прошлого поиска. Нажми «Начать поиск», чтобы искать дальше." : "Нажми «Начать поиск» — трекер будет проверять аукцион без остановки и покажет здесь лоты дешевле рынка.";
  $("sumS").textContent = sub;
  $("cntDeals").textContent = active.length || "";
}

// ---------- «почти находки» ----------
function nearPct(r) { const base = Math.min(r.hist || 0, r.market || 0); return base > 0 ? (1 - r.unit / base) * 100 : 0; }
function nearWhy(r) {
  const out = (r.why || []).map((w) => w.what === "profit" ? `прибыль меньше твоего порога ${rub(w.need)}`
    : w.what === "expected" ? `прибыль с учётом шанса меньше ${rub(w.need)}`
    : `дешевле рынка только на ${Math.floor(nearPct(r))}%, а нужно от ${Math.round(w.need)}%`);
  return out.join("; ") || "не прошла пороги";
}
let lastNearSig = "";
function renderNear(force) {
  const list = (S.near || []).filter((r) => !r.gone || !hideOld);
  $("nearBox").hidden = !list.length;
  $("nearTitle").textContent = `Почти находки: ${list.length}`;
  const sig = JSON.stringify([list.map((r) => [r.key, r.gone, r.fate, r.profit, (r.why || []).length]), Math.floor(S.now / 30)]);
  if (!force && sig === lastNearSig) return;
  lastNearSig = sig;
  $("nearRows").innerHTML = list.map((r, i) => `<div class="nr${r.gone ? " old" : ""}">
    <div class="it">${slot(r.item_id, r.name, tone(r), "sm")}<div class="t"><div class="n">${esc(r.name)} ${gradeTag(r)}${rankTag(r)}</div><div class="why">${esc(nearWhy(r))}${r.gone ? (r.fate === "sold" ? ", уже купили" : ", лот снят") : ""}</div></div></div>
    <div class="r num"><div class="v">${rub(r.cost)}</div><div class="s">${r.amount > 1 ? r.amount + " шт" : ago(r.listed, S.now)}</div></div>
    <div class="r num"><div class="v">${rub(r.resale)}</div><div class="s">−${Math.floor(nearPct(r))}% к рынку</div></div>
    <div class="r num"><div class="p">+${rub(r.profit)}</div></div>
    <button class="ib" data-ncopy="${i}" title="Скопировать название">${IC.copy}</button>
  </div>`).join("");
  $("nearRows").querySelectorAll("[data-ncopy]").forEach((b) => b.onclick = () => { const r = list[+b.dataset.ncopy]; if (r) copyText(r.name); });
}
$("nearBox").ontoggle = () => store.set("nearOpen", $("nearBox").open);
$("nearBox").open = store.get("nearOpen", false);

// ---------- карточка находки ----------
function chanceBlock(c) {
  if (!c) return `<div class="sec"><h3>Шанс продать за сутки</h3><div class="muted">Мало сделок, чтобы оценить.</div></div>`;
  const p = Math.round(c.chance * 100), cls = chanceCls(c.chance);
  const why = [];
  if (c.data && c.data.hours > 0) {
    const life = c.data.per_hour > 0 ? 1 / c.data.per_hour : null;
    why.push([`Похожие лоты на твоём рынке уходят в среднем за ${life ? fmtHours(life).replace("около ", "") : "долгое время"} — по ${c.data.sold} ${plural(c.data.sold, ["продаже", "продажам", "продажам"])} за ${Math.round(c.data.hours)} ч наблюдений`, life && life < 12 ? "up" : "down"]);
  }
  why.push([`Этот предмет покупают примерно ${n1(c.per_day)} раз в сутки`, c.per_day >= 10 ? "up" : c.per_day < 2 ? "down" : ""]);
  why.push([c.comp ? `Рядом по цене ещё ${c.comp} ${plural(c.comp, ["продавец", "продавца", "продавцов"])}` : "Ты будешь самым дешёвым продавцом", c.comp ? "down" : "up"]);
  if (c.need > 1) why.push([`Чтобы продать весь лот, понадобится около ${c.need} ${plural(c.need, ["покупателя", "покупателей", "покупателей"])} (обычно берут по ${Math.round(c.size)} шт)`, "down"]);
  if (c.trend_f < 1) why.push(["Цена за сутки падает", "down"]); else if (c.trend_f > 1) why.push(["Цена за сутки растёт", "up"]);
  if (c.stale_f < 1) why.push(["Лот давно висит со скидкой, а его не берут — возможно, есть подвох", "down"]);
  if (c.supply_days !== null && c.supply_days !== undefined && c.supply_days >= 3) why.push([`На аукционе похожих лотов примерно на ${n1(c.supply_days)} дн. продаж`, "down"]);
  return `<div class="sec"><h3>Шанс продать за сутки</h3>
    <div class="big num ${cls}"><b class="${cls === "hi" ? "good" : cls === "mid" ? "warn" : "bad"}">${p}%</b><span>${chanceWords(c.chance).toLowerCase()}${c.hours != null ? ", обычно " + fmtHours(c.hours) : ""}</span></div>
    <i class="bar ${cls}" style="height:6px;border-radius:3px"><b style="width:${p}%"></b></i>
    <ul class="reasons">${why.map(([t, k]) => `<li class="${k}">${esc(t)}</li>`).join("")}</ul>
    <div class="kv num" style="margin-top:12px">
      <span>Сделок в сутки</span><b>${n1(c.per_day)}</b>
      <span>Платили не меньше этой цены</span><b>${Math.round(c.share * 100)}%</b>
      ${c.data ? `<span>По наблюдениям трекера</span><b>${Math.round(c.data.p * 100)}%, вес ${Math.round(c.data.weight * 100)}%</b>` : `<span>Свои наблюдения</span><b>пока копятся</b>`}
      <span>По формуле</span><b>${Math.round((c.model || 0) * 100)}%</b>
      ${c.week !== undefined ? `<span>Шанс за неделю</span><b>${Math.round(c.week * 100)}%</b>` : ""}
    </div>
    <div class="small faint" style="margin-top:8px">Это оценка, а не гарантия: API не показывает, сколько людей хотят купить. Чем дольше трекер работает, тем больше она опирается на то, как лоты продаются на самом деле.</div>
  </div>`;
}
function priceChart(series, d, sell, buy) {
  const pts = (series || []).filter((x) => x.p > 0);
  if (pts.length < 2) return `<div class="muted">Мало сделок для графика — трекер ещё копит историю.</div>`;
  const W = 300, H = 120, T = 16, B = 18;
  const xs = pts.map((x) => x.t), vals = pts.map((x) => x.p).concat([sell, buy].filter((v) => v > 0));
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const pad = (hi - lo) * 0.15 || hi * 0.05, y0 = lo - pad, y1 = hi + pad;
  const X = (t) => (t - xs[0]) / Math.max(1, xs[xs.length - 1] - xs[0]) * W;
  const Y = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
  const line = pts.map((x, i) => (i ? "L" : "M") + X(x.t).toFixed(1) + " " + Y(x.p).toFixed(1)).join(" ");
  const area = line + ` L${X(xs[xs.length - 1]).toFixed(1)} ${H - B} L0 ${H - B} Z`;
  const lvl = (v, color, label, above) => v > 0 ? `<line x1="0" x2="${W}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}" stroke="${color}" stroke-width="1" stroke-dasharray="4 4"/><text x="${W}" y="${(Y(v) + (above ? -5 : 13)).toFixed(1)}" text-anchor="end" font-size="11" fill="${color}">${label} ${short(v)}</text>` : "";
  const day = (t) => new Date(t * 1000).toLocaleDateString("ru-RU", {day: "2-digit", month: "2-digit"});
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Цена за неделю">
    <path d="${area}" fill="var(--hover)"/><path d="${line}" fill="none" stroke="var(--text-2)" stroke-width="1.5" stroke-linejoin="round"/>
    ${lvl(sell, "var(--accent-t)", "продать", sell >= buy)}${lvl(buy, "var(--good)", "купить", buy > sell)}
    <text x="0" y="${H - 3}" fill="var(--text-3)" font-size="11">${day(xs[0])}</text><text x="${W}" y="${H - 3}" fill="var(--text-3)" font-size="11" text-anchor="end">сейчас</text>
  </svg><div class="cap">Медиана сделок за штуку${d && isArtefact(d) ? " — того же качества и заточки" : ""}, по 12 часов</div>`;
}
function hoursChart(hours) {
  const total = (hours || []).reduce((a, b) => a + b, 0);
  if (total < 12) return "";
  const W = 300, H = 64, B = 16, max = Math.max(...hours), bw = W / 24;
  let best = 0, at = 0;
  for (let h = 0; h < 24; h++) { const s = hours[h] + hours[(h + 1) % 24] + hours[(h + 2) % 24]; if (s > best) { best = s; at = h; } }
  const hot = new Set([at, (at + 1) % 24, (at + 2) % 24]);
  const bars = hours.map((v, h) => { const bh = Math.max(2, v / max * (H - B - 4)); return `<rect x="${(h * bw + 1.5).toFixed(1)}" y="${(H - B - bh).toFixed(1)}" width="${(bw - 3).toFixed(1)}" height="${bh.toFixed(1)}" rx="1.5" fill="${hot.has(h) ? "var(--accent)" : "var(--divider)"}"/>`; }).join("");
  const ticks = [0, 6, 12, 18].map((h) => `<text x="${(h * bw + bw / 2).toFixed(1)}" y="${H - 3}" fill="var(--text-3)" font-size="11" text-anchor="middle">${h}</text>`).join("");
  return `<h3>Когда покупают</h3><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Сделки по часам суток">${bars}${ticks}</svg>
    <div class="cap">Чаще всего — с ${at} до ${(at + 3) % 24} ч (по часам этого компьютера, сделки за 2 недели). Выставляй лот перед этим.</div>`;
}
const statsCache = {};
async function loadItemStats(key, itemId, q, onDone) {
  const hit = statsCache[key];
  if (hit && Date.now() - hit.at < 120000) { onDone(hit.r); return; }
  try { const r = await api(`/api/item_stats?id=${encodeURIComponent(itemId)}${q || ""}`); statsCache[key] = {at: Date.now(), r}; onDone(r); } catch (e) { onDone(null); }
}
function rareMarks() { return (S.settings.rare_items || []).map((x) => String(x).toLowerCase().replace(/ё/g, "е")); }
function isStarred(id, name) { const m = rareMarks(); return m.includes(String(id).toLowerCase()) || (name && m.includes(name.toLowerCase().replace(/ё/g, "е").replace(/[«»]/g, ""))); }
async function toggleStar(id, name) {
  let list = (S.settings.rare_items || []).slice();
  const marks = rareMarks(), on = isStarred(id, name);
  if (on) list = list.filter((x, i) => marks[i] !== String(id).toLowerCase() && marks[i] !== (name || "").toLowerCase().replace(/ё/g, "е").replace(/[«»]/g, ""));
  else list.push(id || name);
  const r = await api("/api/settings", {rare_items: list});
  toast(r.ok ? (on ? "Больше не особо редкий: " : "Особо редкий: ") + (name || id) : r.message, !r.ok);
  await refresh();
}
let lastDetailSig = "";
function renderDealDetail(force) {
  const d = currentDeal(), pane = $("detail");
  if (!d) return;
  if (pane.contains(document.activeElement) && document.activeElement.tagName === "INPUT") return;   // не мешаем вписывать цену
  const sig = JSON.stringify([d.id, d.gone, d.fate, d.bought, d.chance, d.profit, d.stale, isStarred(d.item_id, d.name), narrowMQ.matches, Math.floor(S.now / 60)]);
  if (!force && sig === lastDetailSig) return;
  lastDetailSig = sig;
  const bid = d.kind === "bid", star = isStarred(d.item_id, d.name);
  const sub = [gradeText(d), rankText(d), d.cat && CATNAMES[d.cat] ? CATNAMES[d.cat] : "", d.amount > 1 ? d.amount + " шт" : ""].filter(Boolean).join(", ");
  pane.innerHTML = `
    <button class="ib x" id="dClose" title="Закрыть">${IC.close}</button>
    <div class="dh">${slot(d.item_id, d.name, tone(d), "lg")}<div style="min-width:0">
      <h2>${esc(d.name)}</h2><div class="g" style="--rc:${tone(d)}">${esc(sub)}</div>
      <div class="tags">${dealTags(d, S.now)}</div></div></div>
    <div class="hero num">+${rub(d.profit)}</div>
    <div class="hero-s">возможная прибыль, ${Math.round(d.roi)}% к вложенному, дешевле рынка на ${Math.round(d.pct)}%</div>
    <div class="kv num">
      <span>${bid ? (d.has_bids ? "Текущая ставка" : "Стартовая цена") : "Купить"}${d.amount > 1 ? `<small>${d.amount} шт по ${rub(d.unit)}</small>` : ""}</span><b>${rub(d.cost)}</b>
      <span>Продать примерно за${d.amount > 1 ? `<small>по ${rub(d.market)} за шт</small>` : ""}</span><b>${rub(d.resale)}</b>
      <span>Комиссия аукциона 5%</span><b>−${rub(d.resale * 0.05)}</b>
      <span>Прибыль</span><b class="good">+${rub(d.profit)}</b>
    </div>
    ${d.bought ? `<div class="note ok">Отмечено как купленное — цена и подсказка, за сколько выставить, теперь в «Моих покупках».</div>`
      : `<div class="buy"><span class="unit"><input class="field num" id="dPaid" value="${rubN(d.cost)}" title="Сколько заплатил за весь лот"><i>₽</i></span><button class="btn accent" id="dBuy">Я купил</button></div>
         <div class="small faint" style="margin-top:6px">Впиши, сколько реально заплатил, — трекер будет следить за ценой и подскажет, за сколько выставить.</div>`}
    <div class="actions"><button class="btn wide" id="dCopy">${IC.copy}Скопировать название</button></div>
    ${d.fate === "sold" ? `<div class="note warn">Этот лот уже купили — в истории есть сделка ровно на него.</div>`
      : d.gone && !d.bought ? `<div class="note warn">Этого лота больше нет на аукционе${d.fate === "removed" ? " — его сняли" : d.fate === "expired" ? " — время вышло" : " — сверяю с историей сделок, купили его или сняли"}.</div>` : ""}
    ${d.stale && !d.gone ? `<div class="note warn">${esc(d.stale)}</div>` : ""}
    ${bid ? `<div class="note">Ставь не выше <b>${rub(d.max_bid)}</b> за весь лот — тогда прибыль будет не меньше минимальной из настроек.</div>` : ""}
    ${chanceBlock(d.chance_info)}
    <div class="sec chart" id="dChart"><h3>Цена за неделю</h3><div class="muted">Загружаю…</div></div>
    <div class="sec chart" id="dHours"></div>
    <div class="facts">
      <div class="fact"><div class="l">Цена по сделкам${d.window_h ? " за " + fmtWindow(d.window_h) : ""}</div><div class="v num">${rub(d.hist)}/шт</div></div>
      <div class="fact"><div class="l">${d.exact ? "Такой же или лучше" : "Дешевле всего"} на аукционе</div><div class="v num">${d.floor ? rub(d.floor) + "/шт" : "нет"}</div></div>
      <div class="fact"><div class="l">Выставлен</div><div class="v">${ago(d.listed, S.now)}</div></div>
      <div class="fact"><div class="l">Активен до</div><div class="v">${until(d.ends)}</div></div>
      <div class="fact"><div class="l">Сделок в расчёте</div><div class="v num">${d.n_sales}</div></div>
      <div class="fact"><div class="l">Цена за сутки</div><div class="v num ${d.trend == null ? "" : d.trend <= -5 ? "bad" : d.trend >= 5 ? "good" : ""}">${d.trend == null ? "мало данных" : (d.trend > 0 ? "+" : d.trend < 0 ? "−" : "") + Math.abs(Math.round(d.trend)) + "%"}</div></div>
    </div>
    <div class="note">${d.floor && d.floor * 0.99 < d.hist
      ? "Перепродать дороже самого дешёвого такого же лота не выйдет, поэтому цена продажи — чуть ниже него, а не по прошлым сделкам."
      : d.floor ? "Цена продажи — по прошлым сделкам: такие же лоты на аукционе сейчас дороже."
      : "Такого же или лучше лота на аукционе сейчас нет — цена продажи только по прошлым сделкам, это менее надёжно."} Данные API запаздывают — проверь лот в игре перед покупкой.</div>
    ${isArtefact(d) ? `<div class="note">Артефакт: цена зависит ещё от процента качества и доп. свойств — сравни лот в игре с другими того же качества и заточки.</div>` : ""}
    ${["armor", "weapon"].includes(d.cat) ? `<div class="note">Цена брони и оружия сильно зависит от заточки и состояния — сравни лот в игре с такими же.</div>` : ""}
    <div class="actions"><button class="btn" id="dStar">${star ? "Убрать из особо редких" : "Отметить особо редким"}</button><button class="btn subtle" id="dHide">Скрыть находку</button></div>`;
  $("dClose").onclick = closeDetail;
  $("dCopy").onclick = () => copyText(d.name);
  $("dStar").onclick = async () => { await toggleStar(d.item_id, d.name); renderDealDetail(true); };
  $("dHide").onclick = async () => { await api("/api/deals/remove", {id: d.id}); if (selected === d.id) selected = null; refresh(); };
  if ($("dBuy")) $("dBuy").onclick = async () => {
    const r = await api("/api/purchases/add", {deal_id: d.id, paid: $("dPaid").value.replace(/\s/g, "").replace(",", ".")});
    toast(r.message, !r.ok); await refresh(); renderDealDetail(true);
  };
  if ($("dPaid")) $("dPaid").onkeydown = (e) => { if (e.key === "Enter") $("dBuy").click(); };
  const q = isArtefact(d) && d.quality !== null && d.quality !== undefined ? `&q=${d.quality}&p=${d.ptn ?? 0}` : "";
  loadItemStats(d.item_id + q, d.item_id, q, (r) => {
    if (!$("dChart") || currentDeal() !== d && (currentDeal() || {}).id !== d.id) return;
    $("dChart").innerHTML = "<h3>Цена за неделю</h3>" + (r ? priceChart(r.series, d, d.market, d.unit) : "");
    $("dHours").innerHTML = r ? hoursChart(r.hours) : "";
  });
}
function copyText(t, msg) {
  const done = () => toast(msg || "Скопировано: " + t + " — вставь в поиск аукциона в игре");
  if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(t).then(done, fallback); else fallback();
  function fallback() { const a = document.createElement("textarea"); a.value = t; document.body.appendChild(a); a.select(); try { document.execCommand("copy"); done(); } catch (e) {} a.remove(); }
}

// ---------- предметы ----------
function watch() { return S ? S.settings.watch.slice() : []; }
async function saveWatch(list, msg, warn) { const r = await api("/api/settings", {watch: list}); toast(r.ok ? (msg || "Список обновлён") : r.message, !r.ok || !!warn); await refresh(); }
const normName = (n) => String(n || "").toLowerCase().replace(/ё/g, "е").replace(/[«»]/g, "").trim();
function entryName(w) { return CATMAP[w] ? CATMAP[w].name : w; }
function inWatch(e) { return watch().some((w) => w === e.id || normName(w) === normName(e.name)); }
function addEntry(e) {
  const list = watch();
  if (inWatch(e)) { toast("Уже в списке"); return; }
  const dup = CAT && CAT.filter((x) => normName(x.name) === normName(e.name)).length > 1;   // одинаковые названия — храним id
  list.push(dup ? e.id : e.name);
  saveWatch(list, "Добавлено: " + e.name);
}
function removeEntry(e) { saveWatch(watch().filter((w) => w !== e.id && normName(w) !== normName(e.name)), "Убрано: " + e.name); }
function autoCount() { return (S.auto_cats || []).reduce((s, c) => s + (S.cat_counts[c] || (c === "artefact" ? S.artifacts : 0) || 0), 0); }
function watchTotal() { return watch().length + (S ? autoCount() : 0); }
function entryTone(e) { return e.rank && RANK_Q[e.rank] && e.cat !== "artefact" ? `var(--q${RANK_Q[e.rank]})` : "var(--q0)"; }
async function loadCatalog() {
  if (CAT || Date.now() - catLoading < 4000) return;
  catLoading = Date.now();
  try {
    const r = await api("/api/catalog");
    if (r.items && r.items.length) {
      CAT = r.items; CATNAMES = r.names || {}; CATMAP = {};
      CAT.forEach((e) => { CATMAP[e.id] = e; e._k = searchKey(e.name, (CATNAMES[e.cat] || "") + " " + (RANK_RU[e.rank] || "") + (e.barter ? " бартер" : "")); });
      renderCatalog(true); renderChips(true);
    }
  } catch (e) {}
}
function renderTabs() {
  const counts = {}, visible = (CAT || []).filter((e) => e.trade && (showBarter || !e.barter));
  visible.forEach((e) => counts[e.cat] = (counts[e.cat] || 0) + 1);
  const order = ["all", "artefact", "armor", "weapon", "parts", "tools", "attachment", "misc", "supply", "bullet", "containers", "backpacks", "grenade", "other"];
  $("catTabs").innerHTML = order.filter((c) => c === "all" || counts[c]).map((c) =>
    `<button data-c="${c}" class="${c === catTab ? "on" : ""}">${c === "all" ? "Все" : esc(CATNAMES[c] || c)}<span>${c === "all" ? visible.length : counts[c]}</span></button>`).join("")
    + `<button id="barterBtn" class="${showBarter ? "on" : ""}" title="Предметы, которые получают бартером у торговцев">${showBarter ? "Бартерные показаны" : "+ бартерные"}</button>`;
  $("barterBtn").onclick = () => { showBarter = !showBarter; store.set("showBarter", showBarter); renderCatalog(true); };
  $("catTabs").querySelectorAll("button[data-c]").forEach((b) => b.onclick = () => { catTab = b.dataset.c; store.set("catTab", catTab); renderCatalog(); $("catResults").scrollTop = 0; });
}
let lastCatSig = "";
function renderCatalog(force) {
  if (!CAT) return;
  const sig = [catTab, showBarter, $("catSearch").value, watch().join("|"), (S.settings.rare_items || []).join("|")].join("#");
  if (!force && sig === lastCatSig) return;
  lastCatSig = sig;
  renderTabs();
  const qv = prepQuery($("catSearch").value);
  let list = CAT.filter((e) => e.trade && (showBarter || !e.barter) && (catTab === "all" || e.cat === catTab));
  if (qv) list = list.map((e) => [matchScore(qv, e._k), e]).filter((x) => x[0] > 0).sort((a, b) => b[0] - a[0] || a[1].name.localeCompare(b[1].name, "ru")).map((x) => x[1]);
  else list.sort((a, b) => a.name.localeCompare(b.name, "ru"));
  const shown = list.slice(0, 120);
  $("catResults").innerHTML = shown.map((e) => {
    const on = inWatch(e), star = isStarred(e.id, e.name);
    return `<div class="res">${slot(e.id, e.name, entryTone(e), "sm")}
      <span class="n">${esc(e.name)}</span>${e.rank && RANK_RU[e.rank] && e.cat !== "artefact" ? `<span class="g" style="--rc:${entryTone(e)}">${RANK_RU[e.rank]}</span>` : ""}
      ${e.barter ? `<span class="tag" title="Получают бартером у торговцев">бартер</span>` : ""}<span class="tag">${esc(CATNAMES[e.cat] || e.cat)}</span>
      <button class="star${star ? " on" : ""}" data-star="${e.id}" title="Особо редкий — отдельное уведомление">${star ? "★" : "☆"}</button>
      <button class="btn sm${on ? " subtle" : ""}" data-add="${e.id}" style="min-width:104px" title="${on ? "Убрать из списка" : "Добавить в список"}">${on ? "✓ В списке" : "Следить"}</button></div>`;
  }).join("") || `<div class="res faint">Ничего не нашёл — попробуй часть названия или другую вкладку.</div>`;
  $("catMore").textContent = list.length > shown.length ? `Показано ${shown.length} из ${list.length} — уточни поиск.` : (list.length ? `Найдено: ${list.length}` : "");
  $("catResults").querySelectorAll("[data-add]").forEach((b) => b.onclick = () => { const e = CATMAP[b.dataset.add]; inWatch(e) ? removeEntry(e) : addEntry(e); });
  $("catResults").querySelectorAll("[data-star]").forEach((b) => b.onclick = async () => { const e = CATMAP[b.dataset.star]; await toggleStar(e.id, e.name); renderCatalog(true); });
}
$("catSearch").oninput = () => { clearTimeout(renderCatalog.t); renderCatalog.t = setTimeout(() => renderCatalog(), 90); };
$("catSearch").onkeydown = (e) => {
  if (e.key !== "Enter" || !CAT) return;
  const qv = prepQuery($("catSearch").value); if (!qv) return;
  let best = null, score = 0;   // Enter — добавить лучшее совпадение
  CAT.forEach((x) => { if (!x.trade) return; const sc = matchScore(qv, x._k); if (sc > score) { score = sc; best = x; } });
  if (best) addEntry(best); else toast("Не нашёл такого предмета", true);
};
let lastChipsSig = "";
function renderChips(force) {
  const list = watch(), cats = S.auto_cats || [];
  const sig = JSON.stringify([list, S.settings.rare_items || [], !!CAT]);
  if (force || sig !== lastChipsSig) {
    lastChipsSig = sig;
    $("chips").innerHTML = list.map((w, i) => {
      const e = CATMAP[w] || (CAT || []).find((x) => normName(x.name) === normName(w));
      const name = e ? e.name : w, star = isStarred(e ? e.id : w, name);
      return `<div class="lrow">${e ? slot(e.id, name, entryTone(e), "sm") : `<span class="slot sm" data-l="${esc(letter(name))}" style="--rc:var(--q0)"></span>`}<span class="n">${esc(name)}${e && e.cat !== "artefact" && CATNAMES[e.cat] ? ` <span class="faint small">${esc(CATNAMES[e.cat])}</span>` : ""}${e ? "" : ` <span class="tag bad" title="Такого названия нет в базе игры">не найден</span>`}</span>
        <button class="star${star ? " on" : ""}" data-s="${i}" title="Особо редкий">${star ? "★" : "☆"}</button><button class="ib" title="Убрать из списка" data-i="${i}">${IC.close}</button></div>`;
    }).join("");
    $("chips").querySelectorAll("[data-i]").forEach((b) => b.onclick = () => { const l = watch(); l.splice(+b.dataset.i, 1); saveWatch(l, "Убрано"); });
    $("chips").querySelectorAll("[data-s]").forEach((b) => b.onclick = () => {
      const w = watch()[+b.dataset.s], e = CATMAP[w] || (CAT || []).find((x) => normName(x.name) === normName(w));
      toggleStar(e ? e.id : w, e ? e.name : w);
    });
  }
  $("chipsEmpty").hidden = !!list.length;
  $("chipsEmpty").textContent = cats.length === 1 && cats[0] === "artefact" ? "Свой список пуст — проверяются только все артефакты."
    : cats.length ? "Свой список пуст — проверяются только категории целиком." : "Список пуст. Найди предмет слева и нажми «Следить».";
  $("watchCnt").textContent = list.length ? list.length : "";
  $("cntItems").textContent = watchTotal() || "";
  document.querySelectorAll("[data-cat]").forEach((el) => { if (document.activeElement !== el) el.checked = cats.includes(el.dataset.cat); });
  const arts = S.cat_counts.artefact || S.artifacts;
  $("artSub").textContent = arts ? `Все ${arts} ${plural(arts, ["артефакт", "артефакта", "артефактов"])} из базы игры` : "Все артефакты из базы игры";
  document.querySelectorAll("[data-cnt]").forEach((el) => {
    const n = S.cat_counts[el.dataset.cnt];
    el.textContent = n ? `${n} ${plural(n, ["предмет", "предмета", "предметов"])}${n > 100 ? ", круг станет длиннее примерно на " + Math.max(1, Math.round(n * 1.1 / 380 * 60)) + " с" : ""}` : "";
  });
  syncToggleLabels();
  if (CAT && view === "items") renderCatalog();
}
document.querySelectorAll("[data-cat]").forEach((el) => el.onchange = async () => {
  const cats = [...document.querySelectorAll("[data-cat]")].filter((x) => x.checked).map((x) => x.dataset.cat);
  const r = await api("/api/settings", {auto_categories: cats});
  const name = el.closest(".srow").querySelector(".tx div").textContent;
  toast(r.ok ? (el.checked ? name + ": проверяю целиком" : name + ": выключено") : r.message, !r.ok);
  syncToggleLabels(); refresh();
});
async function loadYield() {
  loadYield.at = Date.now();
  let r;
  try { r = await api("/api/yield"); } catch (e) { return; }
  if (!r || !r.ok) return;
  const rows = r.rows, empty = rows.filter((x) => x.status === "empty"), good = rows.filter((x) => x.status === "good");
  $("yieldBox").hidden = !rows.length;
  if (!rows.length) return;
  const share = r.total ? Math.round(empty.length / r.total * 100) : 0;
  $("yieldSub").textContent = good.length || empty.length
    ? `За неделю: ${good.length} ${plural(good.length, ["предмет дал", "предмета дали", "предметов дали"])} находки, на которые можно было успеть; ${empty.length} — ни одного лота дешевле рынка.`
    : "Нужны хотя бы сутки поиска, чтобы понять, какие предметы приносят находки.";
  const line = (x) => `<div class="yrow"><span>${esc(x.name)}</span><span class="small faint num">${x.status === "good"
      ? `${x.catch} ${plural(x.catch, ["лот успеть", "лота успеть", "лотов успеть"])}${x.deal ? `, находок ${x.deal}` : ""}`
      : `${x.lots} ${plural(x.lots, ["лот", "лота", "лотов"])} за ${Math.round(x.hours)} ч — дешевле рынка ни одного`}</span></div>`;
  $("yieldBody").innerHTML = (good.length ? `<div class="small muted" style="margin-top:6px">Приносят больше всего</div>${good.slice(0, 8).map(line).join("")}` : "")
    + (empty.length ? `<div class="small muted" style="margin-top:10px">Пустые</div>${empty.slice(0, 8).map(line).join("")}${empty.length > 8 ? `<div class="small faint">и ещё ${empty.length - 8}</div>` : ""}
      <div class="linkrow"><button class="btn" id="yieldDrop">Убрать пустые (${empty.length})</button><span class="small faint" style="align-self:center">круг станет короче примерно на ${share}%</span></div>` : "");
  const b = $("yieldDrop");
  if (b) b.onclick = async () => { const res = await api("/api/watch/remove", {ids: empty.map((x) => x.id)}); toast(res.message, !res.ok); await refresh(); loadYield(); };
}

// ---------- мои покупки: общая прибыль ----------
document.querySelectorAll("#pPeriod button").forEach((b) => b.onclick = () => { pPeriod = b.dataset.p; store.set("pPeriod", pPeriod); renderProfit(true); });
function dayStart(ts) { const d = new Date(ts * 1000); d.setHours(0, 0, 0, 0); return d.getTime() / 1000; }
let pDay = null, pBars = null;   // выбранный на графике день (или час): какие продажи показать в списке
function profitBars(sold, from, now) {
  const hourly = pPeriod === "day";
  const step = hourly ? 3600 : 86400, start = hourly ? dayStart(now) : dayStart(Math.max(from, now - 59 * 86400));
  const n = Math.max(1, Math.floor((now - start) / step) + 1);
  const vals = new Array(n).fill(0), cnt = new Array(n).fill(0);
  sold.forEach((p) => { const i = Math.floor((p.sold_at - start) / step); if (i >= 0 && i < n) { vals[i] += p.profit || 0; cnt[i] += 1; } });
  pBars = null;
  if (!cnt.some(Boolean)) return "";
  // рисуем в настоящих пикселях: подписи не растягиваются на широком окне, столбики не толще 56 пикселей
  const W = Math.max(280, Math.round($("pDays").clientWidth || 600)), H = 150, T = 10, B = 20;
  const max = Math.max(1, ...vals.map(Math.abs)), hasNeg = vals.some((v) => v < 0);
  const zero = hasNeg ? T + (H - T - B) / 2 : H - B, scale = (hasNeg ? (H - T - B) / 2 : H - T - B) / max, bw = W / n, w = Math.max(2, Math.min(56, bw * 0.7));
  const label = (i) => hourly ? `${i}:00` : new Date((start + i * step) * 1000).toLocaleDateString("ru-RU", {day: "2-digit", month: "2-digit"});
  pBars = {start, step, label};
  const selI = pDay && pDay.step === step ? Math.round((pDay.from - start) / step) : -1;
  const bars = vals.map((v, i) => { if (!cnt[i]) return "";
    const h = Math.max(2, Math.abs(v) * scale), x = i * bw + (bw - w) / 2, dim = selI >= 0 && selI !== i;
    return `<g class="pbar${selI === i ? " on" : ""}" data-i="${i}" tabindex="0" role="button" aria-label="${label(i)}: ${signed(v)}, продаж ${cnt[i]}">
      <rect class="hit" x="${(i * bw).toFixed(1)}" y="0" width="${bw.toFixed(1)}" height="${H - B}" fill="transparent"/>
      <rect x="${x.toFixed(1)}" y="${(v >= 0 ? zero - h : zero).toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" rx="3" fill="${v >= 0 ? "var(--good)" : "var(--bad)"}" opacity="${dim ? 0.35 : 1}"/>
      <title>${label(i)}: ${signed(v)}, продаж ${cnt[i]} — щёлкни, чтобы посмотреть</title></g>`; }).join("");
  const every = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(W / 70))));
  const ticks = vals.map((_, i) => i).filter((i) => i % every === 0 || i === n - 1).map((i) =>
    `<text x="${(i * bw + bw / 2).toFixed(1)}" y="${H - 4}" font-size="11" fill="var(--text-3)" text-anchor="middle">${label(i)}</text>`).join("");
  return `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Прибыль по ${hourly ? "часам" : "дням"}"><line x1="0" x2="${W}" y1="${zero}" y2="${zero}" stroke="var(--divider)"/>${bars}${ticks}</svg>`;
}
function pickDay(i) {
  if (!pBars) return;
  const from = pBars.start + i * pBars.step;
  pDay = pDay && pDay.from === from && pDay.step === pBars.step ? null : {from, to: from + pBars.step, step: pBars.step, label: pBars.label(i)};
  if (pDay) { bFilter = "sold"; store.set("bFilter", bFilter); }
  renderProfit(true); renderPurchases(true);
  if (pDay) $("bSeg").scrollIntoView({block: "start", behavior: "smooth"});
}
$("pDays").addEventListener("click", (e) => { const g = e.target.closest(".pbar"); if (g) pickDay(+g.dataset.i); });
$("pDays").addEventListener("keydown", (e) => { const g = e.target.closest(".pbar"); if (g && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); pickDay(+g.dataset.i); } });
try { new ResizeObserver(() => { if (view === "buys" && S) renderProfit(true); }).observe($("pDays")); } catch (e) {}
$("bDayClear").onclick = () => { pDay = null; renderProfit(true); renderPurchases(true); };
$("bBestBox").onclick = () => {   // «лучшая сделка» — показать её день
  const sold = (S.purchases || []).filter((p) => p.status === "sold" && p.sold_at);
  const best = sold.reduce((b, p) => (!b || (p.profit || 0) > (b.profit || 0) ? p : b), null);
  if (!best) return;
  const from = dayStart(best.sold_at);
  pDay = {from, to: from + 86400, step: 86400, label: new Date(from * 1000).toLocaleDateString("ru-RU", {day: "2-digit", month: "2-digit"}), best: best.id};
  if (pPeriod === "day" && from < dayStart(S.now)) { pPeriod = "all"; store.set("pPeriod", pPeriod); }
  bFilter = "sold"; renderProfit(true); renderPurchases(true); $("bSeg").scrollIntoView({block: "start", behavior: "smooth"});
};
let lastProfitSig = "";
function renderProfit(force) {
  const all = S.purchases || [], now = S.now;
  const sold = all.filter((p) => p.status === "sold" && p.sold_at), open = all.filter((p) => p.status !== "sold");
  const from = {day: dayStart(now), week: now - 7 * 86400, month: now - 30 * 86400, all: 0}[pPeriod] ?? 0;
  const sig = JSON.stringify([pPeriod, sold.map((p) => [p.id, p.profit, p.sold_at]), open.map((p) => [p.id, p.paid, p.cur_market, p.target]), Math.floor(now / 600)]);
  document.querySelectorAll("#pPeriod button").forEach((b) => b.classList.toggle("on", b.dataset.p === pPeriod));
  const sum = (a, f) => a.reduce((s, p) => s + f(p), 0);
  $("bInv").textContent = rub(sum(open, (p) => p.paid));
  $("bInvS").textContent = open.length ? open.length + " " + plural(open.length, ["покупка", "покупки", "покупок"]) + " не продано" : "всё продано";
  const exp = sum(open, pExpected); $("bExp").textContent = signed(exp); $("bExp").className = "num " + (exp >= 0 ? "good" : "bad");
  const best = sold.reduce((b, p) => (!b || (p.profit || 0) > (b.profit || 0) ? p : b), null);
  $("bBest").textContent = best ? signed(best.profit || 0) : "—"; $("bBest").className = "num " + (best && best.profit >= 0 ? "good" : best ? "bad" : "");
  $("bBestS").textContent = best ? best.name + ", " + agoTs(best.sold_at, now) : "появится после первой продажи";
  if (!force && sig === lastProfitSig) return;
  lastProfitSig = sig;
  const inP = sold.filter((p) => p.sold_at >= from);
  const earned = sum(inP, (p) => p.profit || 0), paid = sum(inP, (p) => p.paid || 0), pos = inP.filter((p) => (p.profit || 0) > 0).length;
  $("pEarned").textContent = inP.length ? signed(earned) : "0 ₽";
  $("pEarned").className = "earned num " + (inP.length ? (earned >= 0 ? "good" : "bad") : "");
  $("pLine").textContent = inP.length
    ? `${inP.length} ${plural(inP.length, ["продажа", "продажи", "продаж"])}, в плюс — ${pos}. В среднем ${signed(earned / inP.length)} за сделку` + (paid > 0 ? `, отдача ${Math.round(earned / paid * 100)}% к вложенному.` : ".")
    : sold.length ? "За этот период продаж нет." : "Пока ничего не продано. Отмечай продажи в списке ниже — здесь будет видно, сколько заработал.";
  $("pDays").innerHTML = profitBars(inP, from || (sold.length ? Math.min(...sold.map((p) => p.sold_at)) : now), now);
}

// ---------- мои покупки: список ----------
document.querySelectorAll("#bSeg button").forEach((b) => b.onclick = () => { bFilter = b.dataset.b; store.set("bFilter", bFilter); renderPurchases(true); });
function pUnit(p) { return p.cur_market || p.target; }
function pExpected(p) { return pUnit(p) * p.amount * (1 - S.settings.fee) - p.paid; }
const STATUS_RU = {holding: "в инвентаре", listed: "выставлен", sold: "продан"};
const OPT_RU = {fast: "Быстро", best: "Выгодно", slow: "Дороже"};
let lastBuysSig = "";
function sellHelp(p) {
  const opts = p.options || [], ls = p.list_state, many = p.amount > 1, per = (x) => rub(x) + (many ? "/шт" : "");
  const parts = [];
  if (p.status === "listed" && p.list_price) {
    const mine = p.list_price / p.amount;
    if (p.undercut || (ls && ls.cheaper)) {
      const best = (p.undercut && p.undercut.best) || (ls && ls.best), sug = (p.undercut && p.undercut.suggest) || (ls && ls.suggest);
      parts.push(`<div class="infobar err">${IC.err}<div class="tx"><b>Твой лот перебили.</b>Есть такой же за ${per(best)}, у тебя ${per(mine)}.${sug ? ` Чтобы продать первым, выставь за ${per(sug)}.` : ""}</div>${sug ? `<button class="btn" data-relist="${p.id}" data-total="${Math.round(sug * p.amount)}">Перевыставил за ${rubN(sug * p.amount)}</button>` : ""}</div>`);
    } else if (ls && ls.own) parts.push(`<div class="infobar ok">${IC.ok}<div class="tx">Твой лот за ${per(mine)} — самый дешёвый среди таких же. Трекер скажет, если его перебьют или он продастся.</div></div>`);
    else parts.push(`<div class="infobar info">${IC.info}<div class="tx">Выставлен за ${rub(p.list_price)}${many ? " за весь лот" : ""}. Трекер ещё не видел его на аукционе — новые лоты появляются в API примерно через 10 минут.</div></div>`);
  }
  if (!opts.length && !parts.length) return `<div class="pfoot"><span class="small faint">${p.cur_at ? "Подсказать цену не по чему: мало сделок по этому предмету." : "Подсказка, за сколько выставить, появится, когда поиск проверит этот предмет."}</span></div>`;
  const pick = optPick[p.id] || (opts.find((o) => o.key === "best") || opts[0] || {}).key;
  const chosen = opts.find((o) => o.key === pick);
  const listVal = Math.round(chosen ? chosen.total : p.list_price || p.paid);
  if (opts.length) parts.push(`<div class="lbl">${p.status === "listed" ? "Перевыставить" : "За сколько выставить"}</div><div class="opts num" role="radiogroup">${opts.map((o) =>
    `<button class="opt${o.key === pick ? " on" : ""}" role="radio" aria-checked="${o.key === pick}" data-opt="${p.id}" data-key="${o.key}"><span class="radio"></span><div><span class="k">${OPT_RU[o.key] || ""}</span><b>${per(o.unit)}</b><small>шанс ${Math.round(o.chance * 100)}%${o.hours ? ", " + fmtHours(o.hours) : ""}, ${signed(o.profit)}</small></div></button>`).join("")}</div>`);
  parts.push(`<div class="listrow"><span class="unit"><input class="field num" data-lp="${p.id}" value="${rubN(listVal)}" title="Цена за весь лот"><i>₽</i></span><button class="btn${p.status === "listed" ? "" : " accent"}" data-list="${p.id}">${p.status === "listed" ? "Перевыставил за эту цену" : "Выставил за эту цену"}</button></div>`);
  return `<div class="pfoot">${parts.join("")}</div>`;
}
function renderPurchases(force) {
  const all = S.purchases || [];
  const open = all.filter((p) => p.status !== "sold"), sold = all.filter((p) => p.status === "sold");
  document.querySelectorAll("#bSeg button").forEach((x) => x.classList.toggle("on", x.dataset.b === bFilter));
  $("bCntOpen").textContent = open.length || ""; $("bCntSold").textContent = sold.length || ""; $("bCntAll").textContent = all.length || "";
  $("cntBuys").textContent = open.length || "";
  let list = all.filter((p) => bFilter === "all" || (bFilter === "open" ? p.status !== "sold" : p.status === "sold"));
  const dayOn = !!pDay && bFilter !== "open";
  if (dayOn) list = list.filter((p) => p.status === "sold" && p.sold_at >= pDay.from && p.sold_at < pDay.to);
  $("bDayBox").hidden = !dayOn;
  if (dayOn) {
    const s = list.reduce((x, p) => x + (p.profit || 0), 0);
    $("bDayTxt").textContent = `${pDay.step === 3600 ? "Продажи в " + pDay.label : "Продажи за " + pDay.label}: ${list.length}, ${signed(s)}`;
  }
  if (document.activeElement && $("bRows").contains(document.activeElement) && document.activeElement.tagName === "INPUT") return;
  const sig = JSON.stringify([list, sellOpen, bFilter, optPick, pDay, Math.floor(S.now / 60)]);
  if (!force && sig === lastBuysSig) return;
  lastBuysSig = sig;
  $("bRows").innerHTML = list.map((p) => {
    const unit = pUnit(p), profit = p.status === "sold" ? (p.profit || 0) : pExpected(p), c = p.cur_chance;
    const actions = p.status === "sold" ? `<button class="btn" data-reopen="${p.id}">Вернуть</button>`
      : sellOpen === p.id ? `<span class="unit" style="width:150px"><input class="field num" id="sellPrice" value="${rubN(unit * p.amount)}" title="За сколько продал весь лот"><i>₽</i></span><button class="btn accent" data-sold="${p.id}">Сохранить</button><button class="btn subtle" data-cancel="1">Отмена</button>`
      : `${p.status === "listed" ? `<button class="btn" data-hold="${p.id}">Снял</button>` : ""}<button class="btn" data-sell="${p.id}">Продал…</button>`;
    const third = p.status === "sold" ? ["Продал за", rub(p.sold_price)] : p.status === "listed" && p.list_price ? ["Выставлен за", rub(p.list_price)] : [p.cur_market ? "Рынок сейчас" : "Оценка при покупке", rub(unit * p.amount)];
    return `<div class="pcard${pDay && pDay.best === p.id ? " hl" : ""}"><div class="prow">
      <div class="it">${slot(p.item_id, p.name, tone(p))}<div class="t"><div class="n">${esc(p.name)}</div><div class="m"><span class="pst ${p.status}">${STATUS_RU[p.status] || p.status}</span>${gradeTag(p)}${p.rare ? `<span class="tag rare">особо редкий</span>` : ""}<span>${p.amount > 1 ? p.amount + " шт, " : ""}куплено ${agoTs(p.bought_at, S.now)}</span></div></div></div>
      <div class="num"><div class="lbl">Купил за</div>${rub(p.paid)}</div>
      <div class="num"><div class="lbl">${third[0]}</div>${third[1]}</div>
      <div class="num"><div class="lbl">${p.status === "sold" ? "Прибыль" : "Прибыль" + (c ? `, шанс ${Math.round(c.chance * 100)}%` : "")}</div><span class="p${profit < 0 ? " neg" : ""}">${signed(profit)}</span></div>
      <div class="acts">${actions}<button class="ib" data-del="${p.id}" title="Удалить запись">${IC.del}</button></div>
    </div>${p.status === "sold" ? "" : sellHelp(p)}</div>`;
  }).join("");
  const empty = !list.length;
  $("bEmpty").hidden = !empty;
  if (empty && all.length) { $("bEmptyH").textContent = bFilter === "sold" ? "Пока ничего не продано" : "Всё продано"; $("bEmptyT").textContent = "Переключи фильтр сверху, чтобы увидеть остальные."; }
  else if (empty) { $("bEmptyH").textContent = "Пока нет покупок"; $("bEmptyT").textContent = "Купил лот из находок — выбери его и нажми «Я купил». Трекер будет следить за его ценой и подскажет, за сколько выставить."; }
  const upd = async (body) => { const r = await api("/api/purchases/update", body); if (!r.ok) toast(r.message, true); else sellOpen = null; await refresh(); renderPurchases(true); renderProfit(true); };
  const box = $("bRows");
  box.querySelectorAll("[data-opt]").forEach((b) => b.onclick = () => {
    optPick[b.dataset.opt] = b.dataset.key;
    const p = all.find((x) => x.id === b.dataset.opt), o = p && (p.options || []).find((x) => x.key === b.dataset.key);
    renderPurchases(true);
    const f = box.querySelector(`[data-lp="${b.dataset.opt}"]`); if (f && o) f.value = rubN(o.total);
  });
  box.querySelectorAll("[data-list]").forEach((b) => b.onclick = () => {
    const f = box.querySelector(`[data-lp="${b.dataset.list}"]`);
    upd({id: b.dataset.list, list_price: (f ? f.value : "").replace(/\s/g, "").replace(",", ".")});
  });
  box.querySelectorAll("[data-lp]").forEach((f) => f.onkeydown = (e) => { if (e.key === "Enter") box.querySelector(`[data-list="${f.dataset.lp}"]`).click(); });
  box.querySelectorAll("[data-relist]").forEach((b) => b.onclick = () => upd({id: b.dataset.relist, list_price: b.dataset.total}));
  box.querySelectorAll("[data-hold]").forEach((b) => b.onclick = () => upd({id: b.dataset.hold, status: "holding"}));
  box.querySelectorAll("[data-reopen]").forEach((b) => b.onclick = () => upd({id: b.dataset.reopen, status: "holding"}));
  box.querySelectorAll("[data-sell]").forEach((b) => b.onclick = () => { sellOpen = b.dataset.sell; renderPurchases(true); const f = $("sellPrice"); if (f) { f.focus(); f.select(); } });
  box.querySelectorAll("[data-cancel]").forEach((b) => b.onclick = () => { sellOpen = null; renderPurchases(true); });
  box.querySelectorAll("[data-sold]").forEach((b) => b.onclick = () => upd({id: b.dataset.sold, status: "sold", sold_price: $("sellPrice").value.replace(/\s/g, "").replace(",", ".")}));
  if ($("sellPrice")) $("sellPrice").onkeydown = (e) => { if (e.key === "Enter") box.querySelector("[data-sold]").click(); if (e.key === "Escape") { sellOpen = null; renderPurchases(true); } };
  box.querySelectorAll("[data-del]").forEach((b) => b.onclick = async () => { const r = await api("/api/purchases/remove", {id: b.dataset.del}); toast(r.message, !r.ok); await refresh(); renderPurchases(true); renderProfit(true); });
}
function renderAccuracy() {
  const a = S.status.accuracy, sold = (S.purchases || []).filter((p) => p.status === "sold");
  let html = "";
  if (sold.length) {
    const exp = sold.reduce((x, p) => x + (p.expected || 0), 0), got = sold.reduce((x, p) => x + (p.profit || 0), 0);
    html += `<p>Твои продажи: трекер обещал <b class="num">${signed(exp)}</b>, вышло <b class="num ${got >= 0 ? "good" : "bad"}">${signed(got)}</b> по ${sold.length} ${plural(sold.length, ["сделке", "сделкам", "сделкам"])}.</p>`;
  }
  if (!a) html += `<p>Сверка по рынку появится через несколько часов работы поиска: нужно, чтобы после находок прошли продажи таких же лотов.</p>`;
  else {
    const pct = Math.round(a.ratio * 100), hit = Math.round(a.hit * 100);
    html += `<p>По ${a.n} ${plural(a.n, ["находке", "находкам", "находкам"])} за неделю такие же лоты потом продавали в среднем за <b>${pct}%</b> от оценки трекера; оценка сбылась у <b>${hit}%</b>.
      ${a.factor < 0.995 ? `Поэтому оценка перепродажи сейчас снижена на <b>${Math.round((1 - a.factor) * 100)}%</b>${S.settings.calibrate === false ? " — но поправка выключена" : ""}.` : a.n < 15 ? "Для поправки нужно хотя бы 15 сверенных находок." : "Поправка не нужна."}</p>`;
    html += `<div class="accrows">${a.rows.map((r) => { const d = Math.round((r.fact / r.pred - 1) * 100);
      return `<div><span>${esc(r.name)}${r.kind === "near" ? ' <span class="faint small">(почти находка)</span>' : ""}</span><span class="num faint">оценка ${rub(r.pred)}</span><span class="num ${d >= -3 ? "good" : "bad"}">факт ${rub(r.fact)} (${d > 0 ? "+" : ""}${d}%)</span></div>`; }).join("")}</div>`;
  }
  const sig = JSON.stringify([a && a.at, sold.length, S.settings.calibrate]);
  if (sig !== renderAccuracy.sig) { renderAccuracy.sig = sig; $("accBody").innerHTML = html; }
}

// ---------- крафт ----------
let CR = null, crSel = null, CARD = null, cardLoading = null;
const FEAT_RU = {workbench: "верстак", centrifuge: "центрифуга", tool_trolley: "тележка с инструментами", laboratory_table: "лабораторный стол",
  rotary_evaporator: "роторный испаритель", chemical_reactor: "химический реактор", precise_tools: "точные инструменты", cnc: "станок ЧПУ",
  flasks_kit: "набор колб", hoods: "вытяжка", kitchen_items: "кухонная утварь", stove: "плита", welding_equipment: "сварка", lathe: "токарный станок",
  fermentation_container: "ёмкость для брожения", precise_powertools: "точный электроинструмент", sterilization_system: "стерилизатор",
  chromatographic_equipment: "хроматограф", kitchen_table: "кухонный стол", electronics_kit: "набор электроники", gauze_filter: "марлевый фильтр",
  laminar_box: "ламинарный бокс", calipers_kit: "штангенциркули", scalpels_kit: "скальпели", screwdrivers: "отвёртки", wrenches_kit: "гаечные ключи",
  laser_level: "лазерный уровень", generator_energy_source_battery: "генератор: аккумулятор", water_collector: "сборщик воды",
  generator_energy_source_anomal: "генератор: аномальный источник"};
async function loadCraft() {
  loadCraft.at = Date.now();
  let r;
  try { r = await api("/api/craft"); } catch (e) { return; }
  if (!r.ok) { $("advice").innerHTML = `<div class="muted">${esc(r.message || "Не получилось загрузить рецепты")}</div>`; return; }
  CR = r; renderSkills(); renderCraft();
}
function renderSkills() {
  if (!CR || document.activeElement && $("skills").contains(document.activeElement)) return;
  $("skills").innerHTML = CR.perks.map((p) => `<label class="skill"><span>${esc(p.name)}</span><span class="combo"><select data-perk="${p.id}">${[0, 1, 2, 3, 4, 5].map((l) => `<option value="${l}"${l === p.level ? " selected" : ""}>${l || "нет"}</option>`).join("")}</select><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><path d="m3 4.5 3 3 3-3"/></svg></span></label>`).join("");
  $("skills").querySelectorAll("select").forEach((sel) => sel.onchange = async () => {
    const skills = {}; $("skills").querySelectorAll("select").forEach((x) => skills[x.dataset.perk] = +x.value);
    const res = await api("/api/settings", {skills}); if (!res.ok) toast(res.message, true);
    sel.blur(); loadCraft();
  });
}
function crName(id) { return (CR && CR.names && CR.names[id]) || (CARD && CARD.names && CARD.names[id]) || id; }
const money = (x) => x == null ? `<span class="faint">—</span>` : signed(x);
function renderCraft() {
  if (!CR) return;
  const q = normQ($("crSearch").value), mine = $("crMine").classList.contains("on"), key = $("crSort").value;
  const perkName = Object.fromEntries(CR.perks.map((p) => [p.id, p.name]));
  let rows = CR.rows.filter((r) => (!mine || r.available) && (!q || [...r.result, ...r.ingredients].some(([i]) => normQ(crName(i)).includes(q))));
  const v = (r) => key === "energy" ? (r.per_energy ?? -1e12) : (r.profit ?? -1e12);
  rows.sort((a, b) => key === "name" ? crName(a.result[0][0]).localeCompare(crName(b.result[0][0]), "ru") : v(b) - v(a));
  const total = Object.keys(CR.names).length, priced = Object.keys(CR.prices).length;
  $("crPrices").textContent = `цены есть у ${priced} из ${total} предметов` + (CR.queued || S.status.craft_left ? `, узнаю ещё ${CR.queued || S.status.craft_left}` : "");
  const ing = (r) => r.ingredients.map(([i, n]) => `<span class="${CR.prices[i] ? "" : "np"}" title="${CR.prices[i] ? rub(CR.prices[i][0]) + "/шт по " + CR.prices[i][1] + " сделкам" : CR.trade[i] === false ? "не продаётся на аукционе" : "нет цены — нажми «Узнать цены»"}">${esc(crName(i))} ×${n}</span>`).join(", ");
  $("crRows").innerHTML = rows.slice(0, 200).map((r) => {
    const [rid, rn] = r.result[0];
    const need = Object.entries(r.need || {}).map(([k, l]) => `<span class="tag bad">${esc(perkName[k] || k)} ${l}</span>`).join("");
    const req = Object.entries(r.perks).filter(([k]) => !(k in (r.need || {}))).map(([k, l]) => `<span class="tag">${esc(perkName[k] || k)} ${l}</span>`).join("");
    return `<div class="tr${r.profit != null && r.profit <= 0 ? " loss" : ""}${crSel === r.id ? " sel" : ""}" data-r="${r.id}" role="option" aria-selected="${crSel === r.id}" title="Щёлкни — за сколько выставлять и почём брать ингредиенты">
      <div class="it">${slot(rid, crName(rid), "var(--q0)", "sm")}<div class="t"><div class="n">${esc(crName(rid))}${rn > 1 ? ` ×${rn}` : ""}</div><div class="tags">${need}${req}</div></div></div>
      <div class="ingl">${ing(r)}${r.missing.length ? `<div class="faint">нет цены: ${r.missing.slice(0, 3).map((i) => esc(crName(i))).join(", ")}${r.missing.length > 3 ? "…" : ""}</div>` : ""}</div>
      <div class="r num">${r.cost == null ? "—" : rub(r.cost)}</div>
      <div class="r num">${r.value == null ? "—" : rub(r.value)}</div>
      <div class="r num"><span class="p${r.profit != null && r.profit < 0 ? " neg" : ""}">${money(r.profit)}</span></div>
      <div class="r num">${money(r.per_energy)}<div class="s">энергия ${Math.round(r.energy)}</div></div></div>`;
  }).join("") || `<div class="empty"><p>${mine ? "По твоим навыкам рецептов не нашлось — поставь уровни навыков выше или нажми «Только доступные мне»." : "Ничего не найдено."}</p></div>`;
  $("crRows").querySelectorAll(".tr[data-r]").forEach((el) => el.onclick = () => openCraftCard(+el.dataset.r));
  $("advice").innerHTML = CR.advice.filter((a) => a.best).slice(0, 6).map((a) => `<div class="adv"><b>${esc(a.name)} ${a.level} → ${a.level + 1}</b>
      <span>откроет ${a.count} ${plural(a.count, ["прибыльный рецепт", "прибыльных рецепта", "прибыльных рецептов"])}; лучший — ${esc(crName(a.best.result[0][0]))}: <b class="num good">+${rub(a.best.profit)}</b> за крафт</span></div>`).join("")
    || `<div class="muted">${priced < total / 3 ? "Мало цен, чтобы советовать: нажми «Узнать цены» — трекер узнает их во время поиска." : "Следующие уровни навыков пока не открывают прибыльных рецептов по нынешним ценам."}</div>`;
}
$("crSearch").oninput = () => renderCraft();
$("crMine").onclick = () => { const on = !$("crMine").classList.contains("on"); $("crMine").classList.toggle("on", on); $("crMine").setAttribute("aria-pressed", on ? "true" : "false"); renderCraft(); };
$("crSort").onchange = () => renderCraft();
$("crFetch").onclick = async () => { const r = await api("/api/craft/fetch", {only_available: $("crMine").classList.contains("on")}); toast(r.message, !r.ok); loadCraft(); };

// ---------- карточка рецепта: за сколько выставлять, почём брать ингредиенты ----------
async function openCraftCard(id, fresh) {
  crSel = id; detailOpen = true; renderCraft();
  if (!CARD || CARD.id !== id || fresh) { CARD = {id, loading: true}; }
  syncDetail();
  if (!CARD.loading) return;
  const token = cardLoading = {};
  let r;
  try { r = await api(`/api/craft/card?id=${id}`); } catch (e) { r = {ok: false, message: "Нет связи с программой"}; }
  if (cardLoading !== token || crSel !== id) return;
  CARD = Object.assign(r, {id});
  renderCraftCard(true);
}
function priceVerdict(x) {
  if (x.floor == null || !x.live) return "";
  if (x.ceiling != null && x.floor > x.ceiling) return `<span class="pill bad">дороже, чем окупится</span>`;
  if (x.hist != null && x.floor <= x.hist * 1.02) return `<span class="pill good">по рынку или дешевле</span>`;
  return `<span class="pill warn">дороже рынка</span>`;
}
let lastCardSig = "";
function renderCraftCard(force) {
  const pane = $("detail");
  if (!CARD || CARD.id !== crSel) return;
  const sig = JSON.stringify([CARD.id, CARD.at, CARD.loading, narrowMQ.matches]);
  if (!force && sig === lastCardSig && pane.innerHTML) return;
  lastCardSig = sig;
  const head = (name, id, sub) => `<button class="ib x" id="dClose" title="Закрыть">${IC.close}</button>
    <div class="dh">${slot(id, name, "var(--q0)", "lg")}<div style="min-width:0"><h2>${esc(name)}</h2><div class="muted small">${esc(sub || "")}</div></div></div>`;
  const row = CR && CR.rows.find((r) => r.id === CARD.id);
  if (CARD.loading || !CARD.ok) {
    const rid = row ? row.result[0][0] : "";
    pane.innerHTML = head(row ? crName(rid) : "Рецепт", rid, "") + (CARD.loading
      ? `<div class="sec dc" style="display:flex;gap:10px;align-items:center">${IC.ring}<span class="muted">Смотрю цены на аукционе…</span></div>`
      : `<div class="note warn">${esc(CARD.message || "Не получилось загрузить рецепт")}</div>`);
    $("dClose").onclick = closeDetail;
    return;
  }
  const res = CARD.result[0], many = res.amount > 1, perX = (x) => rub(x) + (many ? "/шт" : "");
  const sub = [CARD.cat, CARD.sub].filter(Boolean).join(", ");
  const opts = res.options || [];
  const pick = optPick["craft" + CARD.id] || (opts.find((o) => o.key === "best") || opts[0] || {}).key;
  const profit = CARD.profit, live = CARD.profit_live;
  pane.innerHTML = head(res.name + (many ? " ×" + res.amount : ""), res.id, sub) + `
    <div class="hero num${profit != null && profit < 0 ? " neg" : ""}">${profit == null ? "—" : signed(profit)}</div>
    <div class="hero-s">${profit == null ? "не хватает цен — нажми «Узнать цены» во вкладке" : "прибыль за крафт по ценам рынка" + (CARD.per_energy != null ? `, ${signed(CARD.per_energy)} на 1000 энергии` : "")}</div>
    ${live != null ? `<div class="note ${live >= 0 ? "ok" : "warn"}">Если купить ингредиенты на аукционе прямо сейчас: <b>${signed(live)}</b> за крафт.</div>` : ""}
    ${CARD.note ? `<div class="note">${esc(CARD.note)}</div>` : ""}
    <div class="sec"><h3>За сколько выставлять</h3>
      ${opts.length ? `<div class="opts num" role="radiogroup">${opts.map((o) => `<button class="opt${o.key === pick ? " on" : ""}" role="radio" aria-checked="${o.key === pick}" data-copt="${o.key}"><span class="radio"></span><div><span class="k">${OPT_RU[o.key] || ""}</span><b>${perX(o.unit)}</b><small>шанс продать за сутки ${Math.round(o.chance * 100)}%${o.hours ? ", " + fmtHours(o.hours) : ""}; прибыль за крафт ${signed(o.profit)}</small></div></button>`).join("")}</div>`
        : `<div class="muted">${res.hist ? "Мало сделок, чтобы подсказать цену с шансом." : "Цены готового предмета ещё нет."} ${res.hist ? "Рынок — " + perX(res.hist) + "." : "Нажми «Узнать цены» во вкладке — трекер узнает её во время поиска."}</div>`}
      <div class="kv num" style="margin-top:12px">
        <span>Рынок по сделкам</span><b>${res.hist ? perX(res.hist) : "—"}</b>
        <span>Сейчас дешевле всего${res.lots_n != null ? `<small>лотов на аукционе: ${res.lots_n}</small>` : ""}</span><b>${res.floor ? perX(res.floor) : res.live ? "никто не продаёт" : "—"}</b>
        <span>Продаётся в сутки</span><b>${res.per_day != null ? n1(res.per_day) + " шт" : "—"}</b>
      </div>
    </div>
    <div class="sec"><h3>Почём брать ингредиенты</h3>
      ${CARD.ingredients.map((x, i) => `<div class="ing">${slot(x.id, x.name, "var(--q0)", "sm")}<div style="min-width:0"><div class="n">${esc(x.name)} ×${x.amount}</div>
        <div class="s">${x.hist ? "рынок " + rub(x.hist) + "/шт" : x.trade ? "цены нет" : "не продаётся на аукционе"}${x.floor ? `, сейчас от ${rub(x.floor)}` : x.live ? ", сейчас нет лотов" : ""} ${priceVerdict(x)}</div></div>
        <div class="pr num">${x.ceiling != null ? `<div class="small faint">не дороже</div><b>${rub(Math.max(0, x.ceiling))}</b>` : `<span class="faint">—</span>`}<div><button class="ib" data-icopy="${i}" title="Скопировать название">${IC.copy}</button></div></div></div>`).join("")}
      <div class="kv num" style="margin-top:8px">
        <span>Ингредиенты по рынку</span><b>${CARD.cost == null ? "—" : rub(CARD.cost)}</b>
        ${CARD.cost_live != null ? `<span>По аукциону сейчас</span><b>${rub(CARD.cost_live)}</b>` : ""}
        <span>Выручка после комиссии</span><b>${CARD.revenue == null ? "—" : rub(CARD.revenue)}</b>
      </div>
      <div class="small faint" style="margin-top:6px">«Не дороже» — цена за штуку, выше которой крафт уходит в минус (остальное — по рынку, продажа — по варианту «Выгодно»).</div>
    </div>
    <div class="sec"><h3>Что нужно</h3>
      <div class="kv num" style="margin-top:0"><span>Энергия</span><b>${Math.round(CARD.energy)}</b>
      ${CARD.perks.map((p) => `<span>${esc(p.name)}</span><b class="${p.have >= p.level ? "" : "bad"}">${p.level}${p.have >= p.level ? "" : `, у тебя ${p.have}`}</b>`).join("")}</div>
      ${CARD.features.length ? `<div class="small muted" style="margin-top:6px">В убежище: ${esc(CARD.features.map((f) => FEAT_RU[f] || f).join(", "))}</div>` : ""}
    </div>
    <div class="sec chart" id="cChart"><h3>Цена готового за неделю</h3><div class="muted">Загружаю…</div></div>
    <div class="actions"><button class="btn wide" id="cCopy">${IC.copy}Скопировать название</button><button class="btn subtle" id="cRefresh">Обновить цены</button></div>`;
  $("dClose").onclick = closeDetail;
  $("cCopy").onclick = () => copyText(res.name);
  $("cRefresh").onclick = () => openCraftCard(CARD.id, true);
  pane.querySelectorAll("[data-icopy]").forEach((b) => b.onclick = () => copyText(CARD.ingredients[+b.dataset.icopy].name));
  pane.querySelectorAll("[data-copt]").forEach((b) => b.onclick = () => { optPick["craft" + CARD.id] = b.dataset.copt; renderCraftCard(true); });
  const best = opts.find((o) => o.key === pick);
  loadItemStats(res.id, res.id, "", (r) => {
    if (!$("cChart") || !CARD || CARD.id !== crSel) return;
    $("cChart").innerHTML = "<h3>Цена готового за неделю</h3>" + (r ? priceChart(r.series, null, best ? best.unit : res.hist, 0) : "");
  });
}

// ---------- настройки: меняются сразу, как в «Параметрах» Windows ----------
function syncToggleLabels() { document.querySelectorAll(".toggle").forEach((t) => { const i = t.querySelector("input"), s = t.querySelector(".tr-st"); if (i && s) s.textContent = i.checked ? "Вкл." : "Откл."; }); }
function setVal(id, v) { const el = $(id); if (!el || document.activeElement === el) return; if (el.type === "checkbox") el.checked = !!v; else el.value = v; }
function fillForm() {
  const c = S.settings;
  setVal("sDemo", S.demo); setVal("sClientId", c.client_id || ""); setVal("sClientSecret", c.client_secret || "");
  if (document.activeElement !== $("sKeys") && !$("sKeys").dataset.bad) $("sKeys").value = (c.extra_keys || []).map((k) => `${k.id} ${"•".repeat(10)}`).join("\n");
  setVal("sDiscount", Math.round(c.discount * 100)); setVal("sMinProfit", rubN(c.min_profit));
  const bidsOn = c.bids !== false, bw = c.bid_window_minutes ?? 60, bm = c.bid_min_left_minutes ?? 3;
  setVal("sBids", bidsOn); setVal("sBidWindow", bw); setVal("sBidMin", bm);
  $("sBidWindow").disabled = $("sBidMin").disabled = !bidsOn;
  $("bidSum").textContent = bidsOn ? `Торги заканчиваются через ${bm}–${bw} мин, ставка ниже рынка` : "Выключено";
  setVal("sTgToken", c.telegram_token || ""); setVal("sTgChat", c.telegram_chat_id || "");
  setVal("sTgControl", c.tg_control !== false); setVal("sTgPhoto", c.tg_photo !== false); setVal("sTgQuiet", !!c.tg_quiet);
  setVal("sTgQFrom", String(c.tg_quiet_from ?? 0)); setVal("sTgQTo", String(c.tg_quiet_to ?? 8));
  setVal("sTgDaily", c.tg_daily !== false); setVal("sTgDailyH", String(c.tg_daily_hour ?? 23));
  $("sTgQFrom").disabled = $("sTgQTo").disabled = !c.tg_quiet; $("sTgDailyH").disabled = c.tg_daily === false;
  const tg = S.tg || {}, tgOn = !!(c.telegram_token && c.telegram_chat_id);
  const tgLine = !tgOn ? "" : tg.problem ? "⚠ " + tg.problem
    : c.tg_control === false ? "Кнопки и команды выключены — приходят только сообщения"
    : tg.listening ? "Бот на связи: кнопки и команды работают" + (tg.muted_until ? ` · тишина до ${new Date(tg.muted_until * 1000).toLocaleTimeString("ru-RU", {hour: "2-digit", minute: "2-digit"})}` : "") : "";
  $("tgState").hidden = !tgLine; $("tgState").textContent = tgLine; $("tgState").classList.toggle("warn", !!tg.problem);
  setVal("sRare", c.rare_enabled !== false); setVal("sRareQ", String(c.rare_quality ?? 4)); setVal("sRareProfit", rubN(c.rare_min_profit ?? 5000));
  setVal("sTheme", c.theme || "system"); setVal("sUi", c.ui || "new"); setVal("sScale", c.ui_scale || "m"); setVal("sAutostart", !!c.autostart);
  setVal("sSoundOn", c.sound_on !== false); setVal("sVolume", c.sound_volume ?? 70); $("sVolumeV").textContent = ($("sVolume").value) + "%";
  if (SOUNDS) { setVal("sSound", c.sound); setVal("sSoundRare", c.sound_rare); }
  $("soundSum").textContent = `${soundName(c.sound)}; для особо редких — ${soundName(c.sound_rare)}; громкость ${c.sound_volume ?? 70}%`;
  $("appVer").textContent = S.version || ""; $("dataDir").textContent = S.data_dir || "";
  const n = (c.extra_keys || []).length;
  $("keysSum").textContent = c.client_id ? `Client ID ${c.client_id}${n ? ` и ещё ${n} ${plural(n, ["ключ", "ключа", "ключей"])}` : ""}` : S.demo ? "Демо-режим: ключи не нужны" : "Вставь Client ID и Client Secret от @stalzone_api_bot";
  $("tgSum").textContent = c.telegram_token && c.telegram_chat_id ? "Бот настроен — находки и важное приходят в Telegram" : "Сообщение о каждой находке и о важном: продано, перебили, поиск встал";
  syncToggleLabels();
}
async function saveSetting(body, okMsg, el) {
  const r = await api("/api/settings", body);
  if (!r.ok) { toast(r.message, true); if (el) el.dataset.bad = "1"; }
  else { if (el) delete el.dataset.bad; if (okMsg) toast(okMsg === true ? r.message : okMsg); }
  await refresh();
  return r.ok;
}
const num = (v) => String(v).replace(/\s/g, "").replace(",", ".");
const onChange = (id, fn) => $(id).addEventListener("change", fn);
onChange("sDiscount", () => saveSetting({discount_pct: num($("sDiscount").value)}, "Сохранено"));
onChange("sMinProfit", () => saveSetting({min_profit: num($("sMinProfit").value)}, "Сохранено"));
onChange("sBids", () => saveSetting({bids: $("sBids").checked}, $("sBids").checked ? "Ищу и лоты со ставками" : "Лоты со ставками больше не ищу"));
onChange("sBidWindow", () => saveSetting({bid_window_minutes: num($("sBidWindow").value)}, "Сохранено", $("sBidWindow")));
onChange("sBidMin", () => saveSetting({bid_min_left_minutes: num($("sBidMin").value)}, "Сохранено", $("sBidMin")));
onChange("sDemo", () => saveSetting({demo: $("sDemo").checked}, $("sDemo").checked ? "Демо-режим включён" : "Демо-режим выключен"));
onChange("sClientId", () => saveSetting({client_id: $("sClientId").value}, "Сохранено — поиск перезапустится с этим ключом"));
onChange("sClientSecret", () => saveSetting({client_secret: $("sClientSecret").value}, "Сохранено — поиск перезапустится с этим ключом"));
onChange("sKeys", () => saveSetting({extra_keys: $("sKeys").value.split("\n")}, "Ключи сохранены", $("sKeys")));
onChange("sTgToken", () => saveSetting({telegram_token: $("sTgToken").value}, "Сохранено"));
onChange("sTgChat", () => saveSetting({telegram_chat_id: $("sTgChat").value}, "Сохранено"));
onChange("sTgControl", () => saveSetting({tg_control: $("sTgControl").checked}));
onChange("sTgPhoto", () => saveSetting({tg_photo: $("sTgPhoto").checked}));
onChange("sTgQuiet", () => saveSetting({tg_quiet: $("sTgQuiet").checked}));
onChange("sTgQFrom", () => saveSetting({tg_quiet_from: $("sTgQFrom").value}, "Сохранено"));
onChange("sTgQTo", () => saveSetting({tg_quiet_to: $("sTgQTo").value}, "Сохранено"));
onChange("sTgDaily", () => saveSetting({tg_daily: $("sTgDaily").checked}));
onChange("sTgDailyH", () => saveSetting({tg_daily_hour: $("sTgDailyH").value}, "Сохранено"));
$("tgFindBtn").onclick = async () => {
  toast("Ищу, кто написал боту…");
  const r = await api("/api/telegram/find", {telegram_token: $("sTgToken").value});
  toast(r.message, !r.ok);
  if (r.ok) { $("sTgChat").value = r.chat_id; await refresh(); }
};
onChange("sRare", () => { syncToggleLabels(); saveSetting({rare_enabled: $("sRare").checked}); });
onChange("sRareQ", () => saveSetting({rare_quality: $("sRareQ").value}, "Сохранено"));
onChange("sRareProfit", () => saveSetting({rare_min_profit: num($("sRareProfit").value)}, "Сохранено"));
onChange("sAutostart", () => { syncToggleLabels(); saveSetting({autostart: $("sAutostart").checked, autorun_search: $("sAutostart").checked}, true); });
onChange("sTheme", async () => { window.__setTheme($("sTheme").value); await saveSetting({theme: $("sTheme").value}); });
onChange("sScale", async () => { window.__setScale($("sScale").value); await saveSetting({ui_scale: $("sScale").value}); });
onChange("sUi", async () => { if (await saveSetting({ui: $("sUi").value})) location.reload(); });
onChange("sSoundOn", () => { syncToggleLabels(); saveSetting({sound_on: $("sSoundOn").checked}); });
onChange("sSound", () => { playSound($("sSound").value, $("sVolume").value / 100); saveSetting({sound: $("sSound").value}); });
onChange("sSoundRare", () => { playSound($("sSoundRare").value, $("sVolume").value / 100); saveSetting({sound_rare: $("sSoundRare").value}); });
$("sVolume").oninput = () => { $("sVolumeV").textContent = $("sVolume").value + "%"; };
onChange("sVolume", () => { playSound($("sSound").value, $("sVolume").value / 100); saveSetting({sound_volume: $("sVolume").value}); });
document.querySelectorAll("[data-play]").forEach((b) => b.onclick = () => playSound($(b.dataset.play).value, $("sVolume").value / 100));
document.querySelectorAll(".toggle input").forEach((i) => i.addEventListener("change", syncToggleLabels));
$("tgTestBtn").onclick = async () => {
  toast("Отправляю тестовое сообщение…");
  const r = await api("/api/telegram/test", {telegram_token: $("sTgToken").value, telegram_chat_id: $("sTgChat").value});
  toast(r.message, !r.ok);
};
$("openDataBtn").onclick = async () => { const r = await api("/api/open_data", {}); if (!r.ok) toast("Не получилось открыть — путь указан выше", true); };
$("updCheckBtn").onclick = async () => { await api("/api/update/check", {}); toast("Проверяю обновления…"); setTimeout(refresh, 1500); };
$("updBtn").onclick = async () => { await api("/api/update/apply", {}); toast("Скачиваю обновление…"); refresh(); };

// ---------- звуки: встроенные, Windows, свои ----------
let SOUNDS = null;
function soundName(id) {
  const s = String(id || ""), i = s.indexOf(":"), kind = s.slice(0, i), name = s.slice(i + 1);
  if (kind === "builtin") return SOUND_RU[name] || name;
  return name.replace(/\.(wav|mp3|ogg|m4a)$/i, "") + (kind === "win" ? " (Windows)" : "");
}
async function loadSounds() {
  try { SOUNDS = await api("/api/sounds"); } catch (e) { return; }
  const opts = (sel) => `<optgroup label="Встроенные">${SOUNDS.builtin.map((n) => `<option value="builtin:${n}">${esc(SOUND_RU[n] || n)}</option>`).join("")}</optgroup>`
    + (SOUNDS.custom.length ? `<optgroup label="Свои">${SOUNDS.custom.map((n) => `<option value="custom:${esc(n)}">${esc(n.replace(/\.(wav|mp3|ogg|m4a)$/i, ""))}</option>`).join("")}</optgroup>` : "")
    + (SOUNDS.windows.length ? `<optgroup label="Звуки Windows">${SOUNDS.windows.map((n) => `<option value="win:${esc(n)}">${esc(n.replace(/\.wav$/i, ""))}</option>`).join("")}</optgroup>` : "");
  $("sSound").innerHTML = opts(); $("sSoundRare").innerHTML = opts();
  $("customSounds").innerHTML = SOUNDS.custom.map((n) => `<div class="lrow"><span class="n">${esc(n)}</span><button class="btn subtle sm" data-cplay="custom:${esc(n)}">${IC.play}Прослушать</button><button class="ib" data-cdel="custom:${esc(n)}" title="Удалить звук">${IC.del}</button></div>`).join("");
  $("customSounds").querySelectorAll("[data-cplay]").forEach((b) => b.onclick = () => playSound(b.dataset.cplay, $("sVolume").value / 100));
  $("customSounds").querySelectorAll("[data-cdel]").forEach((b) => b.onclick = async () => { const r = await api("/api/sound/remove", {id: b.dataset.cdel}); toast(r.message, !r.ok); await loadSounds(); refresh(); });
  if (S) { $("sSound").value = S.settings.sound; $("sSoundRare").value = S.settings.sound_rare; }
}
$("soundPick").onclick = () => $("soundFile").click();
$("soundFile").onchange = async () => {
  const f = $("soundFile").files[0]; $("soundFile").value = "";
  if (!f) return;
  if (f.size > 4 * 1024 * 1024) { toast("Файл больше 4 МБ — выбери звук покороче", true); return; }
  let r;
  try {
    r = await (await fetch("/api/sound/upload", {method: "POST", headers: {"X-Token": TOKEN, "X-Filename": encodeURIComponent(f.name), "Content-Type": "application/octet-stream"}, body: f})).json();
  } catch (e) { r = {ok: false, message: "Не получилось загрузить звук"}; }
  toast(r.message, !r.ok);
  if (!r.ok) return;
  await loadSounds();
  await saveSetting({sound: r.id});
  playSound(r.id, $("sVolume").value / 100);
};

// ---------- доступ ----------
$("accCopyId").onclick = () => copyText((S.access || {}).request || $("accMachine").textContent, "Код запроса скопирован — отправь его владельцу");
$("lockCopy").onclick = () => copyText((S.access || {}).request || $("lockMachine").textContent, "Код запроса скопирован — отправь его владельцу");
async function enterCode(text) { const r = await api("/api/access/enter", {code: text}); toast(r.message, !r.ok); refresh(); return r.ok; }
$("lockBtn").onclick = () => enterCode($("lockCode").value);
$("accCodeBtn").onclick = async () => { if (await enterCode($("accCode").value)) $("accCode").value = ""; };
$("osCreate").onclick = async () => { const r = await api("/api/access/owner_key", {}); toast(r.message, !r.ok); refresh(); };
$("osCopy").onclick = () => copyText($("osPub").value, "Открытый ключ скопирован");
$("isBtn").onclick = async () => {
  const r = await api("/api/access/issue", {name: $("isName").value, machine: $("isMachine").value, days: $("isDays").value, seats: $("isSeats").value});
  toast(r.message, !r.ok);
  if (r.ok) { showInvite(r.code, +$("isDays").value || 0); $("isName").value = ""; $("isMachine").value = ""; }
  refresh();
};
function inviteText(code, days) {
  return `Доступ к STALZONE Трекеру${days ? ` на ${days} дн.` : ""}:\n1. Скачай программу: ${RELEASES_URL}\n2. Запусти и вставь этот код:\n${code}\n\nКлючи EXBO не нужны — находки приходят с моего сервера.`;
}
function showInvite(code, days) { $("isCode").value = code; $("isMsg").value = inviteText(code, days); $("isResult").hidden = false; }
$("isCopy").onclick = () => copyText($("isMsg").value, "Сообщение скопировано — отправь его подписчику");
$("isCopyCode").onclick = () => copyText($("isCode").value, "Код скопирован");
let funnelLink = null, srvDirty = false;
$("srvFunnel").onclick = async () => {
  toast("Открываю доступ через Tailscale…");
  const r = await api("/api/server/funnel", {});
  toast(r.message, !r.ok);
  funnelLink = r.link || null; $("srvLink").hidden = !funnelLink;
  if (r.ok) srvDirty = false;
  refresh();
};
$("srvLink").onclick = () => { if (funnelLink) api("/api/open", {url: funnelLink}); };
$("srvSave").onclick = async () => {
  const r = await api("/api/settings", {server_enabled: $("srvOn").checked, server_url: $("srvUrl").value});
  toast(r.ok ? ($("srvOn").checked ? "Сервер включён" : "Сервер выключен") : r.message, !r.ok); srvDirty = false; refresh();
};
$("srvTest").onclick = async () => { toast("Проверяю адрес из интернета…"); const r = await api("/api/server/test", {}); toast(r.message, !r.ok); };
$("srvOn").addEventListener("change", () => { srvDirty = true; });
$("srvUrl").oninput = () => { srvDirty = true; };
function onlineText(t) {
  if (!t) return `<span class="dotx"></span><span class="faint">не подключался</span>`;
  const m = (S.now - t) / 60;
  return m < 2 ? `<span class="dotx on"></span>онлайн` : `<span class="dotx"></span><span class="faint">${agoTs(t, S.now)}</span>`;
}
function keyLoad() {
  const st = (S && S.status) || {}, o = st.key_others, lim = st.key_limit || 400;
  return o != null && o >= lim * 0.1 ? {others: Math.round(o), limit: lim} : null;
}
function renderKeys() {
  const st = (S && S.status) || {}, n = (S.settings.extra_keys || []).length;
  $("keysInfo").textContent = !n ? "" : st.keys_total
    ? `Ключей в работе: ${st.keys} из ${st.keys_total}` + (st.keys < st.keys_total ? " — какой-то EXBO не пустила, смотри «Журнал»" : ", до " + (st.keys * 380) + " запросов в минуту")
      + (st.rate && st.max_rate && st.rate < st.max_rate * 0.97 ? `. Сейчас около ${Math.round(st.rate)} в минуту: EXBO ограничивает общую скорость, трекер подстроился` : "")
    : `Ещё ключей: ${n} — заработают после «Начать поиск»`;
}
let lastIssuedSig = "";
function renderAccess() {
  const a = S.access || {};
  const locked = !!(a.required && !a.ok);
  $("lockOverlay").hidden = !locked;
  if (locked) { $("lockReason").textContent = a.reason || ""; $("lockMachine").textContent = a.machine || "—"; }
  $("accMachine").textContent = a.machine || "—";
  $("accStatus").textContent = !a.required ? "Закрытый доступ ещё не включён — программа открыта всем."
    : a.mode === "owner" ? "Ты владелец программы — код доступа тебе не нужен."
    : a.ok ? (a.server ? `Подписка: ${a.name}, оплачено до ${a.expires_text}. Находки приходят с сервера владельца — ключи EXBO не нужны.`
      : `Доступ открыт: ${a.name}, срок — ${a.expires_text}. Номер кода: ${a.code_id}.` + (a.shared_api ? " Ключ API — владельца (вложен в код): свои ключи не нужны." : "")) : (a.reason || "");
  $("accCodeBox").hidden = !a.required || a.mode === "owner";
  const setup = !a.embedded;
  $("ownerSetup").hidden = !(setup || a.owner);
  $("osNoKey").hidden = !setup || a.has_owner_key || !a.has_crypto;
  $("osHasKey").hidden = !(setup && a.has_owner_key);
  $("osPub").value = a.owner_public || "";
  $("sharedNote").hidden = !S.shared_api;
  $("osSub").textContent = setup ? "Закрытый доступ включается один раз: владелец создаёт личный ключ, а его открытая часть вписывается в программу."
    : "Закрытый доступ включён. Ты владелец: коды выдаёшь в карточке «Выдать доступ».";
  $("osWarn").hidden = !a.has_owner_key || !(setup || a.owner);
  const owner = a.owner && a.embedded;
  $("ownerIssue").hidden = !owner; $("ownerList").hidden = !owner; $("serverCard").hidden = !owner;
  const sv = S.server || {};
  const kw = keyLoad();
  $("keyWarn").hidden = !kw;
  if (kw) {
    const names = (a.issued || []).filter((d) => d.shared && !d.renewed && !d.expired).map((d) => d.name);
    $("keyWarnText").textContent = `Сейчас твоим ключом пользуется ещё кто-то: около ${kw.others} запросов в минуту из ${kw.limit}, поэтому твой поиск медленнее. `
      + (names.length ? `Коды с твоим ключом: ${names.join(", ")}. ` : "Так бывает, если ключ вписан во вторую копию программы или на сайт. ")
      + "Как вернуть скорость: смени Client Secret в @stalzone_api_bot и впиши новый в «Настройки». Подписчикам выдай новые коды — они получают находки с твоего сервера и лимит не тратят.";
  }
  $("isWarn").hidden = !owner || !!(sv.enabled && sv.url);
  $("cntAccess").textContent = owner && sv.online ? sv.online : "";
  if (owner) {
    if (!srvDirty) { setVal("srvOn", !!sv.enabled); setVal("srvUrl", sv.url || ""); }
    $("funnelCmd").textContent = "tailscale funnel --bg " + (sv.port || 8790);
    $("srvStatus").innerHTML = !sv.enabled ? "Выключен. Подписчики не получают находки."
      : sv.running ? `Работает на этом компьютере (порт ${sv.port}). Подписчиков онлайн: <b>${sv.online}</b>, в ленте находок: <b>${sv.feed}</b>.`
        + `<br>Подписчики выбирают предметы сами — сервер проверяет и их${sv.sub_items ? ` (ещё <b>${sv.sub_items}</b>${(sv.sub_cats || []).length ? " и категории целиком" : ""})` : ""}. Каждая новая находка — сначала одному подписчику на 2 минуты, по очереди, потом всем.`
        + (S.status.running ? "" : `<br><b class="warn">Нажми «Начать поиск» — без проверки аукциона лента пустая.</b>`)
        + (sv.url ? "" : `<br><b class="warn">Впиши публичный адрес — без него подписчики не найдут сервер.</b>`)
      : `Не запустился: ${esc(sv.error || "")}`;
    const list = (a.issued || []).filter((d) => !d.renewed || d.blocked);
    const sig = JSON.stringify([list, Math.floor(S.now / 30)]);
    if (sig !== lastIssuedSig) {
      lastIssuedSig = sig;
      $("issuedList").innerHTML = list.length ? ["<span class='faint small'>Кто</span><span class='faint small'>Оплачено до</span><span class='faint small'>Сейчас</span><span></span>"]
        .concat(list.map((d) => `<span>${esc(d.name)} <span class="faint small">${d.machine === "*" ? `мест занято ${d.taken || 0} из ${d.seats || 1}` : esc(d.machine)}, № ${esc(d.id)}</span>${d.shared ? ` <span class="tag bad" title="Код с твоим ключом API: его программа тратит твой лимит. Смени Client Secret, и такой код перестанет работать">ключ API — тратит твой лимит</span>` : ""}${d.blocked ? ` <span class="tag bad">отключён</span>` : ""}</span>`
          + `<span class="${d.expired ? "bad" : ""}">${esc(d.expires_text)}</span><span>${onlineText(d.last_seen)}</span>`
          + `<span class="act"><button class="btn sm" data-renew="${esc(d.id)}">+30 дн.</button>${d.machine === "*" && d.taken ? `<button class="btn subtle sm" data-free="${esc(d.id)}" title="Подписчик сменил компьютер — место освободится, привяжется заново">Освободить</button>` : ""}<button class="btn subtle sm" data-block="${esc(d.id)}" data-on="${d.blocked ? 0 : 1}">${d.blocked ? "Включить" : "Отключить"}</button></span>`)).join("")
        : "<span class='faint' style='grid-column:1/-1'>Пока никому не выдавал.</span>";
      $("issuedList").querySelectorAll("[data-renew]").forEach((b) => b.onclick = async () => {
        const r = await api("/api/access/renew", {id: b.dataset.renew, days: 30});
        if (r.ok) { showInvite(r.code, 30); copyText($("isMsg").value, "Новый код и сообщение скопированы — отправь подписчику"); } else toast(r.message, true);
        refresh();
      });
      $("issuedList").querySelectorAll("[data-free]").forEach((b) => b.onclick = async () => { const r = await api("/api/access/free_seats", {id: b.dataset.free}); toast(r.message, !r.ok); refresh(); });
      $("issuedList").querySelectorAll("[data-block]").forEach((b) => b.onclick = async () => { const r = await api("/api/access/block", {id: b.dataset.block, blocked: b.dataset.on === "1"}); toast(r.message, !r.ok); refresh(); });
    }
  }
  const sub = sv.role === "subscriber";
  $("feedNote").hidden = !sub; $("subItemsNote").hidden = !sub;
}

// ---------- журнал ----------
let lastLogSig = "";
function renderLog(force) {
  const sig = S.log.length + ":" + (S.log.length ? S.log[S.log.length - 1].t + S.log[S.log.length - 1].m : "");
  if (!force && sig === lastLogSig) return;
  lastLogSig = sig;
  const cls = (m) => /ОШИБКА|ошибка/.test(m) ? "e" : /^⚠/.test(m) ? "w" : /^Найдено/.test(m) ? "f" : "";
  const box = $("views"), atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
  $("log").innerHTML = S.log.map((l) => `<div><span class="t">${l.t}</span><span class="${cls(l.m)}">${esc(l.m)}</span></div>`).join("");
  if (force || atBottom) box.scrollTop = box.scrollHeight;
}

// ---------- шапка: состояние поиска ----------
function renderStatus() {
  const st = S.status, run = st.running, sv = st.server;
  const subscriber = S.server && S.server.role === "subscriber";
  let txt = "Поиск остановлен";
  if (run) txt = st.starting ? "Запускаю…" : subscriber ? (sv && !sv.ok ? "Нет связи с сервером" : "Беру находки с сервера")
    : st.progress ? `Ищу: ${st.progress.done} из ${st.progress.total}` : "Ищу";
  $("stateTxt").textContent = txt;
  $("ring").hidden = !run; $("dot").hidden = run;
  const btn = $("runBtn"); btn.textContent = run ? "Остановить" : "Начать поиск"; btn.classList.toggle("accent", !run);
  const keys = st.keys_total || 1 + (S.settings.extra_keys || []).length;
  $("modeLbl").textContent = S.demo ? "демо-режим" : subscriber ? "подписка" : "аукцион, сервер RU";
  $("verLbl").textContent = `Версия ${S.version || ""}` + (keys > 1 && !subscriber ? `, ${keys} ${plural(keys, ["ключ", "ключа", "ключей"])} API` : "");
  $("onboard").hidden = S.configured;
  $("demoNote").hidden = !S.demo;
  $("demoNoteSub").textContent = S.has_keys ? "Ключи у тебя уже есть — выключи демо-режим." : "Находки здесь ненастоящие — режим нужен, только чтобы проверить, что всё работает.";
  const up = S.update || {}, busy = up.status === "downloading";
  $("updNote").hidden = !(up.status === "available" || busy);
  $("updTitle").textContent = busy ? up.message : `Доступна версия ${up.version || ""}.`;
  $("updSub").textContent = busy ? "Не закрывай программу — она перезапустится сама." : ((up.notes || "").split("\n").find((l) => l.trim() && !l.startsWith("#")) || "Скачается и установится само, программа перезапустится.");
  $("updBtn").hidden = up.status !== "available";
  $("updInfo").textContent = up.message || (up.repo ? "Ключи, настройки и находки хранятся отдельно — обновление их не сотрёт" : "Обновления не настроены");
  $("restartOverlay").hidden = up.status !== "restarting";
  const db = st.db;
  if (db && db.sales) {
    const n = (x) => String(x).replace(".", ",");
    $("dbInfo").textContent = `База сделок: ${db.sales.toLocaleString("ru-RU")} сделок по ${db.items} предм. за ${n(db.days)} дн., ${n(db.mb)} МБ`;
  }
  if (st.error && st.error_id !== lastErr) { lastErr = st.error_id; toast(st.error, true); }
}

// ---------- обновление раз в 2 секунды ----------
async function refresh() {
  try { S = await api("/api/state"); } catch (e) { $("stateTxt").textContent = "Нет связи с программой"; return; }
  const fresh = S.deals.filter((d) => !knownIds.has(d.id));
  fresh.forEach((d) => knownIds.add(d.id));
  const loud = fresh.filter((d) => d.notify !== false);   // о находках из прошлых запусков — тихо
  if (!firstLoad && loud.length) { beep(loud.some((d) => d.rare)); loud.slice(0, 3).forEach(notifyDesktop); }
  if (view === "settings" || firstLoad) fillForm();
  if (!CAT) loadCatalog();
  renderStatus(); renderLead(); renderDeals(); renderNear(); renderChips(); renderAccess(); renderKeys();
  if (view === "buys" || firstLoad) { renderProfit(); renderPurchases(); renderAccuracy(); }
  else $("cntBuys").textContent = (S.purchases || []).filter((p) => p.status !== "sold").length || "";
  if (view === "log") renderLog();
  if (view === "items" && Date.now() - (loadYield.at || 0) > 300000) loadYield();
  if (view === "craft" && Date.now() - (loadCraft.at || 0) > (S.status.craft_left ? 20000 : 120000)) loadCraft();
  if (view === "deals") syncDetail();
  firstLoad = false;
}
document.addEventListener("pointerdown", () => audioCtx(), {once: true});   // звук разрешён только после первого нажатия
refresh(); setInterval(refresh, 2000);
</script>
</body>
</html>
"""
# ==== НОВЫЙ ВИД: конец ====
