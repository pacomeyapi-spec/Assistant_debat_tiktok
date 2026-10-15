# Assistant Débat TikTok — Mac

Une application locale de démonstration pour rédiger une réponse de débat avec l’API OpenAI puis la lire avec une voix clonée ElevenLabs.

## Installation

1. Téléchargez le dépôt avec **Code → Download ZIP**.
2. Décompressez le dossier sur votre Mac.
3. Ouvrez **Terminal** (Applications → Utilitaires → Terminal).
4. Dans le Terminal, tapez `python3 ` (avec un espace), faites glisser le fichier `app.py` depuis le Finder vers le Terminal, puis appuyez sur Entrée.
5. Si Python 3 n’est pas installé, installez-le depuis https://www.python.org/downloads/macos/.
6. La page de l’application s’ouvre dans le navigateur. Laissez le Terminal ouvert pendant l’utilisation.

## Configuration

Une **clé API OpenAI**, une **clé API ElevenLabs** et l’**identifiant de votre voix ElevenLabs** sont requis. Les abonnements ChatGPT et ElevenLabs ne comprennent pas nécessairement les dépenses API.

- OpenAI : https://platform.openai.com/api-keys
- ElevenLabs : https://elevenlabs.io/app/settings/api-keys

Ne publiez jamais ces clés dans GitHub ni dans les captures d’écran.

## Limites

Il s’agit d’un **prototype local** : les réponses audio jouent sur le Mac. La récupération automatique de l’audio TikTok LIVE et la retransmission vers un iPhone ne sont **pas** intégrées. Informez votre audience de l’usage d’une voix synthétique.
