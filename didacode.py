#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Didacode — didactique appliquée au code.

Générateur de PDF pédagogiques, à partir de fichiers Markdown et de fichiers de
code source annexés : page de garde, table des matières, encadrés pédagogiques
et coloration syntaxique multilingue, en qualité éditoriale.

Moteur : WeasyPrint + Pygments + Markdown.

Ligne de commande
-----------------
    python didacode.py --config manuel.yaml
    python didacode.py -m cours.md -c exercice1.py -o cours.pdf

Utilisation comme module
------------------------
    from didacode import generer_pdf

    generer_pdf(
        markdown=["cours.md"],
        code=["exercice1.py"],
        sortie="build/cours.pdf",
        titre="Programmation Python",
        auteur="Prénom Nom",
    )

La fonction lève ErreurGeneration en cas de problème : fichier manquant,
ressource hors du dossier du projet, échec de rendu.

Confinement des ressources
--------------------------
Toutes les images et ressources référencées doivent se trouver sous la racine
du projet (le dossier du fichier de configuration, ou à défaut celui du premier
Markdown). Rien n'est chargé depuis le réseau ni au-dessus de cette racine.

Copyright (c) 2026 Brahim Machkouri — licence MIT.
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import unquote, urlparse

# Version de l'outil. Se consulte avec « python didacode.py --version » et
# se retrouve dans les propriétés de chaque PDF produit, à la ligne Créateur.
# Convention : MAJEUR.MINEUR.CORRECTIF — le majeur change quand un document
# existant ne se rend plus à l'identique. Chaque évolution est notée dans
# CHANGELOG.md.
__version__ = "2.3.0"

__all__ = [
    "ErreurGeneration",
    "Config",
    "CodeHighlighter",
    "MarkdownConverter",
    "DocumentGenerator",
    "PDFGenerator",
    "RegistreAncres",
    "RessourceRefusee",
    "generer_pdf",
    "__version__",
]

try:
    from weasyprint import HTML
    from weasyprint.text.fonts import FontConfiguration
except ImportError:  # pragma: no cover
    print("❌ WeasyPrint non installé. Exécutez : pip install weasyprint")
    sys.exit(1)

# WeasyPrint 70 remplace le chargeur de ressources par une classe. Les deux
# formes sont gérées pour rester compatible avec les versions empaquetées par
# les distributions.
try:
    from weasyprint.urls import URLFetcher as _ChargeurBase, FatalURLFetchingError
    _API_CHARGEUR = "classe"
except ImportError:  # pragma: no cover
    from weasyprint import default_url_fetcher as _chargeur_defaut

    class FatalURLFetchingError(BaseException):
        """Équivalent local pour les versions antérieures à WeasyPrint 70."""

    _ChargeurBase = object
    _API_CHARGEUR = "fonction"

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import HtmlFormatter
    from pygments.util import ClassNotFound
except ImportError:  # pragma: no cover
    print("❌ Pygments non installé. Exécutez : pip install pygments")
    sys.exit(1)

try:
    import markdown
except ImportError:  # pragma: no cover
    print("❌ Markdown non installé. Exécutez : pip install markdown")
    sys.exit(1)

# PyYAML n'est nécessaire que pour l'option --config
try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


class ErreurGeneration(Exception):
    """Erreur bloquante : le PDF ne doit pas être produit."""


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Configuration du générateur PDF."""

    # Métadonnées du document
    TITLE = "Manuel de Programmation Python"
    SUBTITLE = ""
    AUTHOR = "Auteur"
    INSTITUTION = "Institution"
    MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
               "août", "septembre", "octobre", "novembre", "décembre"]
    _aujourdhui = datetime.now()
    DATE = f"{_aujourdhui.day} {MOIS_FR[_aujourdhui.month - 1]} {_aujourdhui.year}"

    # Signature de l'outil, inscrite dans les métadonnées du PDF
    DESIGNER = "Brahim Machkouri"
    GENERATOR = f"Didacode {__version__}"

    # Chemins
    CSS_FILE = "styles.css"
    FONTS_DIR = "fonts"
    # Dossier utilisé quand le nom de sortie ne comporte aucun répertoire
    SORTIE_PAR_DEFAUT = "output"

    # Racine autorisée pour les ressources (images, CSS). Renseignée au
    # lancement : dossier du YAML, ou à défaut celui du premier Markdown.
    RACINE: Optional[Path] = None

    # Options de génération
    GENERATE_TOC = True
    TOC_DEPTH = 3
    NUMBERED_CHAPTERS = False
    INCLUDE_COVER = True
    # Sauts de page automatiques : 'section' (chaque ##), 'chapter' (chaque #)
    # ou 'none' (uniquement les --- explicites).
    PAGE_BREAKS = 'section'
    PDF_TAGS = False


# =============================================================================
# UTILITAIRES
# =============================================================================

def read_file(filepath, encoding: str = "utf-8") -> str:
    """Lit un fichier texte. Lève ErreurGeneration s'il est introuvable."""
    chemin = Path(filepath)
    try:
        return chemin.read_text(encoding=encoding)
    except FileNotFoundError:
        raise ErreurGeneration(f"Fichier introuvable : {chemin}")
    except UnicodeDecodeError:
        return chemin.read_text(encoding="latin-1")


def detect_language(filepath) -> str:
    """Détecte le langage de programmation à partir de l'extension."""
    ext_map = {
        '.py': 'python', '.pyw': 'python',
        '.js': 'javascript', '.mjs': 'javascript', '.ts': 'typescript',
        '.java': 'java', '.kt': 'kotlin', '.kts': 'kotlin',
        '.c': 'c', '.h': 'c',
        '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp', '.hh': 'cpp',
        '.cs': 'csharp', '.rb': 'ruby', '.go': 'go', '.rs': 'rust',
        '.php': 'php', '.sql': 'sql',
        '.s': 'gas', '.S': 'gas', '.asm': 'nasm', '.nasm': 'nasm',
        '.html': 'html', '.css': 'css', '.json': 'json',
        '.yaml': 'yaml', '.yml': 'yaml', '.xml': 'xml', '.toml': 'toml',
        '.sh': 'bash', '.bash': 'bash', '.zsh': 'bash',
        '.md': 'markdown', '.txt': 'text',
    }
    return ext_map.get(Path(filepath).suffix.lower(), 'text')


def decouper_code(code: str, lignes_mini: int = 6) -> List[str]:
    """
    Découpe un fichier source en blocs logiques.

    Un fichier plus long qu'une page finit forcément coupé. Plutôt que de
    laisser la coupure tomber au milieu d'une fonction, on découpe le code
    aux frontières naturelles : toute ligne non indentée précédée d'une
    ligne vide (un `def`, une `class`, une constante). Chaque bloc est
    ensuite rendu insécable, si bien que les sauts de page ne peuvent plus
    tomber qu'entre deux définitions.

    lignes_mini évite de produire une multitude de blocs minuscules.
    """
    lignes = code.splitlines()
    blocs: List[str] = []
    courant: List[str] = []

    for numero, ligne in enumerate(lignes):
        nouvelle_definition = (
            ligne.strip()                        # ligne non vide
            and not ligne[0].isspace()           # au premier niveau
            and numero > 0
            and not lignes[numero - 1].strip()   # précédée d'une ligne vide
        )
        # Ne pas couper à l'intérieur d'une chaîne sur plusieurs lignes
        chaine_ouverte = '\n'.join(courant).count('"""') % 2 != 0

        if nouvelle_definition and len(courant) >= lignes_mini and not chaine_ouverte:
            blocs.append('\n'.join(courant).strip('\n'))
            courant = []

        courant.append(ligne)

    if courant:
        blocs.append('\n'.join(courant).strip('\n'))

    return [bloc for bloc in blocs if bloc.strip()]


def slugify(text: str) -> str:
    """Transforme un titre en identifiant utilisable comme ancre HTML."""
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[\s_-]+', '-', slug).strip('-')
    return slug or 'section'


def escape_html(text: str) -> str:
    """Échappe les caractères spéciaux HTML."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


def sous_racine(chemin: Path, racine: Path) -> bool:
    """Indique si `chemin` se trouve dans `racine`, liens symboliques résolus."""
    try:
        chemin.resolve().relative_to(racine.resolve())
        return True
    except ValueError:
        return False


def preparer_dossier(chemin: Path) -> Path:
    """Crée le dossier parent d'un fichier de sortie. Vérifie qu'il est écrivable."""
    chemin = Path(chemin).expanduser()
    if chemin.is_dir():
        raise ErreurGeneration(
            f"La sortie « {chemin} » est un dossier existant : indiquez un nom de fichier."
        )
    parent = chemin.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ErreurGeneration(f"Impossible de créer le dossier {parent} : {e}")
    return chemin


def chemin_sortie(valeur, dossier_base: Path, defaut: str = Config.SORTIE_PAR_DEFAUT) -> Path:
    """
    Transforme un nom de sortie en chemin absolu.

    Un nom sans dossier (« manuel.pdf ») est rangé dans `output/` pour ne pas
    mélanger les fichiers produits avec les sources du projet.
    """
    p = Path(valeur).expanduser()
    if not p.is_absolute():
        if p.parent == Path('.'):
            p = Path(defaut) / p
        p = dossier_base / p
    return p


# =============================================================================
# CONFINEMENT DES RESSOURCES
# =============================================================================

BALISE_IMG = re.compile(r'(<img\b[^>]*?\bsrc\s*=\s*)(["\'])(.*?)\2', re.IGNORECASE)
SCHEMA_URL = re.compile(r'^(?:[a-z][a-z0-9+.\-]*:|//)', re.IGNORECASE)


def resoudre_ressources(html: str, dossier_source: Path, racine: Path,
                        erreurs: List[str], source: str = "") -> str:
    """
    Rend absolus les chemins d'images d'un fragment HTML et vérifie le confinement.

    Les chemins relatifs sont résolus par rapport au dossier du Markdown qui les
    contient, ce qui permet de répartir les sources dans des sous-dossiers. Tout
    ce qui sort de la racine du projet, ou qui vient du réseau, est refusé.
    """
    def traiter(match: "re.Match") -> str:
        src = unescape(match.group(3)).strip()
        if not src:
            return match.group(0)

        if SCHEMA_URL.match(src):
            if src.lower().startswith('data:'):
                return match.group(0)          # image incorporée : rien à résoudre
            erreurs.append(f"{source}ressource externe refusée : {src}")
            return match.group(0)

        cible = Path(src)
        cible = (cible if cible.is_absolute() else (dossier_source / cible)).resolve()

        if not sous_racine(cible, racine):
            erreurs.append(
                f"{source}ressource hors du projet : {src} "
                f"(racine autorisée : {racine})"
            )
            return match.group(0)

        if not cible.exists():
            erreurs.append(f"{source}image introuvable : {src} (attendue : {cible})")
            return match.group(0)

        return f'{match.group(1)}{match.group(2)}{cible.as_uri()}{match.group(2)}'

    return BALISE_IMG.sub(traiter, html)


class RessourceRefusee(FatalURLFetchingError):
    """
    Ressource hors du projet demandée pendant le rendu.

    Hérite de l'exception fatale de WeasyPrint : sans cela, le refus serait
    avalé et le PDF sortirait silencieusement sans l'image.
    """


def verifier_url(url: str, racines: Sequence[Path]) -> None:
    """Refuse tout ce qui n'est pas un fichier local rangé sous une des racines."""
    if url.lower().startswith('data:'):
        return

    if not url.lower().startswith('file:'):
        raise RessourceRefusee(
            f"chargement réseau refusé : {url} — les ressources doivent être "
            f"locales et rangées dans le projet"
        )

    chemin = Path(unquote(urlparse(url.split('?')[0]).path))
    if not any(sous_racine(chemin, racine) for racine in racines):
        raise RessourceRefusee(
            f"ressource hors du projet : {chemin} — racines autorisées : "
            + ", ".join(str(r) for r in racines)
        )
    if not chemin.exists():
        raise RessourceRefusee(f"ressource introuvable : {chemin}")


def creer_url_fetcher(racines: Sequence[Path]):
    """
    Construit le chargeur de ressources passé à WeasyPrint.

    Dernier rempart : même si une URL échappe à la réécriture (CSS, SVG imbriqué,
    HTML brut), elle ne sera chargée que si elle pointe sous l'une des racines.
    """
    racines_resolues = [Path(r).resolve() for r in racines]

    if _API_CHARGEUR == "classe":
        class ChargeurConfine(_ChargeurBase):
            def __init__(self):
                super().__init__(allowed_protocols={'file', 'data'})

            def fetch(self, url, headers=None):
                verifier_url(url, racines_resolues)
                return super().fetch(url, headers)

        return ChargeurConfine()

    def chargeur(url: str):  # pragma: no cover - WeasyPrint < 70
        verifier_url(url, racines_resolues)
        return _chargeur_defaut(url)

    return chargeur


# =============================================================================
# POLICES EMBARQUÉES
# =============================================================================

# Familles reconnues dans le dossier fonts/. Chaque famille trouvée est
# incorporée au PDF, ce qui garantit un rendu identique partout.
# Les noms correspondent aux archives distribuées par Google Fonts.
FAMILLES = {
    "EB Garamond": "EBGaramond",
    "Source Serif 4": "SourceSerif4",
    "Charis SIL": "CharisSIL",
    "Roboto Mono": "RobotoMono",
    "Fira Code": "FiraCode",
    "JetBrains Mono": "JetBrainsMono",
}

# Noms de fichiers acceptés, dans l'ordre de préférence. {p} est le préfixe de
# la famille. Les formes correspondent aux archives de fonts.google.com
# (statique ou variable, avec axes wght et éventuellement opsz) et au dépôt
# google/fonts (notation entre crochets).
VARIANTES = [
    (("{p}-VariableFont_wght", "{p}-VariableFont_opsz,wght",
      "{p}[wght]", "{p}[opsz,wght]", "{p}-Regular"),
     "400 700", "normal"),
    (("{p}-Bold",), "700", "normal"),
    (("{p}-Italic-VariableFont_wght", "{p}-Italic-VariableFont_opsz,wght",
      "{p}-Italic[wght]", "{p}-Italic[opsz,wght]", "{p}-Italic"),
     "400 700", "italic"),
    (("{p}-BoldItalic",), "700", "italic"),
]

EXTENSIONS_POLICES = (".woff2", ".ttf", ".otf")


def generer_font_faces(dossier: Path) -> Tuple[str, List[str]]:
    """
    Produit les règles @font-face pour les polices présentes dans `dossier`.

    Retourne le CSS et la liste des familles effectivement trouvées. Un dossier
    vide n'est pas une erreur : la feuille de style retombe alors sur les polices
    du système (DejaVu sous Linux).
    """
    if not dossier.is_dir():
        return "", []

    regles: List[str] = []
    trouvees: List[str] = []

    for famille, prefixe in FAMILLES.items():
        variantes_famille = []
        for motifs, poids, style in VARIANTES:
            fichier = None
            for motif in motifs:
                for ext in EXTENSIONS_POLICES:
                    candidat = dossier / (motif.format(p=prefixe) + ext)
                    if candidat.exists():
                        fichier = candidat
                        break
                if fichier:
                    break
            if not fichier:
                continue
            variantes_famille.append(
                "@font-face {\n"
                f"    font-family: \"{famille}\";\n"
                f"    src: url(\"{fichier.resolve().as_uri()}\");\n"
                f"    font-weight: {poids};\n"
                f"    font-style: {style};\n"
                "}"
            )
        if variantes_famille:
            trouvees.append(famille)
            regles.extend(variantes_famille)

    return "\n".join(regles), trouvees


# =============================================================================
# ANCRES ET TITRES
# =============================================================================

BALISE_TITRE = re.compile(r'<h([1-6])([^>]*)>(.*?)</h\1>', re.DOTALL | re.IGNORECASE)
ATTR_ID = re.compile(r'\bid\s*=\s*(["\'])(.*?)\1', re.IGNORECASE)
ATTR_CLASS = re.compile(r'\bclass\s*=\s*(["\'])(.*?)\1', re.IGNORECASE)


class RegistreAncres:
    """
    Attribue des identifiants uniques pour l'ensemble du document.

    Python-Markdown ne garantit l'unicité qu'à l'intérieur d'un fichier : deux
    Markdown contenant « ## Installation » produisent le même id, et le sommaire
    pointe alors toujours sur le premier. Le registre est partagé par toutes les
    sections, y compris les annexes de code.
    """

    def __init__(self):
        self.utilisees = set()

    def unique(self, base: str) -> str:
        base = slugify(base) if base else 'section'
        if base not in self.utilisees:
            self.utilisees.add(base)
            return base
        numero = 2
        while f"{base}-{numero}" in self.utilisees:
            numero += 1
        ancre = f"{base}-{numero}"
        self.utilisees.add(ancre)
        return ancre


def _ajouter_classe(attributs: str, classe: str) -> str:
    """Ajoute une classe CSS à une chaîne d'attributs HTML."""
    correspondance = ATTR_CLASS.search(attributs)
    if correspondance:
        valeurs = correspondance.group(2).split()
        if classe not in valeurs:
            valeurs.append(classe)
        return ATTR_CLASS.sub(f'class="{" ".join(valeurs)}"', attributs, count=1)
    return f'{attributs.rstrip()} class="{classe}"'


def normaliser_titres(html: str, registre: RegistreAncres, entrees: List[Dict],
                      numeroter: bool = False, profondeur: int = 3) -> str:
    """
    Garantit que chaque titre porte un identifiant unique, et collecte le sommaire.

    Cette passe a lieu sur le HTML, jamais sur le Markdown : les sources restent
    dépouillées, sans ancres écrites à la main. Elle règle du même coup le cas des
    titres sans identifiant (HTML brut, sections de code), qui produisaient
    auparavant des liens cassés dans la table des matières.
    """
    def traiter(match: "re.Match") -> str:
        niveau = int(match.group(1))
        attributs = match.group(2)
        contenu = match.group(3)

        titre = re.sub(r'<[^>]+>', '', contenu)
        titre = re.sub(r'\s+', ' ', unescape(titre)).strip()

        existant = ATTR_ID.search(attributs)
        ancre = registre.unique(existant.group(2) if existant else titre)

        if existant:
            attributs = ATTR_ID.sub(f'id="{ancre}"', attributs, count=1)
        else:
            attributs = f'{attributs.rstrip()} id="{ancre}"'

        if numeroter and niveau <= 3:
            attributs = _ajouter_classe(attributs, 'numbered')

        if niveau <= profondeur and titre:
            entrees.append({'niveau': niveau, 'titre': titre, 'ancre': ancre})

        return f'<h{niveau}{attributs}>{contenu}</h{niveau}>'

    return BALISE_TITRE.sub(traiter, html)


# =============================================================================
# SYNTAX HIGHLIGHTING
# =============================================================================

class CodeHighlighter:
    """Coloration syntaxique des fichiers de code annexés (option -c)."""

    def __init__(self):
        self.formatter = HtmlFormatter(cssclass='highlight', linenos=False,
                                       nowrap=False, noclasses=False)

    def highlight_code(self, code: str, language: str = 'python',
                       linenos: bool = False, filename: str = None) -> str:
        """Retourne le HTML coloré d'un bloc de code."""
        options = {}
        # Un fichier PHP sans balise ouvrante n'est pas colorié du tout par
        # Pygments : il faut le lui signaler explicitement.
        if language == 'php' and '<?php' not in code:
            options['startinline'] = True

        try:
            lexer = get_lexer_by_name(language, **options)
        except ClassNotFound:
            print(f"⚠️  Langage inconnu de Pygments : {language} — rendu en texte brut")
            lexer = get_lexer_by_name('text')

        formatter = HtmlFormatter(cssclass='highlight',
                                  linenos='table' if linenos else False,
                                  nowrap=False, noclasses=False)
        resultat = highlight(code, lexer, formatter)

        if filename:
            resultat = (f'<div class="code-header"><span class="filename">'
                        f'{escape_html(filename)}</span></div>' + resultat)
        return resultat

    def get_css(self) -> str:
        """CSS généré par Pygments, pour référence ou pour régénérer la palette."""
        return self.formatter.get_style_defs('.highlight')


# =============================================================================
# CONVERSION MARKDOWN
# =============================================================================

class MarkdownConverter:
    """Convertisseur Markdown vers HTML avec extensions."""

    # Mot-clé Markdown -> classe CSS de l'encadré
    ENCADRES = {
        'INFO': 'info',
        'WARNING': 'warning',
        'IMPORTANT': 'important',
        'REMINDER': 'reminder',
    }

    def __init__(self):
        self.md = markdown.Markdown(
            extensions=[
                'tables',
                'fenced_code',
                'codehilite',
                'toc',
                'attr_list',
                'def_list',
                'footnotes',
                'meta',
                'sane_lists',
                'smarty',
            ],
            extension_configs={
                # codehilite remplace l'ancien découpage des blocs à la regex :
                # il gère les identifiants de langage tels que c++, objective-c
                # ou shell-session, les clôtures ~~~ et les blocs à attributs.
                'codehilite': {
                    'css_class': 'highlight',
                    'guess_lang': False,
                    'linenums': False,
                },
                'toc': {
                    'permalink': False,
                    'toc_depth': 3,
                },
            }
        )

    def convert(self, markdown_text: str) -> Tuple[str, str]:
        """Convertit le Markdown en HTML. Retourne (html, toc_html)."""
        self.md.reset()
        html = self.md.convert(markdown_text)
        toc = getattr(self.md, 'toc', '')
        return self._postprocess_html(html), toc

    def _postprocess_html(self, html: str) -> str:
        """
        Transforme les citations en encadrés pédagogiques.

        Markdown fusionne en une seule citation deux blocs `>` séparés par une
        ligne vide. Quatre encadrés consécutifs arrivent donc ici sous la forme
        d'un unique <blockquote> contenant quatre paragraphes. On le redécoupe
        à chaque paragraphe ouvert par un mot-clé.
        """
        mots = '|'.join(self.ENCADRES)
        bloc = re.compile(r'<blockquote>(.*?)</blockquote>', re.DOTALL)
        coupure = re.compile(r'(?=<p>\s*\[(?:%s)\])' % mots)
        entete = re.compile(r'^<p>\s*\[(%s)\]\s*' % mots)

        def traiter(match):
            morceaux = [m.strip() for m in coupure.split(match.group(1)) if m.strip()]
            sorties = []
            for morceau in morceaux:
                tag = entete.match(morceau)
                if tag:
                    classe = self.ENCADRES[tag.group(1)]
                    corps = entete.sub('<p>', morceau, count=1)
                    sorties.append(f'<blockquote class="{classe}">{corps}</blockquote>')
                else:
                    sorties.append(f'<blockquote>{morceau}</blockquote>')
            return '\n'.join(sorties)

        return bloc.sub(traiter, html)


# =============================================================================
# FICHIER DE CONFIGURATION YAML
# =============================================================================

CLES_YAML = {
    'title', 'subtitle', 'author', 'institution', 'date',
    'output', 'css', 'html', 'fonts', 'markdown', 'code',
    'cover', 'toc', 'numbered', 'tags', 'page_breaks',
}

CLES_CHEMIN = {'css', 'fonts', 'markdown', 'code'}
CLES_SORTIE = {'output', 'html'}
CLES_BOOLEENNES = {'cover', 'toc', 'numbered', 'tags'}


def booleen(valeur, cle: str) -> bool:
    """
    Convertit une valeur YAML en booléen, en refusant les valeurs ambiguës.

    La chaîne "false" est vraie en Python : une faute de frappe dans le YAML
    inverserait silencieusement le réglage.
    """
    if isinstance(valeur, bool):
        return valeur
    if isinstance(valeur, str) and valeur.strip().lower() in ('true', 'false'):
        return valeur.strip().lower() == 'true'
    raise ErreurGeneration(
        f"La clé '{cle}' attend true ou false, valeur reçue : {valeur!r}"
    )


SAUTS_VALIDES = ('section', 'chapter', 'none')


def valider_sauts(valeur) -> str:
    """Contrôle la valeur de page_breaks et retourne la classe CSS associée."""
    valeur = str(valeur).strip().lower()
    if valeur not in SAUTS_VALIDES:
        raise ErreurGeneration(
            "La clé 'page_breaks' attend " + ", ".join(SAUTS_VALIDES)
            + f", valeur reçue : {valeur!r}"
        )
    return valeur


def load_config_file(filepath: str) -> Dict:
    """
    Charge un fichier de configuration YAML.

    Les chemins qu'il contient sont interprétés par rapport au dossier du
    fichier YAML lui-même, et non par rapport au dossier courant : un même
    fichier de configuration fonctionne donc depuis n'importe où.
    """
    if yaml is None:
        raise ErreurGeneration("PyYAML non installé. Exécutez : pip install pyyaml")

    chemin = Path(filepath)
    if not chemin.exists():
        raise ErreurGeneration(f"Fichier de configuration non trouvé : {filepath}")

    try:
        data = yaml.safe_load(chemin.read_text(encoding='utf-8')) or {}
    except yaml.YAMLError as e:
        raise ErreurGeneration(f"Fichier YAML invalide : {e}")

    if not isinstance(data, dict):
        raise ErreurGeneration(
            "Le fichier YAML doit contenir une liste de clés (title, author, ...)"
        )

    for cle in data:
        if cle not in CLES_YAML:
            print(f"⚠️  Clé ignorée dans {filepath} : '{cle}'")

    dossier = chemin.parent.resolve()

    def resoudre(valeur):
        p = Path(str(valeur))
        return str(p if p.is_absolute() else (dossier / p))

    config: Dict = {}
    for cle, valeur in data.items():
        if cle not in CLES_YAML or valeur is None:
            continue
        if cle in CLES_CHEMIN:
            valeur = ([resoudre(v) for v in valeur] if isinstance(valeur, list)
                      else resoudre(valeur))
        elif cle in CLES_SORTIE:
            valeur = str(chemin_sortie(valeur, dossier))
        elif cle in CLES_BOOLEENNES:
            valeur = booleen(valeur, cle)
        elif cle == 'page_breaks':
            valeur = valider_sauts(valeur)
        config[cle] = valeur

    for cle in ('markdown', 'code'):
        if isinstance(config.get(cle), str):
            config[cle] = [config[cle]]

    config['_racine'] = dossier
    return config


def verifier_fichiers(groupes: Dict[str, Iterable]) -> None:
    """
    Vérifie que tous les fichiers déclarés existent, avant toute génération.

    Un fichier manquant produisait auparavant un avertissement et une section
    vide : le PDF sortait incomplet sans qu'on sache pourquoi. On les liste tous
    d'un coup, pour ne pas corriger les chemins un par un.
    """
    manquants: List[str] = []
    for role, fichiers in groupes.items():
        for fichier in fichiers or []:
            chemin = Path(fichier)
            if not chemin.exists():
                manquants.append(f"  · {role} : {chemin}")
            elif chemin.is_dir():
                manquants.append(f"  · {role} : {chemin} (c'est un dossier)")

    if manquants:
        raise ErreurGeneration(
            "Fichiers déclarés mais introuvables :\n" + "\n".join(manquants)
        )


# =============================================================================
# GÉNÉRATEUR DE DOCUMENT HTML
# =============================================================================

class DocumentGenerator:
    """Assemble les sections et produit le document HTML complet."""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.md_converter = MarkdownConverter()
        self.highlighter = CodeHighlighter()
        self.sections: List[Dict] = []
        self.toc_entries: List[Dict] = []
        self.ancres = RegistreAncres()
        self.erreurs_ressources: List[str] = []

    # -- racine du projet ----------------------------------------------------

    @property
    def racine(self) -> Path:
        """Dossier au-delà duquel aucune ressource n'est chargée."""
        return Path(self.config.RACINE or Path.cwd()).resolve()

    # -- ajout de contenu ----------------------------------------------------

    def _integrer(self, html: str, dossier_source: Path, source: str = "") -> str:
        """Applique les deux passes communes : ressources, puis ancres uniques."""
        html = resoudre_ressources(html, dossier_source, self.racine,
                                   self.erreurs_ressources,
                                   source=f"{source} : " if source else "")
        return normaliser_titres(html, self.ancres, self.toc_entries,
                                 numeroter=self.config.NUMBERED_CHAPTERS,
                                 profondeur=self.config.TOC_DEPTH)

    def add_markdown_file(self, filepath, section_type: str = 'content') -> None:
        """Ajoute un fichier Markdown au document."""
        chemin = Path(filepath)
        contenu = read_file(chemin)
        if not contenu.strip():
            print(f"⚠️  Fichier Markdown vide : {chemin}")
            return

        html, _ = self.md_converter.convert(contenu)
        html = self._integrer(html, chemin.parent.resolve(), chemin.name)

        self.sections.append({
            'type': section_type,
            'content': html,
            'source': str(chemin),
        })

    def add_code_file(self, filepath, title: str = None,
                      explanation: str = None, exercise_text: str = None) -> None:
        """Ajoute un fichier de code source en annexe, avec coloration."""
        chemin = Path(filepath)
        code = read_file(chemin)
        if not code.strip():
            print(f"⚠️  Fichier de code vide : {chemin}")
            return

        language = detect_language(chemin)
        title = title or f"Code : {chemin.name}"

        parties = [f'<h2>{escape_html(title)}</h2>']

        if exercise_text:
            enonce_html, _ = self.md_converter.convert(exercise_text)
            parties.append('<div class="enonce"><h4>Énoncé</h4>'
                           f'{enonce_html}</div>')

        if explanation:
            expl_html, _ = self.md_converter.convert(explanation)
            parties.append('<div class="explication"><h4>Explication</h4>'
                           f'{expl_html}</div>')

        parties.append('<div class="correction">')
        for bloc in decouper_code(code):
            colore = self.highlighter.highlight_code(bloc, language)
            parties.append(f'<div class="code-block">{colore}</div>')
        parties.append('</div>')

        html = self._integrer('\n'.join(parties), chemin.parent.resolve(), chemin.name)
        self.sections.append({
            'type': 'code',
            'content': html,
            'source': str(chemin),
        })

    def add_raw_html(self, html: str, section_type: str = 'content',
                     dossier_source: Path = None) -> None:
        """Ajoute du HTML déjà produit ailleurs (API publique)."""
        html = self._integrer(html, Path(dossier_source or self.racine).resolve())
        self.sections.append({
            'type': section_type,
            'content': html,
            'source': 'raw',
        })

    # -- assemblage ----------------------------------------------------------

    def _generate_cover_page(self) -> str:
        return f'''
        <div class="cover-page">
            <div class="title">{escape_html(self.config.TITLE)}</div>
            <div class="subtitle">{escape_html(self.config.SUBTITLE)}</div>
            <div class="author">{escape_html(self.config.AUTHOR)}</div>
            <div class="date">{escape_html(self.config.DATE)}</div>
            <div class="institution">{escape_html(self.config.INSTITUTION)}</div>
        </div>
        '''

    def _generate_toc(self) -> str:
        """
        Construit la table des matières à partir des titres relevés.

        Les entrées viennent de la passe d'ancrage : chaque lien pointe sur un
        identifiant qui existe réellement et n'est utilisé qu'une fois.
        """
        lignes = ['<div class="toc">', '<h1 class="toc-titre">Table des matières</h1>']
        for entree in self.toc_entries:
            lignes.append(
                f'<a class="toc-entry level-{entree["niveau"]}" href="#{entree["ancre"]}">'
                f'<span class="toc-title">{escape_html(entree["titre"])}</span>'
                f'<span class="toc-leader"></span>'
                f'</a>'
            )
        lignes.append('</div>')
        return '\n'.join(lignes)

    def _charger_css(self) -> str:
        """Lit la feuille de style et y ajoute les @font-face des polices livrées."""
        candidats = [Path(self.config.CSS_FILE),
                     Path(__file__).parent / self.config.CSS_FILE]
        for css_path in candidats:
            if css_path.exists():
                css = read_file(css_path)
                break
        else:
            raise ErreurGeneration(f"Feuille de style introuvable : {self.config.CSS_FILE}")

        faces, trouvees = generer_font_faces(self.dossier_polices())
        if trouvees:
            print(f"🔤 Polices incorporées : {', '.join(trouvees)}")
        else:
            print("⚠️  Aucune police dans le dossier fonts/ : rendu dépendant "
                  "des polices du système")
        return faces + "\n" + css

    def dossier_polices(self) -> Path:
        """Dossier des polices : valeur configurée, ou fonts/ à côté du script."""
        dossier = Path(self.config.FONTS_DIR)
        if not dossier.is_absolute():
            local = Path(__file__).parent / dossier
            dossier = dossier if dossier.is_dir() else local
        return dossier

    def generate_html(self) -> str:
        """Génère le document HTML complet, CSS incorporé."""
        css_content = self._charger_css()

        if self.erreurs_ressources:
            raise ErreurGeneration(
                "Ressources refusées ou manquantes :\n"
                + "\n".join(f"  · {e}" for e in dict.fromkeys(self.erreurs_ressources))
            )

        # Les balises <meta> alimentent les propriétés du PDF (Titre, Auteur,
        # Créateur). Elles n'apparaissent pas sur la page.
        parties = [
            '<!DOCTYPE html>',
            '<html lang="fr">',
            '<head>',
            '    <meta charset="UTF-8">',
            f'    <title>{escape_html(self.config.TITLE)}</title>',
            f'    <meta name="author" content="{escape_html(self.config.AUTHOR)}">',
            f'    <meta name="generator" content="{escape_html(self.config.GENERATOR)} '
            f'— Designed by {escape_html(self.config.DESIGNER)}">',
            f'    <meta name="designer" content="Designed by '
            f'{escape_html(self.config.DESIGNER)}">',
            '    <style>',
            css_content,
            '    </style>',
            '</head>',
            f'<body class="sauts-{self.config.PAGE_BREAKS}">',
        ]

        if self.config.INCLUDE_COVER:
            parties.append(self._generate_cover_page())

        if self.config.GENERATE_TOC:
            parties.append(self._generate_toc())

        # La première section porte une classe à part : c'est le seul endroit
        # où le saut de page automatique doit être annulé, pour ne pas laisser
        # une page blanche après la table des matières. Auparavant la règle
        # :first-of-type s'appliquait dans chaque conteneur, donc à tous les
        # fichiers, et plus aucun titre ne changeait de page.
        for rang, section in enumerate(self.sections):
            classe = section.get('type', 'content')
            premiere = ' premiere-section' if rang == 0 else ''
            if classe == 'annexe':
                parties.append(f'<div class="annexe{premiere}">')
            else:
                parties.append(f'<div class="section section-{classe}{premiere}">')
            parties.append(section.get('content', ''))
            parties.append('</div>')

        parties.extend(['</body>', '</html>'])
        return '\n'.join(parties)


# =============================================================================
# GÉNÉRATEUR PDF
# =============================================================================

class PDFGenerator:
    """Rendu PDF via WeasyPrint, ressources confinées."""

    def __init__(self, racines: Sequence[Path] = (), tags: bool = False):
        self.font_config = FontConfiguration()
        self.racines = [Path(r).resolve() for r in racines] or [Path.cwd()]
        self.tags = tags

    def generate(self, html_content: str, output_path) -> Path:
        """Écrit le PDF. Lève ErreurGeneration en cas d'échec."""
        cible = preparer_dossier(Path(output_path))
        base = self.racines[0].as_uri().rstrip('/') + '/'

        options = {'custom_metadata': True}
        if self.tags:
            options['pdf_tags'] = True

        try:
            document = HTML(string=html_content, base_url=base,
                            url_fetcher=creer_url_fetcher(self.racines))
            document.write_pdf(cible, font_config=self.font_config, **options)
        except RessourceRefusee as e:
            raise ErreurGeneration(str(e))
        except ErreurGeneration:
            raise
        except Exception as e:
            raise ErreurGeneration(f"Échec du rendu PDF : {e}")

        print(f"✅ PDF généré : {cible}")
        return cible

    def generate_from_file(self, html_path, output_path) -> Path:
        """Génère le PDF à partir d'un fichier HTML déjà produit."""
        return self.generate(read_file(html_path), output_path)


# =============================================================================
# API PUBLIQUE
# =============================================================================

def generer_pdf(markdown: Sequence[str] = None,
                code: Sequence[str] = None,
                sortie="document.pdf",
                titre: str = "Manuel Académique",
                sous_titre: str = "",
                auteur: str = "Auteur",
                institution: str = "",
                date: str = None,
                css: str = None,
                polices: str = None,
                racine=None,
                html: str = None,
                couverture: bool = True,
                sommaire: bool = True,
                numerote: bool = False,
                tags: bool = False,
                sauts: str = 'section') -> Path:
    """
    Produit un PDF et retourne son chemin.

    markdown, code : listes de fichiers, dans l'ordre d'apparition.
    racine         : dossier au-delà duquel aucune ressource n'est chargée.
                     Par défaut, le dossier du premier Markdown fourni.
    sauts          : sauts de page automatiques — 'section' (chaque titre de
                     niveau 2), 'chapter' (chaque titre de niveau 1) ou 'none'.
    html           : chemin où sauvegarder le HTML intermédiaire (débogage).

    Lève ErreurGeneration si un fichier déclaré est absent, si une ressource
    sort de la racine, ou si le rendu échoue.
    """
    markdown = list(markdown or [])
    code = list(code or [])
    if not markdown and not code:
        raise ErreurGeneration("Aucun contenu : fournissez un Markdown ou un code source.")

    config = Config()
    config.TITLE = titre
    config.SUBTITLE = sous_titre
    config.AUTHOR = auteur
    config.INSTITUTION = institution
    config.INCLUDE_COVER = couverture
    config.GENERATE_TOC = sommaire
    config.NUMBERED_CHAPTERS = numerote
    config.PDF_TAGS = tags
    config.PAGE_BREAKS = valider_sauts(sauts)
    if date:
        config.DATE = str(date)
    if css:
        config.CSS_FILE = str(css)
    if polices:
        config.FONTS_DIR = str(polices)

    premier = Path(markdown[0] if markdown else code[0]).resolve().parent
    config.RACINE = Path(racine).resolve() if racine else premier

    feuille = Path(config.CSS_FILE)
    verifier_fichiers({
        'markdown': markdown,
        'code': code,
        'css': [feuille] if feuille.is_absolute() or feuille.exists() else [],
    })

    generateur = DocumentGenerator(config)
    for fichier in markdown:
        print(f"📄 Ajout du Markdown : {fichier}")
        generateur.add_markdown_file(fichier)
    for fichier in code:
        print(f"💻 Ajout du code : {fichier}")
        generateur.add_code_file(fichier)

    print("🔧 Génération du HTML...")
    contenu = generateur.generate_html()

    if html:
        cible_html = preparer_dossier(Path(html))
        cible_html.write_text(contenu, encoding='utf-8')
        print(f"📝 HTML sauvegardé : {cible_html}")

    print("📚 Génération du PDF...")
    racines = [generateur.racine, generateur.dossier_polices().resolve()]
    pdf = PDFGenerator(racines, tags=config.PDF_TAGS)
    chemin = pdf.generate(contenu, sortie)

    taille = chemin.stat().st_size / 1024
    print(f"✨ Terminé ! Taille : {taille:.1f} Ko")
    return chemin


# =============================================================================
# INTERFACE CLI
# =============================================================================

# Dossier des fichiers de démonstration, livré à côté du script.
DOSSIER_EXEMPLE = Path(__file__).parent / 'exemple'
FICHIERS_EXEMPLE = ('exemple.md', 'config.exemple.yaml', 'exercice1.py', 'exercice2.py')


def create_example_files(destination: str = 'examples') -> Path:
    """
    Copie les fichiers de démonstration livrés avec l'outil dans un dossier.

    Ce sont les fichiers réels du dossier exemple/, pas des copies intégrées
    au script : ce qui est documenté est donc forcément ce qui est livré.
    """
    source = DOSSIER_EXEMPLE
    cible = Path(destination)
    cible.mkdir(parents=True, exist_ok=True)

    copies = []
    for nom in FICHIERS_EXEMPLE:
        origine = source / nom
        if origine.exists():
            shutil.copy2(origine, cible / nom)
            copies.append(nom)

    dossier_assets = source / 'assets'
    if dossier_assets.is_dir():
        shutil.copytree(dossier_assets, cible / 'assets', dirs_exist_ok=True)
        copies.append('assets/')

    if not copies:
        raise ErreurGeneration(
            f"Aucun fichier de démonstration trouvé dans {source}"
        )

    print(f"✅ Fichiers d'exemple copiés dans '{cible}/' : {', '.join(copies)}")
    return cible


def main() -> None:
    """Point d'entrée de la ligne de commande."""
    parser = argparse.ArgumentParser(
        prog='didacode',
        description='Didacode — générateur de PDF pédagogiques',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemples d'utilisation :
  %(prog)s --example                        Générer le PDF de démonstration
  %(prog)s -m doc.md -o output.pdf          Convertir un Markdown en PDF
  %(prog)s -m doc.md -c code.py -o out.pdf  Markdown + code source
  %(prog)s --config manuel.yaml             Tout paramétrer dans un fichier
  %(prog)s --config manuel.yaml --title X   Surcharger une valeur du fichier
  %(prog)s --create-examples                Copier les fichiers de démonstration

Un nom de sortie sans dossier est rangé dans output/. Les dossiers manquants
sont créés. Les images doivent rester sous la racine du projet : le dossier du
fichier YAML, ou à défaut celui du premier Markdown.
        '''
    )

    parser.add_argument('--config', help='Fichier de configuration YAML')
    parser.add_argument('-m', '--markdown', nargs='+', help='Fichier(s) Markdown à inclure')
    parser.add_argument('-c', '--code', nargs='+', help='Fichier(s) de code source à inclure')
    parser.add_argument('-o', '--output', help='Fichier PDF de sortie (défaut : output/document.pdf)')
    parser.add_argument('--css', help='Feuille de style à utiliser (défaut : styles.css)')
    parser.add_argument('--fonts', help='Dossier des polices à incorporer (défaut : fonts/)')
    parser.add_argument('--root', help='Racine autorisée pour les ressources')
    parser.add_argument('--html', help='Sauvegarder également le HTML intermédiaire')
    parser.add_argument('--title', help='Titre du document')
    parser.add_argument('--subtitle', help='Sous-titre du document')
    parser.add_argument('--author', help='Auteur du document')
    parser.add_argument('--institution', help='Institution')
    parser.add_argument('--numbered', action='store_true',
                        help='Numéroter les titres (Chapitre 1 — , 1.1, 1.1.1)')
    parser.add_argument('--page-breaks', choices=SAUTS_VALIDES, dest='page_breaks',
                        help='Sauts de page automatiques : section (défaut), '
                             'chapter ou none')
    parser.add_argument('--tags', action='store_true',
                        help='Baliser le PDF pour l\'accessibilité')
    parser.add_argument('--no-cover', action='store_true', help='Ne pas inclure la page de garde')
    parser.add_argument('--no-toc', action='store_true', help='Ne pas inclure la table des matières')
    parser.add_argument('--example', action='store_true', help='Générer le PDF de démonstration')
    parser.add_argument('--create-examples', action='store_true',
                        help='Copier les fichiers de démonstration dans examples/')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    args = parser.parse_args()

    try:
        if args.create_examples:
            create_example_files()
            return

        fichier_config: Dict = {}
        if args.config:
            print(f"⚙️  Configuration : {args.config}")
            fichier_config = load_config_file(args.config)

        def valeur(nom, defaut=None):
            """Ligne de commande > fichier YAML > valeur par défaut."""
            depuis_cli = getattr(args, nom, None)
            if depuis_cli:
                return depuis_cli
            if fichier_config.get(nom) is not None:
                return fichier_config[nom]
            return defaut

        fichiers_md = valeur('markdown')
        fichiers_code = valeur('code')
        sortie = valeur('output')
        racine = args.root or fichier_config.get('_racine')

        if args.example:
            fichiers_md = [str(DOSSIER_EXEMPLE / 'exemple.md')]
            fichiers_code = [str(DOSSIER_EXEMPLE / 'exercice1.py')]
            sortie = sortie or 'exemple.pdf'
            racine = racine or DOSSIER_EXEMPLE

        if not fichiers_md and not fichiers_code:
            parser.print_help()
            raise ErreurGeneration(
                "Spécifiez au moins un fichier Markdown ou un fichier de code."
            )

        # Un chemin CLI est relatif au dossier courant ; un chemin YAML a déjà
        # été résolu par rapport au fichier de configuration.
        sortie = chemin_sortie(sortie or 'document.pdf', Path.cwd())
        html = args.html and str(chemin_sortie(args.html, Path.cwd()))
        html = html or fichier_config.get('html')

        generer_pdf(
            markdown=fichiers_md,
            code=fichiers_code,
            sortie=sortie,
            titre=valeur('title', 'Manuel Académique'),
            sous_titre=valeur('subtitle', ''),
            auteur=valeur('author', 'Auteur'),
            institution=valeur('institution', ''),
            date=fichier_config.get('date'),
            css=valeur('css', Config.CSS_FILE),
            polices=valeur('fonts'),
            racine=racine,
            html=html,
            couverture=False if args.no_cover else fichier_config.get('cover', True),
            sommaire=False if args.no_toc else fichier_config.get('toc', True),
            numerote=args.numbered or fichier_config.get('numbered', False),
            tags=args.tags or fichier_config.get('tags', False),
            sauts=valeur('page_breaks', 'section'),
        )

    except ErreurGeneration as e:
        print(f"\n❌ {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:  # pragma: no cover
        print("\n⏹️  Interrompu.", file=sys.stderr)
        sys.exit(130)


if __name__ == '__main__':
    main()
