# Didacode

À partir de fichiers Markdown et de fichiers de code source, Didacode produit un livret PDF avec page de garde, table des matières cliquable, encadrés pédagogiques et coloration syntaxique multilingue : supports de cours, antisèches, corrigés d'exercices.

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

Les polices variables livrées dans `fonts/` sont **incorporées au PDF** : le document a alors le même rendu sur toutes les machines, y compris celles où aucune de ces polices n'est installée. Lorsqu'une famille fournit un véritable italique, deux fichiers suffisent : le fichier droit couvre les graisses normale et grasse, et le fichier italique couvre l'italique et l'italique grasse.

| Rôle | Police conseillée | Licence |
|---|---|---|
| Texte | [EB Garamond](https://fonts.google.com/specimen/EB+Garamond) | SIL OFL 1.1 |
| Texte (alternative) | [Source Serif 4](https://fonts.google.com/specimen/Source+Serif+4) | SIL OFL 1.1 |
| Code | [Roboto Mono](https://fonts.google.com/specimen/Roboto+Mono) | SIL OFL 1.1 |
| Code (alternative) | [Fira Code](https://fonts.google.com/specimen/Fira+Code) | SIL OFL 1.1 |

Fira Code ne fournit pas de fichier italique officiel : son unique fichier variable couvre les graisses normale et grasse, tandis que WeasyPrint incline synthétiquement les passages demandés en italique. Source Serif 4 fournit bien un vrai italique variable.

Les notices d'attribution et les textes complets des licences se trouvent dans `fonts/NOTICE.md` et `fonts/licenses/`. Les polices peuvent être utilisées, incorporées et redistribuées avec le logiciel conformément à la SIL Open Font License 1.1 ; elles ne passent pas sous la licence MIT du code.

Pour utiliser une autre famille, poser les fichiers dans `fonts/`, ajouter son préfixe au dictionnaire `FAMILLES` de `didacode.py`, modifier les variables `--police-texte` / `--police-code` en tête de `styles.css`, puis conserver sa licence et sa notice. Si le dossier est absent ou vide, l'outil le signale et retombe sur les polices du système, avec un rendu potentiellement différent.

Georgia, la police du prototype, n'est volontairement plus utilisée par défaut : elle appartient à Microsoft et ne peut être ni redistribuée ni incorporée dans un PDF.

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

markdown:
  - antiseche.md

code:
  - exercice1.py
  - exercice2.py
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
| `fonts` | Dossier des polices à incorporer (défaut : `fonts/`) |
| `html` | Sauvegarde du HTML intermédiaire (débogage) |
| `cover` | `false` pour supprimer la page de garde |
| `toc` | `false` pour supprimer la table des matières |
| `numbered` | `true` pour numéroter les titres |
| `page_breaks` | Sauts de page automatiques : `section`, `chapter` ou `none` |
| `tags` | `true` pour produire un PDF balisé (accessibilité) |

Une clé inconnue déclenche un avertissement au lieu d'être ignorée en silence. `cover`, `toc`, `numbered` et `tags` n'acceptent que `true` ou `false` : toute autre valeur provoque une erreur, plutôt qu'un réglage inversé sans prévenir.

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
| `fonts/` | Polices OFL incorporées, notices et licences propres |
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

- **Bleu nuit** (#1B2A41) : titres principaux
- **Violet** (#6A1B9A) : fonctions, concepts importants
- **Orange** (#E67E22) : avertissements
- **Jaune doux** (#F4D03F) : rappels pédagogiques
- **Gris** (#777777) : commentaires

### Coloration syntaxique

Le code est coloré par Pygments, selon les règles `.highlight` définies dans `styles.css` :

- mots-clés en bleu gras ;
- chaînes en vert ;
- commentaires en gris italique ;
- fonctions en violet.

Le langage est déduit de l'extension pour les fichiers passés à `-c`, et du mot qui suit les triples accents graves pour les blocs Markdown. Tout identifiant connu de Pygments est accepté, y compris `c++`, `objective-c` ou `shell-session`, ainsi que les clôtures `~~~` et les blocs à attributs. **Un bloc sans langage indiqué est rendu sans coloration** : aucun langage n'est deviné.

Un bloc PHP écrit sans `<?php` n'est pas colorié par Pygments. Les fichiers `.php` annexés avec `-c` sont détectés automatiquement, mais dans un bloc Markdown, il faut écrire la balise ouvrante.

### Mise en page

- Page de garde minimaliste, sans numéro de page
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
| Polices | variables `--police-texte` et `--police-code` — section 2 |
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
