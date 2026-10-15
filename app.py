#!/usr/bin/env python3
"""Assistant Débat TikTok pour macOS. Clés stockées dans le Trousseau macOS."""
import base64
import json
import re
import ssl
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SERVICE = "assistant-debat-tiktok"
try:
    import certifi
    TLS = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    TLS = ssl.create_default_context()

def secret(name):
    if sys.platform != "darwin":
        return ""
    p = subprocess.run(["security", "find-generic-password", "-s", SERVICE, "-a", name, "-w"],
                       capture_output=True, text=True)
    return p.stdout.rstrip("\n") if p.returncode == 0 else ""

def store(name, value):
    if sys.platform != "darwin":
        raise ValueError("Le Trousseau est disponible uniquement sur macOS.")
    if not value:
        return
    p = subprocess.run(["security", "add-generic-password", "-U", "-s", SERVICE,
                        "-a", name, "-w", value], capture_output=True, text=True)
    if p.returncode:
        raise ValueError("Impossible d'enregistrer dans le Trousseau macOS.")

def call(url, body, headers):
    request = urllib.request.Request(
        url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(request, timeout=90, context=TLS) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        detail = e.read(350).decode("utf-8", errors="replace")
        raise ValueError("API : erreur " + str(e.code) + " — " + detail)
    except urllib.error.URLError as e:
        raise ValueError("Connexion impossible : " + str(e.reason))

PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Assistant Débat TikTok</title>
<style>
body{background:#f3f6fa;color:#152033;font:16px system-ui,sans-serif;margin:22px auto;max-width:860px;padding:0 12px}
main{background:white;padding:28px;border-radius:18px;box-shadow:0 3px 15px #ddd}
label{display:block;font-weight:600;margin:16px 0 5px}
input:not([type=checkbox]),textarea,select{width:100%;box-sizing:border-box;border:1px solid #aaa;border-radius:8px;padding:12px;font:inherit}
textarea{min-height:130px}button{background:#23519a;color:white;border:0;border-radius:9px;padding:12px;margin:10px 8px 5px 0;cursor:pointer}
#status{white-space:pre-wrap}audio{width:100%;margin-top:14px}.note{color:#555;font-size:13px}
</style></head><body><main>
<h1>🎙️ Assistant Débat TikTok</h1>
<p>Des réponses argumentées, puis leur lecture avec ta voix ElevenLabs. Le son sort sur le Mac, pas encore directement dans TikTok.</p>
<h3>Configuration sécurisée</h3>
<p class="note">Enregistre une fois tes clés dans le Trousseau sécurisé de macOS. Laisse les champs vides ensuite : les clés enregistrées seront utilisées automatiquement.</p>
<label>Clé API OpenAI</label><input id="oa" type="password" autocomplete="off" placeholder="À renseigner pour enregistrer ou remplacer">
<label>Clé API ElevenLabs</label><input id="el" type="password" autocomplete="off" placeholder="À renseigner pour enregistrer ou remplacer">
<label>Identifiant de voix ElevenLabs</label><input id="voice" autocomplete="off" placeholder="Voice ID">
<button onclick="save()">Enregistrer la configuration sur ce Mac</button>
<p id="saved" class="note"></p>
<label>Mes questions enregistrées</label>
<select id="savedQuestions" onchange="loadQuestion()"><option value="">— Choisir une question enregistrée —</option></select>
<button onclick="saveQuestion()">Enregistrer / mettre à jour la question</button>
<button onclick="newQuestion()">Nouvelle question</button>
<button onclick="deleteQuestion()">Supprimer la question sélectionnée</button>
<p class="note">Les questions sont conservées localement dans ce navigateur sur ton Mac, et peuvent être modifiées puis réenregistrées. Elles ne contiennent pas tes clés API.</p>
<label>Question ou argument de l'interlocuteur</label>
<textarea id="question" placeholder="Écris ici la question entendue pendant le débat..."></textarea>
<label>Longueur de la réponse</label><select id="length"><option value="court">Courte</option><option value="long">Développée</option></select>
<label style="font-weight:400"><input type="checkbox" id="sources"> Réponse avec références (facultatif)</label>
<button onclick="draft(false)">Préparer une réponse</button><button onclick="draft(true)">Répondre maintenant</button>
<label>Réponse modifiable avant diffusion</label>
<textarea id="answer" placeholder="Le texte proposé apparaîtra ici ; tu peux le modifier."></textarea>
<button onclick="speak()">Lire avec ma voix</button><button onclick="stopAudio()">Arrêter le son</button>
<p id="status" role="status"></p><audio id="player" controls></audio>
<p class="note">Les clés ne sont jamais publiées sur GitHub. Les appels API peuvent être facturés. Vérifie les références avant de les citer en public et informe les participants qu'une voix synthétique intervient.</p>
</main><script>
const byId=id=>document.getElementById(id);
let busy=false;
const QUESTIONS_KEY='assistantDebatTikTokQuestionsV1';
function questions(){try{const x=JSON.parse(localStorage.getItem(QUESTIONS_KEY)||'[]');return Array.isArray(x)?x:[]}catch(e){return []}}
function refreshQuestions(selected=''){
  const select=byId('savedQuestions');
  select.replaceChildren(new Option('— Choisir une question enregistrée —',''));
  questions().forEach(q=>select.add(new Option(q.text.slice(0,105),q.id)));
  select.value=selected;
}
function loadQuestion(){
  const selected=questions().find(q=>q.id===byId('savedQuestions').value);
  if(selected){byId('question').value=selected.text;status('Question chargée. Tu peux la modifier avant de générer la réponse.')}
}
function newQuestion(){byId('savedQuestions').value='';byId('question').value='';byId('question').focus();status('Nouvelle question prête à saisir.')}
function saveQuestion(){
  const value=byId('question').value.trim();
  if(!value){status('Écris d’abord une question à enregistrer.');return}
  if(value.length>6000){status('La question est trop longue.');return}
  const list=questions(),id=byId('savedQuestions').value;
  const index=list.findIndex(q=>q.id===id);
  const selected=index>=0?id:String(Date.now())+'-'+Math.random().toString(36).slice(2);
  if(index>=0)list[index].text=value;else list.push({id:selected,text:value});
  try{localStorage.setItem(QUESTIONS_KEY,JSON.stringify(list));refreshQuestions(selected);status('Question enregistrée sur ce Mac.')}
  catch(e){status('Enregistrement impossible : stockage du navigateur indisponible.')}
}
function deleteQuestion(){
  const id=byId('savedQuestions').value;
  if(!id){status('Sélectionne une question enregistrée à supprimer.');return}
  try{localStorage.setItem(QUESTIONS_KEY,JSON.stringify(questions().filter(q=>q.id!==id)));
    refreshQuestions();byId('question').value='';status('Question supprimée.')}
  catch(e){status('Suppression impossible.')}
}
refreshQuestions();
function status(msg){byId('status').textContent=msg}
async function api(path,data){
  const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const j=await r.json();
  if(!r.ok)throw Error(j.error||'Erreur');
  return j;
}
async function load(){
  try{
    const r=await fetch('/config');
    const j=await r.json();
    byId('voice').value=j.voice||'';
    byId('saved').textContent=j.saved?'Clés API enregistrées dans le Trousseau macOS.':'Clés API à enregistrer.';
  }catch(e){status(e.message)}
}
async function save(){
  try{
    const j=await api('/save',{openai:byId('oa').value,elevenlabs:byId('el').value,voice:byId('voice').value});
    byId('oa').value='';byId('el').value='';
    byId('saved').textContent=j.message;
  }catch(e){status(e.message)}
}
async function draft(auto){
  if(busy)return;busy=true;
  try{
    status('Préparation de la réponse…');
    const j=await api('/draft',{key:byId('oa').value,question:byId('question').value,
      length:byId('length').value,sources:byId('sources').checked});
    byId('answer').value=j.text;
    status('Réponse prête. Tu peux la modifier avant la lecture.');
    if(auto)await speak();
  }catch(e){status(e.message)}finally{busy=false}
}
async function speak(){
  try{
    status('Génération de la voix…');
    const j=await api('/speak',{key:byId('el').value,voice:byId('voice').value,text:byId('answer').value});
    stopAudio();
    byId('player').src='data:audio/mpeg;base64,'+j.audio;
    await byId('player').play();
    status('Lecture en cours sur le Mac.');
  }catch(e){status(e.message)}
}
function stopAudio(){byId('player').pause();byId('player').currentTime=0}
load();
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def output(self, body, code=200, kind="application/json"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/":
            return self.output(PAGE, kind="text/html; charset=utf-8")
        if self.path == "/config":
            return self.output(json.dumps({
                "saved": bool(secret("openai") and secret("elevenlabs")),
                "voice": secret("voice")}))
        return self.output("Introuvable", 404)

    def do_POST(self):
        try:
            origin = self.headers.get("Origin", "")
            if origin not in ("", "http://127.0.0.1:" + str(self.server.server_port)):
                raise ValueError("Origine refusée.")
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 18000:
                raise ValueError("Taille de requête invalide.")
            x = json.loads(self.rfile.read(length))
            if self.path == "/save":
                openai = str(x.get("openai", "")).strip()
                elevenlabs = str(x.get("elevenlabs", "")).strip()
                voice = str(x.get("voice", "")).strip()
                if not (openai or secret("openai")) or not (elevenlabs or secret("elevenlabs")):
                    raise ValueError("Saisis les deux clés API pour le premier enregistrement.")
                if not (voice or secret("voice")):
                    raise ValueError("Identifiant de voix requis.")
                if voice and not re.fullmatch(r"[a-zA-Z0-9_-]{8,80}", voice):
                    raise ValueError("Identifiant de voix invalide.")
                store("openai", openai)
                store("elevenlabs", elevenlabs)
                store("voice", voice)
                return self.output(json.dumps({"message": "Configuration conservée dans le Trousseau macOS."}))
            if self.path == "/draft":
                key = str(x.get("key") or "").strip() or secret("openai")
                if not key:
                    raise ValueError("Clé OpenAI absente.")
                question = str(x.get("question") or "").strip()
                if not question or len(question) > 6000:
                    raise ValueError("Question absente ou trop longue.")
                words = "80 à 110" if x.get("length") == "court" else "180 à 230"
                instructions = (
                    "Tu es un débatteur oral défendant la thèse que Dieu existe. "
                    "Tu réponds DIRECTEMENT à l'argument ou à la question qui vient d'être posé, "
                    "comme si ton contradicteur était devant toi. "
                    "Ne rédige ni exposé scolaire, ni panorama neutre des opinions, "
                    "ni introduction du genre 'cette question soulève un grand mystère'. "
                    "Commence par une prise de position claire répondant à l'objection. "
                    "Identifie le point faible ou le présupposé précis de l'argument adverse, "
                    "puis donne un raisonnement concret et un exemple lorsque pertinent. "
                    "Termine par une conclusion brève ou une question pertinente au contradicteur. "
                    "Parle à la première personne, adresse-toi éventuellement à 'vous', "
                    "avec un ton ferme, naturel et respectueux, sans mépris. "
                    "Défends au mieux le théisme sans transformer arguments discutables en certitudes "
                    "et sans caricaturer l'athéisme. Réponds uniquement en français avec " + words +
                    " mots environ, sans titres ni listes, comme dans un débat TikTok en direct. "
                    "Si l'objection manque de précision, réponds à sa version la plus plausible. "
                    "Aucune source inventée."
                )
                if x.get("sources") is True:
                    instructions += (
                        " Ajoute après la réponse une courte section Références avec seulement des "
                        "sources dont tu connais avec certitude l'auteur, le titre et le passage "
                        "ou chapitre exact. Si incertain, omets la référence. "
                        "Ne prétends pas avoir fait une vérification en ligne.")
                payload = {"model": "gpt-4.1-mini", "instructions": instructions,
                           "input": question, "max_output_tokens": 1100}
                data = json.loads(call("https://api.openai.com/v1/responses", payload,
                                       {"Authorization": "Bearer " + key}))
                text = " ".join(c.get("text", "") for item in data.get("output", [])
                                for c in item.get("content", []) if c.get("type") == "output_text")
                if not text:
                    raise ValueError("Aucune réponse générée.")
                return self.output(json.dumps({"text": text}, ensure_ascii=False))
            if self.path == "/speak":
                key = str(x.get("key") or "").strip() or secret("elevenlabs")
                voice = str(x.get("voice") or "").strip() or secret("voice")
                spoken = str(x.get("text") or "").strip()
                if not key:
                    raise ValueError("Clé ElevenLabs absente.")
                if not re.fullmatch(r"[a-zA-Z0-9_-]{8,80}", voice):
                    raise ValueError("Identifiant de voix invalide.")
                if not spoken or len(spoken) > 4500:
                    raise ValueError("Texte requis (maximum 4500 caractères).")
                audio = call("https://api.elevenlabs.io/v1/text-to-speech/" + voice,
                             {"text": spoken, "model_id": "eleven_multilingual_v2"},
                             {"xi-api-key": key, "Accept": "audio/mpeg"})
                return self.output(json.dumps({"audio": base64.b64encode(audio).decode("ascii")}))
            raise ValueError("Action inconnue.")
        except Exception as e:
            self.output(json.dumps({"error": str(e)}, ensure_ascii=False), 400)

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = "http://127.0.0.1:" + str(server.server_port)
    print("Ouvre " + url + " ; laisse le Terminal ouvert.")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
