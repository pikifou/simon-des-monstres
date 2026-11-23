"""La mémoire de Simon des Monstres confiée à Ludiworld : python tests/sauvegarde.py

Règle de Ludiworld (spec/kit.md) : un jeu qui garde une partie la confie à Ludiworld (Ludi.save) et reprend celle qu'il
lui rend (Ludi.onRestore). Julien, 23 novembre 2026 : Simon le fait aussi, comme les autres jeux.
La mémoire partagée : prénoms, monstres, vitesse, record, victoires à deux, concert vu. La langue reste sur l'appareil.

Vérifie : une mémoire d'avant ce changement est confiée au kit (comme très ancienne) ; dans Ludiworld, une mémoire plus
récente venue d'ailleurs remplace celle de l'appareil (record, prénoms) mais pas sa langue ; un changement dans le jeu
part vers Ludiworld ; ouvert seul, le jeu marche comme avant.
Serveur sur le port 7371 (jamais 8000). Navigateur muet.
"""
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
RACINE = pathlib.Path(__file__).resolve().parent.parent
PORT = 7371
BASE = f'http://localhost:{PORT}/'
CLE = 'simon-des-monstres-v1'
echecs = []

MUET = "try { window.speechSynthesis.speak = () => {}; } catch (e) {}"
LANCEUR = """<!doctype html><meta charset="utf-8"><title>lanceur</title>
<iframe id="jeu" src="index.html" style="width:820px;height:1100px;border:0"></iframe>
<script>
window.__recus = [];
addEventListener('message', (e) => { if (e.data && e.data.type) window.__recus.push(e.data); });
window.envoyer = (m) => document.getElementById('jeu').contentWindow.postMessage(m, '*');
</script>"""
ANCIENNE = {'names': ['Lou', ''], 'avatars': [2, 0], 'speed': 'normal', 'best': 5, 'tally': [1, 0], 'starter': 0, 'lang': 'en', 'concert': False}


def verifier(cond, message):
    print(('  ok  ' if cond else '  ÉCHEC  ') + message)
    if not cond:
        echecs.append(message)


def attendre(cible, expr, attente=5000):
    for _ in range(attente // 50):
        try:
            if cible.evaluate(expr):
                return True
        except Exception:
            pass
        time.sleep(0.05)
    return False


def pret(cible):
    return attendre(cible, '!!(window.__simon && window.Ludi && document.querySelector("#choir .singer"))')


def cadre_du_jeu(page):
    for _ in range(100):
        f = next((f for f in page.frames if f.url.endswith('/index.html')), None)
        if f:
            return f
        time.sleep(0.05)
    return None


serveur = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'], cwd=RACINE,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(50):
    try:
        urllib.request.urlopen(BASE, timeout=1)
        break
    except Exception:
        time.sleep(0.1)
try:
    with sync_playwright() as pw:
        nav = pw.chromium.launch(args=['--mute-audio'])
        erreurs = []

        def contexte(memoire=None):
            ctx = nav.new_context(viewport={'width': 820, 'height': 1180}, service_workers='block', locale='fr-FR')
            ctx.add_init_script(MUET)
            if memoire is not None:
                ctx.add_init_script("if (!sessionStorage.getItem('seme')) { localStorage.setItem(%s, %s); sessionStorage.setItem('seme', '1'); }"
                                    % (json.dumps(CLE), json.dumps(json.dumps(memoire))))
            ctx.route(BASE + '__lanceur.html', lambda r: r.fulfill(status=200, content_type='text/html', body=LANCEUR))
            return ctx

        print('Ouvert seul, avec une mémoire d\'avant ce changement')
        ctx = contexte(ANCIENNE)
        page = ctx.new_page()
        page.on('pageerror', lambda e: erreurs.append(str(e)))
        page.goto(BASE)
        verifier(pret(page), 'le jeu est prêt')
        sv = page.evaluate('Ludi.data().save')
        verifier(sv is not None and sv['at'] == 1 and sv['data']['best'] == 5 and sv['data']['names'] == ['Lou', ''],
                 f'la mémoire est confiée au kit, comme très ancienne ({sv})')
        verifier(sv is not None and 'lang' not in sv['data'], 'la langue n\'en fait pas partie')
        verifier(page.evaluate('window.__simon && document.documentElement.lang') in ('en', 'fr'), 'le jeu marche comme avant')
        ctx.close()

        print('Dans Ludiworld : une mémoire plus récente venue d\'un autre appareil')
        ctx = contexte(ANCIENNE)
        page = ctx.new_page()
        page.on('pageerror', lambda e: erreurs.append(str(e)))
        page.goto(BASE + '__lanceur.html')
        cadre = cadre_du_jeu(page)
        verifier(cadre is not None and pret(cadre), 'le jeu est prêt dans le launcher')
        verifier(attendre(page, 'window.__recus.some((m) => m.type === "ludi:hello")'), 'le jeu dit bonjour au launcher')
        venue = {'names': ['Malo', 'Noé'], 'avatars': [3, 1], 'speed': 'slow', 'best': 12, 'tally': [4, 2], 'starter': 1, 'concert': True}
        page.evaluate("v => envoyer({ type: 'ludi:welcome', player: { name: 'Malo' }, save: { data: v, at: 5000 } })", venue)
        # Le jeu range la mémoire et se recharge : on attend la nouvelle page du jeu.
        ok = attendre(page, f"(() => {{ const f = document.getElementById('jeu').contentWindow; try {{ return JSON.parse(f.localStorage.getItem({json.dumps(CLE)})).best === 12; }} catch (e) {{ return false; }} }})()")
        verifier(ok, 'la mémoire venue d\'ailleurs est rangée sur l\'appareil')
        time.sleep(0.8)
        cadre = cadre_du_jeu(page)
        verifier(cadre is not None and pret(cadre), 'le jeu repart après s\'être rechargé')
        d = cadre.evaluate(f'JSON.parse(localStorage.getItem({json.dumps(CLE)}))')
        verifier(d['names'] == ['Malo', 'Noé'] and d['tally'] == [4, 2] and d['speed'] == 'slow' and d['concert'] is True,
                 f'prénoms, victoires, vitesse et concert sont repris ({d})')
        verifier(d['lang'] == 'en', 'la langue de l\'appareil n\'a pas changé')

        print('Un changement dans le jeu part vers Ludiworld')
        page.evaluate('window.__recus.length = 0')
        cadre.evaluate("document.getElementById('spdNormal').click()")
        verifier(attendre(page, 'window.__recus.some((m) => m.type === "ludi:event" && m.event && m.event.kind === "save" && m.event.data.speed === "normal" && m.event.data.best === 12)'),
                 'la mémoire changée est envoyée au launcher')
        ctx.close()
        verifier(not erreurs, f'aucune erreur dans la page ({erreurs})')
        nav.close()
finally:
    serveur.terminate()

print()
print('ÉCHECS : ' + ', '.join(echecs) if echecs else 'Tout est bon.')
sys.exit(1 if echecs else 0)
