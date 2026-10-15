#!/usr/bin/env python3
"""Assistant Débat TikTok : préparation de réponses et voix ElevenLabs sur Mac."""
import json, urllib.request, urllib.error, webbrowser, threading, html
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PAGE = """<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Assistant Débat TikTok</title>
<style>body{font-family:system-ui;margin:25px auto;max-width:850px;color:#152033;padding:0 12px;background:#f6f8fa}main{background:white;border-radius:16px;padding:25px;box-shadow:0 3px 15px #ddd}h1{font-size:26px}label{display:block;margin:14px 0 6px;font-weight:600}input,textarea,select{width:100%;box-sizing:border-box;border:1px solid #aaa;border-radius:8px;padding:12px;font:inherit}textarea{min-height:140px}button{padding:12px 16px;border:0;border-radius:9px;background:#204f9a;color:white;margin:8px 5px 5px 0;cursor:pointer}button:disabled{opacity:.5}#status{white-space:pre-wrap;color:#444}audio{width:100%;margin-top:16px}.note{font-size:13px;color:#555}</style>
<main><h1>🎙️ Assistant Débat TikTok</h1><p>Prépare une réponse avec ChatGPT, puis prononce-la avec ta voix ElevenLabs. Le son sort sur le Mac, pas encore directement dans TikTok.</p>
<label>Clé API OpenAI</label><input id="oa" type="password" autocomplete="off" placeholder="sk-...">
<label>Clé API ElevenLabs</label><input id="el" type="password" autocomplete="off">
<label>Identifiant de ta voix ElevenLabs</label><input id="voice" placeholder="Voice ID (voir ElevenLabs)">
<label>Question ou argument de l'interlocuteur</label><textarea id="question" placeholder="Écris ici la question entendue pendant le débat..."></textarea>
<label>Longueur de la réponse</label><select id="length"><option value="court">Courte</option><option value="long">Développée</option></select>
<button onclick="draft(false)">Préparer une réponse</button><button onclick="draft(true)">Répondre maintenant</button>
<label>Réponse modifiable avant diffusion</label><textarea id="answer" placeholder="Le texte proposé apparaîtra ici. Tu peux le modifier."></textarea>
<button onclick="speak()">Lire avec ma voix</button><button onclick="stopAudio()">Arrêter le son</button>
<p id="status" aria-live="polite"></p><audio id="player" controls></audio>
<p class="note">Les clés ne sont pas enregistrées sur disque. Ne communique jamais tes clés API, ni dans TikTok ni dans GitHub. Les appels API sont facturés séparément. Indique aux participants que tu utilises une voix synthétique. Le bouton Arrêter coupe le son local.</p></main>
<script>
let busy=false;
function status(s){document.getElementById('status').textContent=s}
async function api(path, payload){let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});let j=await r.json();if(!r.ok)throw Error(j.error||'Erreur');return j}
async function draft(auto){if(busy)return;busy=true;try{status('Préparation de la réponse…');let j=await api('/draft',{key:oa.value,question:question.value,length:length.value});answer.value=j.text;status('Réponse préparée. Tu peux la modifier.');if(auto)await speak()}catch(e){status(e.message)}finally{busy=false}}
async function speak(){try{status('Création de la voix…');let j=await api('/speak',{key:el.value,voice:voice.value,text:answer.value});stopAudio();player.src='data:audio/mpeg;base64,'+j.audio;await player.play();status('Lecture en cours sur le Mac.')}catch(e){status(e.message)}}
function stopAudio(){player.pause();player.currentTime=0}
</script></html>"""

def call(url,payload,headers):
    data=json.dumps(payload,ensure_ascii=False).encode()
    req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json',**headers})
    try:
        with urllib.request.urlopen(req,timeout=90) as response:return response.read()
    except urllib.error.HTTPError as e:
        raise ValueError('Service API : '+str(e.code)+' '+e.read(300).decode(errors='replace'))
    except urllib.error.URLError as e:raise ValueError('Connexion impossible : '+str(e.reason))

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def output(self,data,code=200,ctype='application/json'):
        b=data.encode() if isinstance(data,str) else data
        self.send_response(code);self.send_header('Content-Type',ctype)
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(b)
    def do_GET(self):
        self.output(PAGE,ctype='text/html; charset=utf-8') if self.path=='/' else self.output('Introuvable',404)
    def do_POST(self):
        try:
            if self.headers.get('Origin','').strip() not in ('','http://127.0.0.1:'+str(self.server.server_port)):raise ValueError('Origine refusée')
            n=int(self.headers.get('Content-Length',0))
            if n<1 or n>16000:raise ValueError('Taille de requête invalide')
            x=json.loads(self.rfile.read(n)); key=x.get('key','').strip()
            if not key:raise ValueError('Clé API requise')
            if self.path=='/draft':
                q=x.get('question','').strip()
                if not q or len(q)>6000:raise ValueError('Question manquante ou trop longue')
                size='80 à 110' if x.get('length')=='court' else '180 à 230'
                p={'model':'gpt-4.1-mini','instructions':'Rédige une réponse orale en français de '+size+' mots pour un débat public. Arguments rigoureux, respectueux, nuancés, sans sources inventées. Retourne uniquement le discours à prononcer.','input':q,'max_output_tokens':800}
                r=json.loads(call('https://api.openai.com/v1/responses',p,{'Authorization':'Bearer '+key}))
                out=' '.join(c.get('text','') for i in r.get('output',[]) for c in i.get('content',[]) if c.get('type')=='output_text')
                if not out:raise ValueError('Aucune réponse générée')
                return self.output(json.dumps({'text':out}))
            if self.path=='/speak':
                import re,base64
                voice=x.get('voice','').strip(); txt=x.get('text','').strip()
                if not re.fullmatch('[a-zA-Z0-9_-]{8,80}',voice):raise ValueError('Identifiant de voix invalide')
                if not txt or len(txt)>4500:raise ValueError('Texte requis (maximum 4500 caractères)')
                audio=call('https://api.elevenlabs.io/v1/text-to-speech/'+voice,{'text':txt,'model_id':'eleven_multilingual_v2'},{'xi-api-key':key,'Accept':'audio/mpeg'})
                return self.output(json.dumps({'audio':base64.b64encode(audio).decode()}))
            raise ValueError('Action inconnue')
        except Exception as e:self.output(json.dumps({'error':str(e)}),400)

server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
url='http://127.0.0.1:'+str(server.server_port)
print('Ouvre '+url+' ; laisse cette fenêtre ouverte.')
threading.Timer(.8,lambda:webbrowser.open(url)).start()
try:server.serve_forever()
except KeyboardInterrupt:pass
