# Simon des Monstres

Un Simon à cinq monstres chanteurs (Do, Ré, Mi, Sol, La) pour tablette, en français et en anglais.
*A five-monster Simon game for tablets, in French and English.*
La chanson grandit d'une note à chaque tour. On peut jouer seul (avec un record) ou à deux, chacun son tour : le premier qui se trompe a perdu.

Une petite histoire : la chorale des monstres prépare un grand concert. En solo, retenir une chanson de 8 notes fait le concert (une courte vidéo, puis une image), et le jeu est « Fini » ; la chanson continue ensuite de grandir comme avant. Les vidéos (`assets/cine/`) ne sont pas gardées hors ligne : sans réseau, le jeu montre directement l'image.

**Jouer :** https://pikifou.github.io/simon-des-monstres/

Sur une tablette Android, ouvrez le lien dans Chrome puis touchez « Installer l'appli » (ou menu ⋮ → « Installer l'application »).
L'appli s'ouvre alors en plein écran et marche sans connexion.

Compatible Ludiworld : la fiche du jeu est `ludi.json` et le kit `ludi.js` (copie de https://pikifou.github.io/ludiworld/kit/ludi.js) remonte au launcher les fins de partie, le record solo, les chansons retenues et le concert (« Fini ») ; ouvert seul, le jeu ne change pas.

Le son suit le réglage de Ludiworld (kit 0.5) : tout est allumé au départ. Les notes des monstres et les petits sons suivent « bruitages », la voix qui lit les phrases suit « voix » ; pas de musique. Le haut-parleur du jeu ouvre un petit panneau à deux boutons, « Bruitages » et « Voix », chacun son réglage ; « Voix Oui / Non » de l'accueil règle la même voix. Dans Ludiworld, ces boutons changent le réglage de toute la maison. Test : `python tests/son.py` (serveur local sur le port 7370).

La mémoire du jeu (prénoms, monstres, vitesse, record, victoires à deux, concert vu) est confiée à Ludiworld (`Ludi.save`, `Ludi.onRestore`) : elle suit l'enfant d'un appareil à l'autre. La langue reste sur l'appareil. Test : `python tests/sauvegarde.py` (port 7371).

Personnages et décors générés avec Higgsfield. Polices : Grandstander et Andika (SIL Open Font License).
