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
.listbar{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;margin:-6px 0 -8px}
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
.presets{display:flex;flex-direction:column;gap:10px}
.preset{all:unset;cursor:pointer;background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.preset:hover{border-color:var(--line-2)}
.preset b{display:block}
.preset span{color:var(--muted);font-size:13.5px}
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
        <div class="seg" id="kindSeg"><button data-k="all" class="on">Все</button><button data-k="buyout">Выкуп</button><button data-k="bid">Ставки</button></div>
        <select class="field" id="fCat" title="Категория"><option value="all">Все категории</option><option value="artefact">Артефакты</option><option value="armor">Броня</option><option value="weapon">Оружие</option><option value="parts">Запчасти</option><option value="tools">Инструменты</option><option value="other">Остальное</option></select>
        <select class="field" id="fChance" title="Шанс продать за сутки"><option value="0">Любой шанс</option><option value="30">Шанс от 30%</option><option value="50">Шанс от 50%</option><option value="70">Шанс от 70%</option></select>
        <input class="field small num" id="fProfit" placeholder="Прибыль от, ₽" inputmode="numeric">
        <button class="toggle rare" id="fRare" title="Только особо редкие находки">💎 Редкие</button>
        <button class="toggle" id="fFresh" title="Выставлены меньше 30 минут назад">Свежие</button>
      </div>
      <div class="listbar">
        <select class="field bare" id="fSort" title="Порядок"><option value="profit">Сначала самые прибыльные</option><option value="chance">Сначала самые надёжные</option><option value="listed">Сначала самые свежие</option><option value="pct">Сначала с самой большой скидкой</option><option value="name">По названию</option></select>
        <div class="spacer"></div>
        <label class="check"><input type="checkbox" id="hideOld" checked> Скрывать проданные и снятые</label>
        <button class="btn ghost sm" id="fReset">Сбросить фильтры</button>
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
          <div class="card">
            <h3>Готовые наборы</h3>
            <div class="sub">Добавляет предметы к списку, повторы не появятся.</div>
            <div class="presets">
              <button class="preset" data-preset="craft"><b>Ингредиенты твоих крафтов</b><span>Морфин, Янтарная полынь, Хлорид алюминия, Теломераза, Мутаген, Коагулянт, Чертоцвет, Полимеры, Помидор</span></button>
              <button class="preset" data-preset="arts"><b>Ходовые артефакты</b><span>Ледяной ежик, Вихрь, Змеиный глаз, Гелий, Спираль, Батарейка</span></button>
              <button class="preset" data-preset="hot"><b>Ходовые материалы</b><span>Огромный артефактный фрагмент, Моток медной проволоки, Аммиак, Набор специй, Полимеры</span></button>
            </div>
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
    </section>

    <section class="view" id="view-settings">
      <div class="form">
        <div class="card">
          <h3>Что считать выгодным</h3>
          <div class="sub">Лот попадёт в находки, только если выполнены оба условия.</div>
          <div class="row"><label>Дешевле рынка минимум на<small>в процентах</small></label><input class="field num" id="sDiscount" inputmode="numeric"></div>
          <div class="row"><label>Минимальная прибыль<small>после комиссии 5%, ₽</small></label><input class="field num" id="sMinProfit" inputmode="numeric"></div>
          <div class="row"><label>Пауза между кругами<small>минут; 0 — проверять без остановки (быстрее всего). Новые лоты API показывает с задержкой ~10 мин.</small></label><input class="field num" id="sPoll" inputmode="numeric"></div>
          <div class="row"><label>Рыночная цена по сделкам за<small>часов</small></label><input class="field num" id="sHist" inputmode="numeric"></div>
        </div>
        <div class="card">
          <h3>Доступ к API</h3>
          <div class="sub">Ключи выдаёт @stalzone_api_bot после одобрения заявки.</div>
          <div class="note ok" id="sharedNote" hidden>Работает ключ API владельца из кода доступа — свои ключи не нужны. Впишешь свои — будут использоваться они.</div>
          <div class="note ok" id="feedNote" hidden>Подписка: находки приходят с сервера владельца — ключи EXBO не нужны.</div>
          <div class="row" id="demoRow"><label>Демо-режим<small>Тестовые данные EXBO, ключи не нужны</small></label><label class="switch"><input type="checkbox" id="sDemo"><i></i></label></div>
          <div class="row wide"><label>Client ID</label><input class="field" id="sClientId" autocomplete="off"></div>
          <div class="row wide"><label>Client Secret</label><input class="field" id="sClientSecret" type="password" autocomplete="off"></div>
          <div class="row wide"><label>Токен (необязательно)<small>Только если EXBO выдала готовый токен</small></label><input class="field" id="sToken" type="password" autocomplete="off"></div>
          <div class="linkrow"><button class="btn" data-open="api_bot">Получить доступ</button><button class="btn" data-open="docs">Документация</button></div>
        </div>
        <div class="card">
          <h3>Уведомления</h3>
          <div class="sub">Звук в программе и сообщение в Telegram о каждой новой находке.</div>
          <div class="row"><label>Звук при находке<small>сохраняется на этом компьютере</small></label><label class="switch"><input type="checkbox" id="sSound"><i></i></label></div>
          <div class="row"><label>Только если шанс продажи от<small>%, особо редкие — всегда; 0 — обо всех</small></label><input class="field num" id="sMinChance" inputmode="numeric"></div>
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
          <h3>Ставки</h3>
          <div class="sub">Лоты со ставками, которые скоро закончатся, а ставка сильно ниже рынка.</div>
          <div class="row"><label>Искать выгодные ставки</label><label class="switch"><input type="checkbox" id="sBids"><i></i></label></div>
          <div class="row"><label>Лоты, что закончатся в ближайшие<small>минут</small></label><input class="field num" id="sBidWin" inputmode="numeric"></div>
        </div>
        <div class="card">
          <h3>Программа и данные</h3>
          <div class="sub">Версия <span id="appVer"></span>. Ключи, настройки, находки и журнал хранятся отдельно от программы — обновление их не сотрёт.</div>
          <div class="row w2"><label>Тема<small>меняется сразу</small></label><select class="field" id="sTheme"><option value="system">Как в Windows</option><option value="light">Светлая</option><option value="dark">Тёмная</option></select></div>
          <div class="row wide"><label>Папка с данными<small id="dataDir" style="word-break:break-all"></small></label></div>
          <div class="row"><label>Хранить историю сделок<small>дней, от 3 до 90: больше — точнее оценка редких артефактов</small></label><input class="field num" id="sKeep" inputmode="numeric"></div>
          <div class="muted small" id="dbInfo" style="margin-top:10px">База сделок пока пустая — начнёт копиться после запуска.</div>
          <div class="row wide" style="margin-top:6px"><label>Обновления с GitHub<small>репозиторий «владелец/имя» — программа сама проверит, скачает и поставит новую версию</small></label><input class="field" id="sUpdRepo" placeholder="например, ivan/stalzone-tracker" autocomplete="off"></div>
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
            <div class="sub">По коду запроса владелец выдаёт код доступа. Код работает только на этом компьютере.</div>
            <div class="idrow"><b class="num" id="accMachine">—</b><button class="btn" id="accCopyId">Копировать код запроса</button></div>
            <div class="muted small" style="margin:-4px 0 8px">Код запроса = ID компьютера + его ключ. С ним владелец может вложить в код доступа свой ключ API — тогда свои ключи не нужны.</div>
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
          <div class="card" id="serverCard" hidden>
            <h3>Сервер для подписчиков</h3>
            <div class="sub">Твоя программа ищет находки твоим ключом EXBO и раздаёт их подписчикам — им ключи не нужны. Пока сервер работает, компьютер должен быть включён.</div>
            <div class="row"><label>Раздавать находки подписчикам</label><label class="switch"><input type="checkbox" id="srvOn"><i></i></label></div>
            <div class="row wide"><label>Публичный адрес<small>его даёт Tailscale Funnel, например https://мой-пк.xxxx.ts.net — он вписывается в новые коды</small></label><input class="field" id="srvUrl" placeholder="https://…ts.net" autocomplete="off"></div>
            <div class="note" id="srvStatus"></div>
            <div class="linkrow"><button class="btn primary" id="srvSave">Сохранить</button><button class="btn" id="srvTest">Проверить адрес</button></div>
            <details class="note howto"><summary>Как открыть сервер в интернет — бесплатно, без настройки роутера</summary>
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
            <div class="sub">Друг запускает программу, жмёт «Копировать код запроса» и присылает тебе. Если включён сервер для подписчиков, друг получает твои находки и ключи EXBO ему не нужны.</div>
            <div class="row wide"><label>Имя<small>по нему потом можно отозвать доступ</small></label><input class="field" id="isName" autocomplete="off"></div>
            <div class="row wide"><label>Код запроса друга<small>друг копирует его в своей программе: «Копировать код запроса»</small></label><input class="field" id="isMachine" placeholder="SZR1-…" autocomplete="off"></div>
            <div class="row"><label>Вложить мой ключ API<small>другу не нужны свои ключи, но лимит EXBO (400 в минуту) делится между вами — твой поиск станет медленнее вдвое. Лучше сервер для подписчиков.</small></label><label class="switch"><input type="checkbox" id="isShare"><i></i></label></div>
            <div class="row"><label>Срок<small>дней, 0 — бессрочно</small></label><input class="field num" id="isDays" value="30" inputmode="numeric"></div>
            <div class="linkrow"><button class="btn primary" id="isBtn">Создать код</button></div>
            <div id="isResult" hidden>
              <div class="row wide"><label>Код для друга<small>отправь целиком, вместе со ссылкой на программу</small></label><textarea class="field code" id="isCode" readonly></textarea></div>
              <div class="linkrow"><button class="btn" id="isCopy">Копировать код</button><button class="btn" id="isCopyLink">Копировать ссылку на программу</button></div>
            </div>
          </div>
          <div class="card" id="ownerList" hidden>
            <h3>Подписчики</h3>
            <div class="sub">«+30 дн.» создаёт новый код с продлением от конца оплаченного срока и копирует его — отправь подписчику. «Отключить» сразу закрывает ему находки с сервера.</div>
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
const PRESETS = {
  craft: ["Морфин","Янтарная полынь","Хлорид алюминия","Теломераза","Мутаген","Коагулянт","Чертоцвет","Полимеры","Помидор"],
  arts: ["Ледяной ежик","Вихрь","Змеиный глаз","Гелий","Спираль","Батарейка"],
  hot: ["Огромный артефактный фрагмент","Моток медной проволоки","Аммиак","Набор специй","Полимеры"],
};
const TITLES = {deals:"Находки", items:"Предметы", buys:"Мои покупки", settings:"Настройки", access:"Доступ", log:"Журнал"};
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
let F = Object.assign({cat: "all", chance: 0, profit: "", rare: false, fresh: false, sort: "profit"}, store.get("filters", {}));
let bFilter = store.get("bFilter", "open"), sellOpen = null, showBarter = store.get("showBarter", false);

// ---------- тема ----------
function applyTheme(t) { if (t === "light" || t === "dark") document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; }
applyTheme(store.get("theme", "system"));

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
$("kindSeg").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; kind = b.dataset.k; [...$("kindSeg").children].forEach((x) => x.classList.toggle("on", x === b)); renderDeals(true); };
$("search").oninput = () => renderDeals(true);
$("hideOld").onchange = () => { renderDeals(true); renderNear(true); };
$("clearBtn").onclick = async () => { await api("/api/deals/clear", {}); closeDrawer(); refresh(); };
function catGroup(c) { return FILTER_CATS.includes(c) ? c : "other"; }
function saveFilters() { store.set("filters", F); }
function syncFilters() {
  $("fCat").value = F.cat; $("fChance").value = String(F.chance || 0); $("fProfit").value = F.profit || ""; $("fSort").value = F.sort || "profit";
  $("fRare").classList.toggle("on", !!F.rare); $("fFresh").classList.toggle("on", !!F.fresh);
}
$("fCat").onchange = () => { F.cat = $("fCat").value; saveFilters(); renderDeals(true); };
$("fChance").onchange = () => { F.chance = +$("fChance").value; saveFilters(); renderDeals(true); };
$("fProfit").oninput = () => { F.profit = $("fProfit").value.replace(/\D/g, ""); saveFilters(); renderDeals(true); };
$("fSort").onchange = () => { F.sort = $("fSort").value; saveFilters(); renderDeals(true); };
$("fRare").onclick = () => { F.rare = !F.rare; saveFilters(); syncFilters(); renderDeals(true); };
$("fFresh").onclick = () => { F.fresh = !F.fresh; saveFilters(); syncFilters(); renderDeals(true); };
$("fReset").onclick = () => { F = {cat: "all", chance: 0, profit: "", rare: false, fresh: false, sort: "profit"}; $("search").value = ""; saveFilters(); syncFilters(); renderDeals(true); };
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
  const val = (d) => key === "listed" ? Date.parse(d.listed || 0) : key === "chance" ? (d.chance == null ? -1 : d.chance) : key === "name" ? d.name : d[key];
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
document.querySelectorAll("[data-preset]").forEach((b) => b.onclick = () => {
  const list = watch(), add = PRESETS[b.dataset.preset].filter((n) => !list.some((x) => normName(entryName(x)) === normName(n)));
  if (!add.length) return toast("Всё из набора уже в списке");
  saveWatch(list.concat(add), "Добавлено: " + add.length);
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
      <td><span class="inline">${actions}<button class="btn sm ghost" data-del="${p.id}" title="Удалить запись">✕</button></span></td></tr>`;
  }).join("");
  const empty = !list.length;
  $("bEmpty").style.display = empty ? "grid" : "none";
  if (empty && all.length) { $("bEmptyH").textContent = bFilter === "sold" ? "Пока ничего не продано" : "Всё продано"; $("bEmptyT").textContent = "Переключи фильтр сверху, чтобы увидеть остальные."; }
  else if (empty) { $("bEmptyH").textContent = "Пока нет покупок"; $("bEmptyT").textContent = "Купил лот из находок — открой его и нажми «Я купил». Трекер будет следить за его ценой и шансом продажи."; }
  const upd = async (body) => { const r = await api("/api/purchases/update", body); if (!r.ok) toast(r.message, true); else sellOpen = null; await refresh(); renderPurchases(true); };
  $("bRows").querySelectorAll("[data-listed]").forEach((b) => b.onclick = () => upd({id: b.dataset.listed, status: "listed"}));
  $("bRows").querySelectorAll("[data-hold]").forEach((b) => b.onclick = () => upd({id: b.dataset.hold, status: "holding"}));
  $("bRows").querySelectorAll("[data-reopen]").forEach((b) => b.onclick = () => upd({id: b.dataset.reopen, status: "holding"}));
  $("bRows").querySelectorAll("[data-sell]").forEach((b) => b.onclick = () => { sellOpen = b.dataset.sell; renderPurchases(true); const f = $("sellPrice"); if (f) { f.focus(); f.select(); } });
  $("bRows").querySelectorAll("[data-sold]").forEach((b) => b.onclick = () => upd({id: b.dataset.sold, status: "sold", sold_price: $("sellPrice").value.replace(/\s/g, "").replace(",", ".")}));
  $("bRows").querySelectorAll("[data-del]").forEach((b) => b.onclick = async () => { const r = await api("/api/purchases/remove", {id: b.dataset.del}); toast(r.message, !r.ok); await refresh(); renderPurchases(true); });
}

// ---------- настройки ----------
function fillForm() {
  const c = S.settings;
  $("sDemo").checked = S.demo; $("sClientId").value = c.client_id || ""; $("sClientSecret").value = c.client_secret || ""; $("sToken").value = c.app_token || "";
  $("sDiscount").value = Math.round(c.discount * 100); $("sMinProfit").value = Math.round(c.min_profit); $("sPoll").value = c.poll_minutes;
  $("sHist").value = c.history_hours; $("sBids").checked = !!c.bids; $("sBidWin").value = c.bid_window_minutes;
  $("sTgToken").value = c.telegram_token || ""; $("sTgChat").value = c.telegram_chat_id || ""; $("sSound").checked = store.get("sound", true);
  $("appVer").textContent = S.version || ""; $("dataDir").textContent = S.data_dir || "";
  $("sKeep").value = c.history_keep_days || 14;
  $("sUpdRepo").value = c.update_repo || "";
  $("sRare").checked = c.rare_enabled !== false; $("sRareQ").value = String(c.rare_quality ?? 4);
  $("sRareProfit").value = Math.round(c.rare_min_profit ?? 5000); $("sMinChance").value = Math.round(c.notify_min_chance || 0);
  $("sTheme").value = store.get("theme", "system");
}
document.querySelectorAll("#view-settings input, #view-settings select").forEach((el) => el.addEventListener("input", () => {
  if (el.id === "sTheme" || el.id === "sSound") return;
  formDirty = true; $("saveHint").textContent = "Есть несохранённые изменения";
}));
$("sTheme").onchange = () => { store.set("theme", $("sTheme").value); applyTheme($("sTheme").value); };
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
    demo: $("sDemo").checked, client_id: $("sClientId").value, client_secret: $("sClientSecret").value, app_token: $("sToken").value,
    discount_pct: num("sDiscount"), min_profit: num("sMinProfit"), poll_minutes: num("sPoll"), history_hours: num("sHist"),
    bids: $("sBids").checked, bid_window_minutes: num("sBidWin"), telegram_token: $("sTgToken").value, telegram_chat_id: $("sTgChat").value,
    history_keep_days: num("sKeep"), update_repo: $("sUpdRepo").value,
    rare_enabled: $("sRare").checked, rare_quality: $("sRareQ").value, rare_min_profit: num("sRareProfit"),
    notify_min_chance: num("sMinChance"),
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
  const r = await api("/api/access/issue", {name: $("isName").value, machine: $("isMachine").value, days: $("isDays").value, share: $("isShare").checked});
  toast(r.message, !r.ok);
  if (r.ok) { $("isCode").value = r.code; $("isResult").hidden = false; $("isName").value = ""; $("isMachine").value = ""; }
  refresh();
};
$("isCopy").onclick = () => copyText($("isCode").value, "Код скопирован — отправь его другу");
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
$("isCopyLink").onclick = () => copyText(RELEASES_URL, "Ссылка на программу скопирована");
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
  if (owner) {
    if (!srvDirty) { $("srvOn").checked = !!sv.enabled; $("srvUrl").value = sv.url || ""; }
    $("funnelCmd").textContent = "tailscale funnel --bg " + (sv.port || 8790);
    $("srvStatus").innerHTML = !sv.enabled ? "Выключен. Подписчики не получают находки."
      : sv.running ? `Работает на этом компьютере (порт ${sv.port}). Подписчиков онлайн: <b>${sv.online}</b> · в ленте находок: <b>${sv.feed}</b>`
        + (S.status.running ? "" : `<br><b style="color:var(--amber-text)">Нажми «Начать поиск» — без проверки аукциона лента пустая.</b>`)
        + (sv.url ? "" : `<br><b style="color:var(--amber-text)">Впиши публичный адрес — без него подписчики не найдут сервер.</b>`)
      : `Не запустился: ${esc(sv.error || "")}`;
    const list = (a.issued || []).filter((d) => !d.renewed || d.blocked);
    $("issuedList").innerHTML = list.length ? ["<span class='muted'>Кто</span><span class='muted'>Оплачено до</span><span class='muted'>Сейчас</span><span></span>"]
      .concat(list.map((d) => `<span>${esc(d.name)} <span class="muted">${esc(d.machine)} · № ${esc(d.id)}</span>${d.shared ? ` <span class="tag" title="С твоим ключом API">ключ API</span>` : ""}${d.blocked ? ` <span class="tag" style="color:var(--bad)">отключён</span>` : ""}</span>`
        + `<span style="${d.expired ? "color:var(--bad)" : ""}">${esc(d.expires_text)}</span><span>${onlineText(d.last_seen)}</span>`
        + `<span class="act"><button class="btn sm" data-renew="${esc(d.id)}">+30 дн.</button><button class="btn sm ghost" data-block="${esc(d.id)}" data-on="${d.blocked ? 0 : 1}">${d.blocked ? "Включить" : "Отключить"}</button></span>`)).join("")
      : "<span class='muted' style='grid-column:1/-1'>Пока никому не выдавал.</span>";
    $("issuedList").querySelectorAll("[data-renew]").forEach((b) => b.onclick = async () => {
      const r = await api("/api/access/renew", {id: b.dataset.renew, days: 30});
      if (r.ok) { copyText(r.code, r.message); $("isCode").value = r.code; $("isResult").hidden = false; } else toast(r.message, true);
      refresh();
    });
    $("issuedList").querySelectorAll("[data-block]").forEach((b) => b.onclick = async () => {
      const r = await api("/api/access/block", {id: b.dataset.block, blocked: b.dataset.on === "1"}); toast(r.message, !r.ok); refresh();
    });
  }
  const sub = sv.role === "subscriber";
  $("feedNote").hidden = !sub; $("subItemsNote").hidden = !sub;
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
  renderStatus(); renderDeals(); renderNear(); renderChips(); renderPurchases(); renderAccess();
  firstLoad = false;
}
document.querySelector('.nav button[data-view="log"]').addEventListener("click", () => { if (S) renderStatus(); });
refresh(); setInterval(refresh, 2000);
</script>
</body>
</html>
"""
