"""Le son de Simon des Monstres, réglé par Ludiworld : python tests/son.py

Règle de Ludiworld (Julien, 23 novembre 2026) : un jeu ne démarre jamais muet ; le son se règle pour toute la maison,
en trois réglages séparés (musique, bruitages, voix) ; le bouton du jeu change ce réglage.
Ici : les notes des monstres et les petits sons suivent « bruitages », la voix qui lit les phrases suit « voix ».
Pas de musique dans ce jeu.

Le haut-parleur ouvre un petit panneau à deux boutons, « Bruitages » et « Voix » (Julien : « il fait comme ailleurs »).

Vérifie : premier lancement avec le son ; chaque bouton du panneau ne change que son réglage dans le kit, et
« Voix Oui / Non » de l'accueil règle la même voix ; le panneau tient en entier sur un téléphone et une tablette ;
le réglage reste après rechargement ; un message « ludi:son » du launcher est suivi (et le bouton du jeu le lui renvoie) ;
une ancienne sauvegarde avec le son coupé ne rend plus le jeu muet ; sans bruitages, la chanson se montre encore.
Serveur sur le port 7370 (jamais 8000). Navigateur muet, voix du navigateur remplacée par un compteur.
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
PORT = 7370
BASE = f'http://localhost:{PORT}/'
echecs = []

# La voix du navigateur ne parle pas : chaque phrase dite est notée dans window.__dits.
MUET = """
window.__dits = [];
try { window.speechSynthesis.speak = (u) => { window.__dits.push(u.text); }; } catch (e) {}
"""

# Un faux launcher Ludiworld, à la même adresse locale (le kit accepte localhost) : il note les messages du jeu.
LANCEUR = """<!doctype html><meta charset="utf-8"><title>lanceur</title>
<iframe id="jeu" src="index.html" style="width:820px;height:1100px;border:0"></iframe>
<script>
window.__recus = [];
addEventListener('message', (e) => { if (e.data && e.data.type) window.__recus.push(e.data); });
window.envoyer = (m) => document.getElementById('jeu').contentWindow.postMessage(m, '*');
</script>"""


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


def chanter(cible, i=0):
    """Touche un monstre de la chorale (écran d'accueil) et rend les sons joués depuis la dernière fois."""
    cible.evaluate('window.__simon.sons()')
    cible.locator('#choir .singer').nth(i).dispatch_event('pointerdown')
    time.sleep(0.15)
    return cible.evaluate('window.__simon.sons()')


def presse(cible, id_):
    return cible.get_attribute('#' + id_, 'aria-pressed')


def haut_parleur(cible, id_):
    """« on » : le haut-parleur dessiné normal ; « off » : barré."""
    return cible.get_attribute('#' + id_, 'data-son')


def ouvert(cible):
    return cible.evaluate('!document.getElementById("sonPanel").hidden')


def barre_visible(cible, id_):
    return cible.evaluate(f'getComputedStyle(document.querySelector("#{id_} .barre")).display !== "none"')


def dits(cible):
    return cible.evaluate('window.__dits.splice(0)')


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
        nav = pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required', '--mute-audio'])

        def contexte():
            ctx = nav.new_context(viewport={'width': 820, 'height': 1180}, service_workers='block', locale='fr-FR',
                                  reduced_motion='reduce')
            ctx.add_init_script(MUET)
            return ctx

        erreurs = []

        print('Premier lancement, jeu ouvert seul')
        ctx = contexte()
        page = ctx.new_page()
        page.on('pageerror', lambda e: erreurs.append(str(e)))
        page.goto(BASE)
        verifier(pret(page), 'le jeu est prêt')
        son = page.evaluate('Ludi.son()')
        verifier(son == {'musique': True, 'bruitages': True, 'voix': True}, f'le kit : tout allumé au départ ({son})')
        verifier(page.evaluate('window.__simon.son') == son, 'le jeu suit le réglage du kit')
        verifier(haut_parleur(page, 'btnSoundHome') == 'on', 'le haut-parleur n\'est pas barré')
        verifier(presse(page, 'voiceOn') == 'true' and presse(page, 'voiceOff') == 'false', 'Voix : « Oui » est choisi')
        verifier('note' in chanter(page), 'toucher un monstre : sa note se joue')
        dits(page)
        page.click('#voiceOn')
        verifier(dits(page) == ['Coucou !'], 'Voix « Oui » : la voix dit « Coucou ! »')

        print('Le panneau du son')
        verifier(not ouvert(page), 'fermé au départ')
        page.click('#btnSoundHome')
        verifier(ouvert(page), 'le haut-parleur ouvre le panneau')
        verifier(page.get_attribute('#btnSoundHome', 'aria-expanded') == 'true', 'le haut-parleur le dit (aria-expanded)')
        verifier(presse(page, 'sonBruitages') == 'true' and presse(page, 'sonVoix') == 'true', 'Bruitages et Voix sont allumés')
        verifier(page.locator('#sonPanel button').count() == 2, 'deux boutons seulement : pas de musique')
        verifier(barre_visible(page, 'sonBruitages') is False, 'Bruitages allumé : son dessin n\'est pas barré')
        page.click('#sonBruitages')
        son = page.evaluate('Ludi.son()')
        verifier(son == {'musique': True, 'bruitages': False, 'voix': True}, f'« Bruitages » ne coupe que les bruitages ({son})')
        garde = json.loads(page.evaluate('localStorage.getItem("ludi.v1.son")') or 'null')
        verifier(garde == son, 'le kit garde ce réglage sur l\'appareil (ludi.v1.son)')
        verifier(presse(page, 'sonBruitages') == 'false' and barre_visible(page, 'sonBruitages'),
                 'Bruitages coupé : aria-pressed faux et dessin barré')
        verifier(ouvert(page), 'le panneau reste ouvert')
        verifier(haut_parleur(page, 'btnSoundHome') == 'on', 'la voix parle encore : le haut-parleur n\'est pas barré')
        dits(page)
        page.click('#sonVoix')
        son = page.evaluate('Ludi.son()')
        verifier(son == {'musique': True, 'bruitages': False, 'voix': False}, f'« Voix » ne coupe que la voix ({son})')
        verifier(haut_parleur(page, 'btnSoundHome') == 'off', 'les deux coupés : le haut-parleur est barré')
        verifier(presse(page, 'voiceOff') == 'true', 'Voix Oui / Non de l\'accueil montre « Non » (même réglage)')
        page.mouse.click(30, 600)
        verifier(not ouvert(page), 'toucher ailleurs ferme le panneau')
        verifier(chanter(page) == [], 'toucher un monstre : plus de note')
        page.click('#langEn')
        page.click('#langFr')
        verifier(dits(page) == [], 'changer de langue : la voix ne dit rien')
        page.click('#btnSoundHome')
        page.click('#sonVoix')
        son = page.evaluate('Ludi.son()')
        verifier(son == {'musique': True, 'bruitages': False, 'voix': True}, f'« Voix » remet la voix seule ({son})')
        verifier(dits(page) == ['Coucou !'], 'la voix parle même avec les bruitages coupés')
        verifier(haut_parleur(page, 'btnSoundHome') == 'on', 'le haut-parleur n\'est plus barré')
        page.keyboard.press('Escape')
        # Fermer en touchant un monstre de la chorale : le toucher ferme seulement le panneau.
        page.evaluate('window.__simon.sons()')
        page.click('#btnSoundHome')
        page.click('#sonBruitages')
        page.evaluate('window.__simon.sons()')
        boite = page.locator('#choir .singer').nth(2).bounding_box()
        page.mouse.click(boite['x'] + boite['width'] / 2, boite['y'] + boite['height'] / 2)
        time.sleep(0.15)
        verifier(not ouvert(page), 'toucher un monstre quand le panneau est ouvert le ferme')
        verifier('note' not in page.evaluate('window.__simon.sons()'), 'sans faire chanter le monstre en dessous')
        verifier(page.evaluate('Ludi.son()') == {'musique': True, 'bruitages': True, 'voix': True}, 'tout est rallumé')
        verifier('note' in chanter(page), 'la note revient')

        print('Voix Oui / Non de l\'accueil, séparée des bruitages')
        page.click('#voiceOff')
        son = page.evaluate('Ludi.son()')
        verifier(son == {'musique': True, 'bruitages': True, 'voix': False}, f'Voix « Non » ne coupe que la voix ({son})')
        page.click('#btnSoundHome')
        verifier(presse(page, 'sonVoix') == 'false' and presse(page, 'sonBruitages') == 'true',
                 'le panneau montre la même chose')
        page.keyboard.press('Escape')
        verifier(not ouvert(page), 'Échap ferme le panneau')
        verifier('note' in chanter(page), 'les notes jouent toujours')
        dits(page)
        page.click('#langEn')
        page.click('#langFr')
        verifier(dits(page) == [], 'la voix ne dit plus rien')

        print('Après rechargement')
        page.click('#btnSoundHome')
        page.click('#sonBruitages')
        page.reload()
        verifier(pret(page), 'le jeu est prêt')
        son = page.evaluate('window.__simon.son')
        verifier(son == {'musique': True, 'bruitages': False, 'voix': False}, f'le réglage est gardé par le kit ({son})')
        verifier(haut_parleur(page, 'btnSoundHome') == 'off' and presse(page, 'voiceOff') == 'true',
                 'le haut-parleur est barré, Voix montre « Non »')

        print('La chanson sans bruitages se montre encore')
        page.evaluate('window.__simon.setTimeScale(0.2)')
        page.evaluate("""() => {
          window.__allumes = 0;
          new MutationObserver((ms) => ms.forEach((m) => { if (m.target.classList.contains('lit')) window.__allumes++; }))
            .observe(document.getElementById('game'), { attributes: true, attributeFilter: ['class'], subtree: true });
        }""")
        page.evaluate('window.__simon.sons()')
        page.click('#btnSolo')
        if attendre(page, '!document.getElementById("cine").hidden', 1500):
            if page.is_visible('#cine .passer'):
                page.click('#cine .passer')
            page.click('#cine .go')
        verifier(attendre(page, 'window.__simon.stage === "input"', 8000), 'la chanson se joue jusqu\'au tour de l\'enfant')
        verifier(page.evaluate('window.__allumes') >= 1, 'le monstre de la chanson s\'allume')
        verifier(page.evaluate('window.__simon.sons()') == [], 'aucune note jouée')
        verifier(haut_parleur(page, 'btnSoundGame') == 'off', 'le haut-parleur de la partie est barré')
        page.click('#btnSoundGame')
        verifier(ouvert(page), 'il ouvre le panneau pendant la partie')
        page.click('#sonBruitages')
        verifier(haut_parleur(page, 'btnSoundGame') == 'on', 'Bruitages remis : le haut-parleur n\'est plus barré')
        boite = page.locator('#btnSoundGame').bounding_box()
        page.mouse.click(boite['x'] + boite['width'] / 2, boite['y'] + boite['height'] / 2)
        verifier(not ouvert(page), 'toucher encore le haut-parleur ferme le panneau')
        seq = page.evaluate('window.__simon.game.sequence()')
        page.evaluate('window.__simon.sons()')
        page.keyboard.press('12345'[seq[0]])
        time.sleep(0.3)
        s = page.evaluate('window.__simon.sons()')
        verifier('note' in s, f'avec les bruitages, la note du monstre touché se joue ({s})')
        ctx.close()

        print('Le panneau tient sur l\'écran')
        for nom, taille in (('téléphone', {'width': 390, 'height': 844}), ('tablette', {'width': 820, 'height': 1180}),
                            ('tablette en paysage', {'width': 1180, 'height': 820})):
            ctx = contexte()
            page = ctx.new_page()
            page.set_viewport_size(taille)
            page.on('pageerror', lambda e: erreurs.append(str(e)))
            page.goto(BASE)
            pret(page)
            for ecran, bouton in (('accueil', 'btnSoundHome'), ('partie', 'btnSoundGame')):
                if ecran == 'partie':
                    page.evaluate('window.__simon.setTimeScale(0.2)')
                    page.click('#btnSolo')
                    if attendre(page, '!document.getElementById("cine").hidden', 1500):
                        page.click('#cine .go')
                    attendre(page, 'window.__simon.stage === "input"', 8000)
                page.click('#' + bouton)
                time.sleep(0.3)
                b = page.locator('#sonPanel').bounding_box()
                dedans = b and b['x'] >= 0 and b['y'] >= 0 and b['x'] + b['width'] <= taille['width'] and b['y'] + b['height'] <= taille['height']
                verifier(dedans, f'{nom}, {ecran} : le panneau est en entier sur l\'écran ({b})')
                page.keyboard.press('Escape')
            ctx.close()

        print('Une ancienne sauvegarde avec le son coupé')
        ctx = contexte()
        page = ctx.new_page()
        page.on('pageerror', lambda e: erreurs.append(str(e)))
        page.goto(BASE)
        pret(page)
        page.evaluate("""() => {
          localStorage.clear();
          localStorage.setItem('simon-des-monstres-v1', JSON.stringify({ sound: false, voice: false, best: 3, speed: 'slow', lang: 'fr' }));
        }""")
        page.reload()
        verifier(pret(page), 'le jeu est prêt')
        son = page.evaluate('Ludi.son()')
        verifier(son == {'musique': True, 'bruitages': True, 'voix': True}, f'le jeu ne démarre pas muet ({son})')
        verifier(haut_parleur(page, 'btnSoundHome') == 'on' and presse(page, 'voiceOn') == 'true', 'les boutons montrent le son')
        verifier('note' in chanter(page), 'la note se joue')
        verifier(page.evaluate('window.__simon.store.best') == 3 and presse(page, 'spdSlow') == 'true',
                 'le reste de la sauvegarde est gardé (record, vitesse)')
        page.click('#spdNormal')
        vieux = json.loads(page.evaluate('localStorage.getItem("simon-des-monstres-v1")'))
        verifier('sound' not in vieux and 'voice' not in vieux, 'la sauvegarde du jeu ne garde plus le son')
        ctx.close()

        print('Dans Ludiworld')
        ctx = contexte()
        page = ctx.new_page()
        page.on('pageerror', lambda e: erreurs.append(str(e)))
        ctx.route(BASE + '__lanceur.html', lambda r: r.fulfill(status=200, content_type='text/html', body=LANCEUR))
        page.goto(BASE + '__lanceur.html')
        cadre = None
        for _ in range(100):
            cadre = next((f for f in page.frames if f.url.endswith('/index.html')), None)
            if cadre:
                break
            time.sleep(0.05)
        verifier(cadre is not None and pret(cadre), 'le jeu est prêt dans le launcher')
        verifier(attendre(page, 'window.__recus.some((m) => m.type === "ludi:hello" && m.kit === "0.5.0")'),
                 'le jeu dit bonjour au launcher avec le kit 0.5.0')
        verifier(cadre.evaluate('Ludi.inLauncher()'), 'le kit sait qu\'il est dans Ludiworld')
        page.evaluate("envoyer({ type: 'ludi:welcome', player: { name: 'Léa' }, save: null, son: { musique: true, bruitages: true, voix: false } })")
        verifier(attendre(cadre, 'window.__simon.son.voix === false'), 'ludi:welcome : la voix coupée par la maison est suivie')
        verifier(presse(cadre, 'voiceOff') == 'true' and presse(cadre, 'sonVoix') == 'false', 'Voix montre « Non », ici et dans le panneau')
        page.evaluate("envoyer({ type: 'ludi:son', son: { musique: true, bruitages: false, voix: false } })")
        verifier(attendre(cadre, 'window.__simon.son.bruitages === false'), 'ludi:son : les bruitages coupés par la maison sont suivis')
        verifier(haut_parleur(cadre, 'btnSoundHome') == 'off', 'le haut-parleur est barré')
        verifier(chanter(cadre) == [], 'toucher un monstre : pas de note')
        page.evaluate('window.__recus.length = 0')
        cadre.click('#btnSoundHome')
        verifier(ouvert(cadre), 'le haut-parleur ouvre le panneau')
        cadre.click('#sonBruitages')
        verifier(attendre(page, 'window.__recus.some((m) => m.type === "ludi:son")'), '« Bruitages » prévient le launcher')
        recu = page.evaluate('window.__recus.filter((m) => m.type === "ludi:son").pop()')
        verifier(recu and recu.get('game') == 'simon-des-monstres'
                 and recu.get('son') == {'musique': True, 'bruitages': True, 'voix': False},
                 f'avec le nouveau réglage de toute la maison, la voix n\'est pas touchée ({recu and recu.get("son")})')
        page.evaluate('window.__recus.length = 0')
        cadre.click('#sonVoix')
        attendre(page, 'window.__recus.some((m) => m.type === "ludi:son")')
        recu = page.evaluate('window.__recus.filter((m) => m.type === "ludi:son").pop()')
        verifier(recu and recu.get('son') == {'musique': True, 'bruitages': True, 'voix': True},
                 f'« Voix » prévient aussi le launcher ({recu and recu.get("son")})')
        cadre.press('body', 'Escape')
        verifier('note' in chanter(cadre), 'et la note revient')
        page.evaluate('window.__recus.length = 0')
        cadre.click('#voiceOff')
        attendre(page, 'window.__recus.some((m) => m.type === "ludi:son")')
        recu = page.evaluate('window.__recus.filter((m) => m.type === "ludi:son").pop()')
        verifier(recu and recu.get('son') == {'musique': True, 'bruitages': True, 'voix': False},
                 'Voix « Non » de l\'accueil prévient aussi le launcher')
        ctx.close()

        verifier(not erreurs, f'aucune erreur dans la page ({erreurs[:3]})')
        nav.close()
finally:
    serveur.terminate()

print()
if echecs:
    print(f'{len(echecs)} échec(s)')
    sys.exit(1)
print('Tout est bon.')
