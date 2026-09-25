"""Build a portable, local listening page from generated audition manifests."""

import html
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent


def rows(path, engine):
    data = json.loads((OUT / path).read_text(encoding="utf-8"))
    by_voice = {}
    for item in data["samples"]:
        if item["status"] != "ok":
            continue
        key = item["voice"]
        row = by_voice.setdefault(key, {"engine": engine, "voice": key,
                                       "label": item["label"], "clips": {}})
        row["clips"][item["passage"]] = item["file"]
    return list(by_voice.values())


def main():
    all_rows = (rows("manifest.json", "VieNeu v3 Turbo · GPU") +
                rows("zerotts-manifest.json", "ZeroTTS · CPU") +
                rows("piper-gpu-manifest.json", "Piper · GPU"))
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    payload = json.dumps({"rows": all_rows, "passages": manifest["passages"]},
                         ensure_ascii=False).replace("<", "\\u003c")
    page = f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nghe thử giọng truyện ma</title>
<style>
:root{{--bg:#11141d;--card:#1e2330;--ink:#f3f0e9;--muted:#c0bdba;--accent:#dcac68;--line:#454550}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at top,#2b2634,#11141d 60%);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:1120px;margin:auto;padding:28px 18px 100px}}h1{{font:700 clamp(30px,5vw,50px)/1.15 Georgia,serif;margin:8px 0 10px;color:#f4d8ae}}
h2{{font:700 28px Georgia,serif;margin:42px 0 16px;color:#f4d8ae}}p{{margin:8px 0}}.muted,small{{color:var(--muted)}}
.intro,.toolbar,.feedback{{background:#1a1c28;border:1px solid var(--line);border-radius:16px;padding:18px;margin:18px 0}}
.passage{{border-left:3px solid var(--accent);padding-left:12px;margin:14px 0;color:#e9e4dc}}
.toolbar{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;position:sticky;top:0;z-index:5}}
input[type=search],textarea,select,input[type=text]{{background:#11141d;color:var(--ink);border:1px solid #666574;border-radius:8px;padding:9px;font:inherit}}
input[type=search]{{min-width:250px;flex:1}}button{{background:var(--accent);color:#16151b;border:0;border-radius:8px;padding:10px 15px;font:700 15px system-ui;cursor:pointer}}
button:hover{{filter:brightness(1.12)}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(315px,1fr));gap:14px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;min-width:0}}
.card h3{{margin:0 0 3px;font-size:20px}}.card .meta{{color:var(--muted);font-size:13px;min-height:39px}}
.clip{{margin:12px 0}}.clip label{{display:block;color:#f0d2a7;font-weight:650;margin-bottom:4px}}
audio{{width:100%;height:42px}}.choices{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:10px 0}}
.choices label{{display:flex;align-items:center;gap:5px}}.note{{width:100%}}textarea{{width:100%;min-height:90px}}
.hidden{{display:none!important}}a{{color:#f5c989}}.count{{color:#f1c47f;font-weight:700}}
@media(max-width:600px){{main{{padding:18px 12px 80px}}.toolbar{{top:0;padding:10px}}}}
</style>
</head>
<body><main>
<p class="muted">BỘ MẪU GIỌNG · 24/09/2026</p>
<h1>Nghe thử giọng kể truyện ma</h1>
<p><strong>Bộ này chỉ để chọn chất giọng, chưa kiểm tra khả năng diễn cảm xúc.</strong> 36 giọng Việt từ 3 engine miễn phí đọc hai đoạn dưới đây. Hãy nghe bằng tai nghe và ghi chú giọng nào có chất giọng hợp truyện ma.</p>
<div class="intro"><strong>Đoạn tự sự</strong><p class="passage">{html.escape(manifest['passages']['tu_su'])}</p>
<strong>Đoạn hồi hộp, có thoại</strong><p class="passage">{html.escape(manifest['passages']['hoi_hop'])}</p>
<small>Trích nguyên văn từ content revision 1 của <code>thu-5p-h007g</code>. Đây là mẫu độc lập; chưa thay giọng trong job.</small></div>
<div class="toolbar"><input id="search" type="search" placeholder="Tìm tên giọng hoặc engine"><span class="count" id="count"></span><button id="showFav">Chỉ giọng đã chọn</button></div>
<div id="sections"></div>
<div class="feedback"><h2>Giọng bạn chọn</h2><p class="muted">Điểm và ghi chú được giữ trong trình duyệt trên máy này. Bấm nút để tạo phản hồi, rồi gửi nguyên văn cho mình.</p>
<button id="makeReply">Tạo phản hồi để gửi</button><p><textarea id="reply" readonly placeholder="Giọng bạn chọn sẽ hiện ở đây."></textarea></p></div>
<p class="muted">Nguồn và giới hạn: <a href="README.md">README.md</a>. Các file WAV được lưu cạnh trang này, mở được khi không có mạng.</p>
</main>
<script id="data" type="application/json">{payload}</script>
<script>
const data=JSON.parse(document.getElementById('data').textContent);
const saved=JSON.parse(localStorage.getItem('voice-audition-20260924')||'{{}}');
let onlyFav=false;
function save(){{localStorage.setItem('voice-audition-20260924',JSON.stringify(saved));}}
function render(){{
  const q=document.getElementById('search').value.trim().toLocaleLowerCase('vi');
  const host=document.getElementById('sections');host.replaceChildren();let visible=0;
  for(const engine of [...new Set(data.rows.map(x=>x.engine))]){{
    const group=data.rows.filter(x=>x.engine===engine).filter(x=>{{
      const key=x.engine+'|'+x.voice, st=saved[key]||{{}};
      return (!onlyFav||st.fav)&&(!q||(x.voice+' '+x.label+' '+x.engine).toLocaleLowerCase('vi').includes(q));
    }});
    if(!group.length)continue;visible+=group.length;
    const title=document.createElement('h2');title.textContent=engine+' ('+group.length+')';host.append(title);
    const grid=document.createElement('div');grid.className='grid';host.append(grid);
    for(const x of group){{
      const key=x.engine+'|'+x.voice,st=saved[key]||{{}};
      const card=document.createElement('article');card.className='card';
      const h=document.createElement('h3');h.textContent=x.voice;card.append(h);
      const meta=document.createElement('div');meta.className='meta';meta.textContent=x.label;card.append(meta);
      for(const [kind,label] of [['tu_su','① Tự sự'],['hoi_hop','② Hồi hộp']]){{
        const area=document.createElement('div');area.className='clip';
        const cap=document.createElement('label');cap.textContent=label;area.append(cap);
        const player=document.createElement('audio');player.controls=true;player.preload='none';player.src=x.clips[kind];area.append(player);card.append(area);
      }}
      const choices=document.createElement('div');choices.className='choices';
      const check=document.createElement('input');check.type='checkbox';check.checked=!!st.fav;
      check.onchange=()=>{{saved[key]={{...(saved[key]||{{}}),fav:check.checked}};save();}};
      const fav=document.createElement('label');fav.append(check,document.createTextNode('Chọn giọng này'));choices.append(fav);
      const score=document.createElement('select');score.setAttribute('aria-label','Điểm');
      for(let i=0;i<=5;i++){{let opt=document.createElement('option');opt.value=i;opt.textContent=i?i+'/5':'Chấm điểm';score.append(opt);}}
      score.value=st.score||0;score.onchange=()=>{{saved[key]={{...(saved[key]||{{}}),score:score.value}};save();}};choices.append(score);card.append(choices);
      const note=document.createElement('input');note.type='text';note.className='note';note.placeholder='Ghi chú: tự nhiên, diễn tốt, phát âm...';note.value=st.note||'';
      note.oninput=()=>{{saved[key]={{...(saved[key]||{{}}),note:note.value}};save();}};card.append(note);grid.append(card);
    }}
  }}
  document.getElementById('count').textContent=visible+' giọng';
}}
document.getElementById('search').oninput=render;
document.getElementById('showFav').onclick=()=>{{onlyFav=!onlyFav;document.getElementById('showFav').textContent=onlyFav?'Hiện tất cả':'Chỉ giọng đã chọn';render();}};
document.getElementById('makeReply').onclick=()=>{{
  const lines=data.rows.filter(x=>(saved[x.engine+'|'+x.voice]||{{}}).fav).map(x=>{{
    const st=saved[x.engine+'|'+x.voice];return '- '+x.voice+' ('+x.engine+')'+(st.score?' — '+st.score+'/5':'')+(st.note?' — '+st.note:'');
  }});
  const box=document.getElementById('reply');box.value=lines.length?'Tôi chọn các giọng sau cho truyện ma:\\n'+lines.join('\\n'):'Chưa chọn giọng nào.';box.focus();box.select();
}};
render();
</script></body></html>'''
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(f"Wrote {len(all_rows)} voices to {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
