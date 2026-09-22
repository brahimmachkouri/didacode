# Didacode

À partir de fichiers Markdown et de fichiers de code source, Didacode produit un livret PDF avec page de garde, table des matières cliquable, encadrés pédagogiques et coloration syntaxique multilingue : supports de cours, antisèches, corrigés d'exercices, hors ligne.

Ce générateur de PDF utilise **WeasyPrint** et **Pygments**.

## 📦 Installation

### Installation isolée — recommandée

Depuis le dossier du projet, [pipx](https://pipx.pypa.io/) ou [uv](https://docs.astral.sh/uv/) installe Didacode avec ses dépendances et crée directement la commande `didacode` :

```bash
pipx install .
# ou
uv tool install .
```

Installation sans clonage préalable :

```bash
pipx install "git+https://github.com/brahimmachkouri/didacode.git"
```

Vérifier ensuite l'installation :

```bash
didacode --version
didacode --example
```

Dans un environnement virtuel Python classique, utiliser plutôt :

```bash
python -m pip install .
```

Pour contribuer au code, l'installation modifiable évite de réinstaller le paquet après chaque changement :

```bash
python -m pip install --editable .
python -m unittest discover -s tests
```

Le fichier `pyproject.toml` décrit le paquet et ses dépendances. `requirements.txt` reste fourni pour les outils qui l'utilisent encore. La commande historique `python didacode.py` continue également de fonctionner depuis le dépôt.

WeasyPrint s'appuie sur des bibliothèques système, notamment Pango et HarfBuzz, qui ne s'installent pas par pip. Voir les commentaires de `requirements.txt` en cas d'erreur au premier lancement.

### Polices

Les polices livrées dans `fonts/` sont **incorporées au PDF lorsqu'elles sont utilisées** : le document a alors le même rendu sur toutes les machines, y compris celles où aucune de ces polices n'est installée. Source Serif 4, Source Sans 3 et JetBrains Mono sont fournies en fontes variables ; les autres familles utilisent les variantes statiques nécessaires.

| Rôle | Police conseillée | Licence |
|---|---|---|
| Texte | [Source Serif 4](https://fonts.google.com/specimen/Source+Serif+4) | SIL OFL 1.1 |
| Texte (alternative) | [Bitstream Charter](https://practicaltypography.com/charter.html) | Notice Bitstream/X Consortium |
| Replis avec empattements | DejaVu Serif, Liberation Serif | DejaVu/Bitstream Vera, SIL OFL 1.1 |
| Titres et interface | [Fira Sans](https://fonts.google.com/specimen/Fira+Sans) | SIL OFL 1.1 |
| Titres (alternative) | [Source Sans 3](https://fonts.google.com/specimen/Source+Sans+3) | SIL OFL 1.1 |
| Replis sans empattements | DejaVu Sans, Liberation Sans | DejaVu/Bitstream Vera, SIL OFL 1.1 |
| Code | [Fira Mono](https://fonts.google.com/specimen/Fira+Mono) | SIL OFL 1.1 |
| Code (alternative) | [JetBrains Mono](https://www.jetbrains.com/lp/mono/) | SIL OFL 1.1 |

EB Garamond, Roboto Mono et Fira Code restent livrées comme alternatives. Fira Mono et Fira Code ne fournissent pas de fichier italique officiel : WeasyPrint incline synthétiquement les passages demandés en italique. Source Serif 4, Source Sans 3, Fira Sans et Bitstream Charter fournissent de vrais italiques.

Les notices d'attribution et les textes complets des licences se trouvent dans `fonts/NOTICE.md` et `fonts/licenses/`. Les polices peuvent être utilisées, incorporées et redistribuées avec le logiciel conformément à leurs licences propres ; elles ne passent pas sous la licence MIT du code.

#### Choisir les polices dans le YAML

Deux options distinctes contrôlent les polices sans modifier `styles.css` :

| Option | Effet |
|---|---|
| `fonts` | Dossier contenant les fichiers à déclarer avec `@font-face` et à incorporer lorsqu'ils sont utilisés. Par défaut, Didacode emploie son dossier `fonts/` livré avec le paquet. |
| `font_priority` | Surcharge en mémoire l'ordre des familles pour le texte (`serif`), les titres et l'interface (`sans`) et le code (`mono`). Le fichier CSS reste inchangé. |

Chaque rôle de `font_priority` accepte un nom unique ou une liste ordonnée :

```yaml
# Facultatif : chemin relatif au fichier YAML.
# Omettre cette ligne pour employer les fontes livrées avec Didacode.
# fonts: mes-fontes

font_priority:
  serif: DejaVu Serif
  sans:
    - DejaVu Sans
    - Liberation Sans
  mono: JetBrains Mono
```

Les valeurs sont les noms de familles, pas les noms de fichiers. Pour chaque rôle, Didacode essaie dans l'ordre :

1. la première famille indiquée dans `font_priority` ;
2. les familles suivantes, lorsqu'une liste est fournie ;
3. la pile normale définie par `styles.css`.

Une famille n'a pas besoin d'être présente dans le dossier `fonts` : si elle est installée dans le système, WeasyPrint peut l'utiliser et l'incorporer au PDF. Si elle est introuvable, le repli suivant est essayé automatiquement. Le rendu ne sera toutefois reproductible sur une autre machine que si cette police y est aussi incorporée ou installée, et son utilisation reste soumise à sa propre licence.

Pour incorporer une nouvelle famille, poser ses fichiers dans `fonts/`, ajouter son préfixe au dictionnaire `FAMILLES` de `didacode.py`, puis conserver sa licence et sa notice. Si le dossier est absent ou vide, l'outil le signale et utilise les polices disponibles dans le système, avec un rendu potentiellement différent.

La Bitstream Charter livrée ici provient des fontes libres confiées au X Consortium, et non du fichier `Charter.ttc` de macOS. Les autres polices propriétaires du prototype (Georgia, Segoe UI, Helvetica Neue, Menlo et Consolas) ne figurent plus dans les piles : leur présence sur un système n'autorise pas à redistribuer leurs fichiers avec Didacode.

## 🚀 Utilisation rapide

### Voir le rendu

```bash
didacode --example
```

Produit `output/exemple.pdf` à partir de `exemple/exemple.md`, qui illustre chaque élément de mise en page : encadrés, tableaux, blocs de code dans plusieurs langages, images, listes, sauts de page. Le dossier `exemple/` regroupe tout ce qui sert à cette démonstration : le Markdown, ses images dans `assets/`, deux exercices Python et un modèle de configuration.

### Convertir un fichier Markdown

```bash
didacode -m documentation.md -o manuel.pdf
```

### Markdown + code source

```bash
didacode -m doc.md -c script.py -o manuel.pdf
```

### Options complètes

```bash
didacode \
    -m chapitre1.md chapitre2.md \
    -c exercice1.py exercice2.py \
    --title "Manuel Python" \
    --subtitle "Cours et exercices corrigés" \
    --author "Jean Dupont" \
    --institution "IUT Informatique" \
    --output cours_python.pdf \
    --numbered \
    --html debug.html
```

## ⚙️ Fichier de configuration YAML

Pour éviter de retaper une longue commande à chaque génération :

```bash
didacode --config manuel.yaml
```

Exemple de fichier :

```yaml
title: Python
subtitle: Antisèche et corrigé de l'évaluation
author: Sub
institution: IUT
output: manuel.pdf

# Insère un verso vide entre la couverture et la table des matières.
blank_page: true

markdown:
  - antiseche.md

code:
  - exercice1.py
  - exercice2.py

font_priority:
  serif: DejaVu Serif
  sans: DejaVu Sans
  mono: JetBrains Mono
```

Un fichier `exemple/config.exemple.yaml` commenté est livré avec Didacode : le copier sous un autre nom et l'adapter. `didacode --create-examples` copie dans `examples/` les fichiers de démonstration réellement livrés dans `exemple/` (`exemple.md`, `config.exemple.yaml`, les deux exercices et `assets/`).

### Clés reconnues

| Clé | Rôle |
|---|---|
| `title` | Titre du livret (page de garde) |
| `subtitle` | Sous-titre (page de garde) |
| `author` | Auteur |
| `institution` | Établissement |
| `date` | Date affichée (par défaut : date du jour, en français) |
| `output` | Fichier PDF produit |
| `markdown` | Fichier ou liste de fichiers Markdown |
| `code` | Fichier ou liste de fichiers de code à annexer |
| `css` | Feuille de style à utiliser (défaut : `styles.css`) |
| `fonts` | Dossier des fichiers de polices à déclarer et incorporer (défaut : fontes livrées) |
| `font_priority` | Nom ou liste de familles prioritaires pour `serif`, `sans` et `mono` |
| `html` | Sauvegarde du HTML intermédiaire (débogage) |
| `cover` | `false` pour supprimer la page de garde |
| `blank_page` | `true` pour insérer une page blanche après la couverture et avant la table des matières ; ignoré si `cover: false` |
| `toc` | `false` pour supprimer la table des matières |
| `numbered` | `true` pour numéroter les titres |
| `page_breaks` | Sauts de page automatiques : `section`, `chapter` ou `none` |
| `tags` | `true` pour produire un PDF balisé (accessibilité) |

Une clé inconnue déclenche un avertissement au lieu d'être ignorée en silence. `cover`, `blank_page`, `toc`, `numbered` et `tags` n'acceptent que `true` ou `false` : toute autre valeur provoque une erreur, plutôt qu'un réglage inversé sans prévenir.

### Cinq comportements à connaître

- **Les chemins sont relatifs au fichier YAML**, pas au dossier courant. Le fichier de configuration peut donc être rangé à côté du Markdown et la commande lancée depuis n'importe où.
- **La ligne de commande est prioritaire** sur le fichier : `--config manuel.yaml --title "Brouillon"` reprend tout le fichier sauf le titre.
- **Un fichier déclaré mais absent arrête la génération**, avec la liste complète des fichiers manquants. Aucun PDF incomplet n'est produit, et le code de retour est non nul : l'outil est utilisable dans un script ou une chaîne d'intégration.
- **Une sortie sans dossier est rangée dans `output/`**, pour ne pas mélanger les fichiers produits avec les sources. `-o build/pdf/cours.pdf` est respecté tel quel, et les dossiers manquants sont créés.
- **Les deux-points dans une valeur exigent des guillemets**, sinon YAML croit lire une nouvelle clé :
  ```yaml
  title: "Python : les bases"
  ```

## 🔒 Ressources et images

Le projet est confiné à une racine : le dossier du fichier YAML, ou à défaut celui du premier Markdown. L'option `--root` permet de la fixer explicitement.

- Un chemin d'image est résolu **par rapport au Markdown qui la contient**, ce qui permet de répartir les sources dans des sous-dossiers.
- Les assets peuvent être rangés où l'on veut **sous la racine** : `assets/`, `images/`, `chapitre1/figures/`.
- Une image absente, située au-dessus de la racine, ou chargée depuis le réseau arrête la génération. Un document ne dépend donc jamais d'une ressource extérieure, et ne sort jamais silencieusement troué.

## 📁 Fichiers inclus

| Fichier | Description |
|---------|-------------|
| `didacode.py` | Script principal |
| `pyproject.toml` | Métadonnées, dépendances et commande du paquet installable |
| `styles.css` | Feuille de style académique complète |
| `exemple/` | Fichiers de démonstration, utilisés par `--example` et `--create-examples` |
| `exemple/exemple.md` | Document de démonstration |
| `exemple/config.exemple.yaml` | Modèle de configuration à copier et adapter |
| `exemple/exercice1.py`, `exemple/exercice2.py` | Exemples de code annexé |
| `exemple/assets/` | Ressources de la démonstration |
| `fonts/` | Polices OFL à incorporer, notices et licences propres |
| `tests/` | Tests automatisés |
| `CHANGELOG.md` | Journal des versions |
| `requirements.txt` | Dépendances Python |
| `README.md` | Ce fichier |
| `LICENSE` | Licence MIT |

## 🎨 Caractéristiques

### Typographie

- Police serif pour le texte, incorporée au PDF
- Police monospace pour le code, incorporée également
- Interligne confortable (1.45)
- Texte justifié avec césures

### Palette de couleurs

La palette éditoriale vient des variables `:root` de `styles.css` :

| Usage | Trait ou texte | Fond |
|---|---|---|
| Titres, liens et accent général | bleu `#1f4e79` | — |
| Information (`[INFO]`) | bleu `#1f6feb` | bleu pâle `#eef4fd` |
| À retenir (`[IMPORTANT]`) | violet `#6d28d9` | violet pâle `#f4f0fe` |
| Attention (`[WARNING]`) | ocre `#b45309` | crème `#fdf5e7` |
| Rappel (`[REMINDER]`) et correction | vert canard `#0f766e` | vert pâle `#eefaf8` |
| Texte principal | `#1a1a1a` | — |
| Texte secondaire et discret | `#4a4a4a` et `#767676` | — |

Les encadrés se distinguent aussi par leur filet — fin, épais, double ou pointillé — afin de rester identifiables en niveaux de gris.

### Coloration syntaxique

Le code est coloré par Pygments, selon les règles `.highlight` définies dans `styles.css` :

- mots-clés en bleu `#1f4e79`, généralement en gras ;
- chaînes en vert `#1a6b52` ;
- commentaires en gris `#6a737d` et en italique ;
- fonctions et classes en violet `#5a3ba8` ;
- erreurs en rouge `#a03030`, sur fond `#fdecec` lorsqu'un fond est nécessaire.

Le langage est déduit de l'extension pour les fichiers passés à `-c`, et du mot qui suit les triples accents graves pour les blocs Markdown. Tout identifiant connu de Pygments est accepté, y compris `c++`, `objective-c` ou `shell-session`, ainsi que les clôtures `~~~` et les blocs à attributs. **Un bloc sans langage indiqué est rendu sans coloration** : aucun langage n'est deviné.

Un bloc PHP écrit sans `<?php` n'est pas colorié par Pygments. Les fichiers `.php` annexés avec `-c` sont détectés automatiquement, mais dans un bloc Markdown, il faut écrire la balise ouvrante.

### Mise en page

- Page de garde minimaliste, sans numéro de page
- Page blanche facultative après la page de garde, pour les documents reliés
- Table des matières automatique, avec liens et numéros de page
- Identifiants de titres uniques pour tout le document, même quand deux fichiers contiennent le même titre
- Numérotation des pages, filet horizontal sur toute la largeur
- Sauts de page automatiques réglables (voir ci-dessous)
- Contrôle des veuves et orphelines
- Blocs de code jamais coupés

## 📄 Sauts de page

Trois comportements, au choix, avec `page_breaks` dans le YAML ou `--page-breaks` en ligne de commande :

| Valeur | Effet |
|---|---|
| `section` | Chaque titre de niveau 2 (`##`) démarre une page. Défaut, adapté aux livrets découpés en fiches. |
| `chapter` | Seuls les titres de niveau 1 (`#`) démarrent une page. Le document est plus dense. |
| `none` | Aucun saut automatique : seules les lignes `---` en produisent. |

Le tout premier titre du document ne déclenche jamais de saut, pour éviter une page blanche après la table des matières. Dans tous les modes, un titre n'est jamais laissé seul en bas de page.

Le mode `section` combiné aux blocs insécables (encadrés, tableaux, blocs de code) produit parfois des pages creuses : un encadré qui ne tient pas en bas de page bascule entier, et la section suivante démarre de toute façon sur une nouvelle page. Passer en `chapter` est la réponse la plus simple.

## 📃 Page blanche après la page de garde

```bash
didacode -m cours.md --blank-page -o cours.pdf
```

ou, dans le YAML :

```yaml
blank_page: true
```

Une page rigoureusement vide s'intercale alors entre la page de garde et la table des matières : ni en-tête, ni numéro, ni filet. C'est la convention des documents reliés, où la couverture occupe un recto seul et s'ouvre sur un verso vierge.

La page compte dans la pagination, comme au tirage : la table des matières passe en page 3 et ses renvois suivent. Demander cette page sans page de garde n'a pas de sens — le document s'ouvrirait sur du vide : l'outil le signale et ne l'insère pas.

## 📝 Syntaxe Markdown spéciale

### Encadrés pédagogiques

```markdown
> [INFO] Ceci est une information importante.

> [WARNING] Attention à ce point particulier.

> [IMPORTANT] Concept clé à retenir.

> [REMINDER] Rappel d'un élément précédent.
```

Le mot-clé doit ouvrir le paragraphe. Des encadrés consécutifs séparés par une seule ligne vide sont correctement séparés, alors que Markdown les fusionne normalement en une seule citation.

### Saut de page manuel

Une ligne `---` provoque un saut de page (le filet horizontal est masqué). Un `<div class="saut-page"></div>` fait la même chose de façon plus explicite. Attention aux doublons : les titres de niveau 2 changent déjà de page tout seuls.

## 🐍 Utilisation comme module

```python
from didacode import generer_pdf, ErreurGeneration

try:
    chemin = generer_pdf(
        markdown=["cours.md", "annexes.md"],
        code=["exercice1.py"],
        sortie="build/cours.pdf",
        titre="Programmation Python",
        auteur="Prénom Nom",
        institution="IUT Informatique",
        numerote=True,
    )
    print("Produit :", chemin)
except ErreurGeneration as e:
    print("Échec :", e)
```

`generer_pdf()` retourne le chemin du PDF produit et lève `ErreurGeneration` sur tout problème bloquant : fichier absent, ressource hors du projet, échec de rendu. Les classes `DocumentGenerator`, `MarkdownConverter`, `CodeHighlighter` et `PDFGenerator` restent accessibles pour composer un document section par section, y compris à partir de HTML déjà produit (`add_raw_html`).

## 🔧 Réglages fréquents dans `styles.css`

| Réglage | Où |
|---|---|
| Polices prioritaires | clé YAML `font_priority` |
| Couleurs | variables `:root` — section 2 |
| Taille du code | `pre { font-size }` — section 8 |
| Classes de coloration | section 9 |
| Style des encadrés | section 11 |
| Coupure des annexes de code | `.correction pre` — section 14 |
| Marges et format de page | `@page` — section 1 |
| Saut de page par section | règle `h2 { break-before }` — fin du fichier |

## 🏷️ Version

```bash
didacode --version
```

La version se retrouve aussi dans les propriétés de chaque PDF produit, à la ligne « Créateur » : un document retrouvé six mois plus tard indique lui-même avec quelle version il a été fabriqué. Les changements sont notés dans `CHANGELOG.md`.

## ✅ Tests

```bash
python -m unittest discover -s tests
```

Les tests couvrent les cas qui ont posé problème : ancres dupliquées entre plusieurs fichiers, fichiers déclarés mais absents, images hors du projet, booléens YAML ambigus, création des dossiers de sortie, coloration des différents langages.

### Intégration continue et PDF de démonstration

La GitHub Action `.github/workflows/ci.yml` lance les tests sous les versions de Python prises en charge, génère le PDF de démonstration, vérifie qu'il n'incorpore que les familles libres livrées et le conserve comme artefact téléchargeable de chaque exécution.

Lorsqu'un tag de version commençant par `v` est poussé, par exemple :

```bash
git tag v2.3.0
git push origin v2.3.0
```

la même Action crée automatiquement une GitHub Release et y joint `didacode-exemple.pdf`. Le PDF produit n'est donc pas stocké dans l'historique Git.

## 🔍 Débogage

L'option `--html debug.html` sauvegarde le HTML intermédiaire, CSS inclus. Il s'ouvre dans un navigateur et se convertit directement :

```bash
weasyprint debug.html document.pdf
```

## 📄 Licence

MIT — libre d'utilisation, de modification et de redistribution, y compris
à des fins commerciales, à condition de conserver la mention de copyright.
Texte complet dans le fichier `LICENSE`.

Les polices placées dans `fonts/` conservent leur propre licence SIL OFL 1.1. Leurs attributions et textes de licence sont fournis dans ce dossier.

Copyright (c) 2026 Brahim Machkouri
