#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests de Didacode.

    python -m unittest discover -s tests

Chaque test correspond à un défaut corrigé : ancres dupliquées, fichiers
déclarés mais absents, ressources hors du projet, booléens YAML ambigus,
dossiers de sortie inexistants, langages de blocs de code.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import didacode as dc  # noqa: E402


class DossierTemporaire(unittest.TestCase):
    """Crée un projet jetable pour chaque test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.racine = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def ecrire(self, nom, contenu):
        chemin = self.racine / nom
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(contenu, encoding='utf-8')
        return chemin


class TestAncres(DossierTemporaire):

    def test_titres_identiques_dans_deux_fichiers(self):
        """Deux « ## Installation » doivent produire deux ancres différentes."""
        self.ecrire('a.md', '# Doc A\n\n## Installation\n\nTexte.\n')
        self.ecrire('b.md', '# Doc B\n\n## Installation\n\nTexte.\n')

        config = dc.Config()
        config.RACINE = self.racine
        doc = dc.DocumentGenerator(config)
        doc.add_markdown_file(self.racine / 'a.md')
        doc.add_markdown_file(self.racine / 'b.md')

        ancres = [e['ancre'] for e in doc.toc_entries]
        self.assertEqual(len(ancres), len(set(ancres)))
        self.assertIn('installation', ancres)
        self.assertIn('installation-2', ancres)

    def test_titre_sans_identifiant(self):
        """Un titre en HTML brut reçoit un identifiant au lieu d'un lien cassé."""
        registre = dc.RegistreAncres()
        entrees = []
        html = dc.normaliser_titres('<h2>Annexe</h2>', registre, entrees)
        self.assertIn('id="annexe"', html)
        self.assertEqual(entrees[0]['ancre'], 'annexe')

    def test_sommaire_pointe_sur_des_ancres_existantes(self):
        self.ecrire('a.md', '# A\n\n## Installation\n')
        self.ecrire('b.md', '# B\n\n## Installation\n')
        config = dc.Config()
        config.RACINE = self.racine
        doc = dc.DocumentGenerator(config)
        doc.add_markdown_file(self.racine / 'a.md')
        doc.add_markdown_file(self.racine / 'b.md')

        html = doc.generate_html()
        for entree in doc.toc_entries:
            self.assertIn(f'id="{entree["ancre"]}"', html)
            self.assertIn(f'href="#{entree["ancre"]}"', html)


class TestFichiers(DossierTemporaire):

    def test_fichier_absent_bloque_la_generation(self):
        self.ecrire('a.md', '# A\n')
        with self.assertRaises(dc.ErreurGeneration) as contexte:
            dc.verifier_fichiers({'markdown': [self.racine / 'a.md',
                                               self.racine / 'absent.md']})
        self.assertIn('absent.md', str(contexte.exception))

    def test_dossier_de_sortie_cree(self):
        cible = self.racine / 'build' / 'pdf' / 'doc.pdf'
        dc.preparer_dossier(cible)
        self.assertTrue(cible.parent.is_dir())

    def test_sortie_sans_dossier_rangee_dans_output(self):
        chemin = dc.chemin_sortie('manuel.pdf', self.racine)
        self.assertEqual(chemin, self.racine / 'output' / 'manuel.pdf')

    def test_sortie_avec_dossier_respectee(self):
        chemin = dc.chemin_sortie('build/manuel.pdf', self.racine)
        self.assertEqual(chemin, self.racine / 'build' / 'manuel.pdf')


class TestRessources(DossierTemporaire):

    def setUp(self):
        super().setUp()
        self.erreurs = []

    def test_image_locale_rendue_absolue(self):
        (self.racine / 'images').mkdir()
        (self.racine / 'images' / 'x.png').write_bytes(b'x')
        html = dc.resoudre_ressources('<img src="images/x.png">', self.racine,
                                      self.racine, self.erreurs)
        self.assertEqual(self.erreurs, [])
        self.assertIn('file://', html)

    def test_image_hors_racine_refusee(self):
        with tempfile.TemporaryDirectory() as ailleurs:
            image = Path(ailleurs) / 'x.png'
            image.write_bytes(b'x')
            dc.resoudre_ressources(f'<img src="{image}">', self.racine,
                                   self.racine, self.erreurs)
        self.assertTrue(any('hors du projet' in e for e in self.erreurs))

    def test_image_absente_signalee(self):
        dc.resoudre_ressources('<img src="images/absente.png">', self.racine,
                               self.racine, self.erreurs)
        self.assertTrue(any('introuvable' in e for e in self.erreurs))

    def test_ressource_distante_refusee(self):
        dc.resoudre_ressources('<img src="https://exemple.fr/x.png">', self.racine,
                               self.racine, self.erreurs)
        self.assertTrue(any('externe' in e for e in self.erreurs))

    def test_image_incorporee_conservee(self):
        html = dc.resoudre_ressources('<img src="data:image/png;base64,AA">',
                                      self.racine, self.racine, self.erreurs)
        self.assertEqual(self.erreurs, [])
        self.assertIn('data:image/png', html)

    def test_chargeur_refuse_le_reseau(self):
        with self.assertRaises(dc.RessourceRefusee):
            dc.verifier_url('https://exemple.fr/x.png', [self.racine])


class TestYaml(DossierTemporaire):

    def test_chaine_false_interpretee_comme_faux(self):
        self.assertFalse(dc.booleen('false', 'cover'))
        self.assertFalse(dc.booleen(False, 'cover'))

    def test_valeur_ambigue_refusee(self):
        with self.assertRaises(dc.ErreurGeneration):
            dc.booleen('oui', 'cover')

    def test_chemins_relatifs_au_fichier_yaml(self):
        self.ecrire('projet/doc.md', '# A\n')
        self.ecrire('projet/manuel.yaml',
                    'title: T\nmarkdown:\n  - doc.md\noutput: manuel.pdf\n')
        config = dc.load_config_file(self.racine / 'projet' / 'manuel.yaml')
        self.assertEqual(config['markdown'], [str(self.racine / 'projet' / 'doc.md')])
        self.assertEqual(config['_racine'], (self.racine / 'projet').resolve())


class TestPagination(DossierTemporaire):

    def html(self, mode):
        self.ecrire('a.md', '# Chapitre A\n\nTexte.\n\n## Section A1\n\nTexte.\n')
        self.ecrire('b.md', '# Chapitre B\n\nTexte.\n')
        config = dc.Config()
        config.RACINE = self.racine
        config.PAGE_BREAKS = mode
        doc = dc.DocumentGenerator(config)
        doc.add_markdown_file(self.racine / 'a.md')
        doc.add_markdown_file(self.racine / 'b.md')
        return doc.generate_html()

    def test_classe_de_mode_sur_le_body(self):
        self.assertIn('<body class="sauts-chapter">', self.html('chapter'))

    def test_une_seule_premiere_section(self):
        """L'exception de saut ne doit valoir que pour la première section."""
        html = self.html('section')
        # la chaîne apparaît aussi dans le CSS incorporé : on ne compte que
        # les attributs class des sections
        self.assertEqual(html.count('premiere-section">'), 1)

    def test_mode_invalide_refuse(self):
        with self.assertRaises(dc.ErreurGeneration):
            dc.valider_sauts('parfois')

    def test_modes_valides(self):
        for mode in dc.SAUTS_VALIDES:
            self.assertEqual(dc.valider_sauts(mode.upper()), mode)


class TestCode(unittest.TestCase):

    def test_langages_multiples(self):
        colorateur = dc.CodeHighlighter()
        for langage, extrait in [
            ('python', 'def f(): pass'),
            ('c', '#include <stdio.h>'),
            ('cpp', 'int main() { return 0; }'),
            ('nasm', 'mov rax, 1'),
            ('gas', 'mov %rax, %rbx'),
            ('java', 'class A {}'),
            ('kotlin', 'fun main() {}'),
            ('php', 'function f() {}'),
        ]:
            html = colorateur.highlight_code(extrait, langage)
            self.assertIn('class="highlight"', html, langage)
            self.assertIn('<span', html, langage)

    def test_php_sans_balise_ouvrante_est_colorie(self):
        html = dc.CodeHighlighter().highlight_code('function f() { return 1; }', 'php')
        self.assertIn('class="k"', html)

    def test_extensions_reconnues(self):
        self.assertEqual(dc.detect_language('a.kt'), 'kotlin')
        self.assertEqual(dc.detect_language('a.S'), 'gas')
        self.assertEqual(dc.detect_language('a.inconnu'), 'text')

    def test_blocs_markdown_multilingues(self):
        converteur = dc.MarkdownConverter()
        html, _ = converteur.convert(
            "```c++\nint a = 1;\n```\n\n~~~shell-session\n$ ls\n~~~\n"
        )
        self.assertEqual(html.count('class="highlight"'), 2)

    def test_encadres_consecutifs_separes(self):
        converteur = dc.MarkdownConverter()
        html, _ = converteur.convert("> [INFO] Un.\n\n> [WARNING] Deux.\n")
        self.assertIn('blockquote class="info"', html)
        self.assertIn('blockquote class="warning"', html)


class TestPolices(DossierTemporaire):

    def test_roboto_mono_est_reconnue(self):
        """La police monospace livrée doit produire une règle @font-face."""
        self.ecrire('RobotoMono-Regular.ttf', '')
        css, familles = dc.generer_font_faces(self.racine)
        self.assertIn('Roboto Mono', familles)
        self.assertIn('font-family: "Roboto Mono"', css)

    def test_variables_couvrent_droit_italique_normal_et_gras(self):
        """Deux fontes variables couvrent les quatre styles d'une famille."""
        self.ecrire('EBGaramond-VariableFont_wght.ttf', '')
        self.ecrire('EBGaramond-Italic-VariableFont_wght.ttf', '')
        css, familles = dc.generer_font_faces(self.racine)

        self.assertEqual(familles, ['EB Garamond'])
        self.assertEqual(css.count('font-family: "EB Garamond"'), 2)
        self.assertEqual(css.count('font-weight: 400 700'), 2)
        self.assertIn('font-style: normal', css)
        self.assertIn('font-style: italic', css)

    def test_source_serif_reconnait_les_axes_optiques_et_de_graisse(self):
        """Les noms variables de Source Serif 4 doivent être reconnus."""
        self.ecrire('SourceSerif4-VariableFont_opsz,wght.ttf', '')
        self.ecrire('SourceSerif4-Italic-VariableFont_opsz,wght.ttf', '')
        css, familles = dc.generer_font_faces(self.racine)

        self.assertEqual(familles, ['Source Serif 4'])
        self.assertEqual(css.count('font-family: "Source Serif 4"'), 2)
        self.assertEqual(css.count('font-weight: 400 700'), 2)
        self.assertIn('font-style: normal', css)
        self.assertIn('font-style: italic', css)

    def test_fira_code_variable_couvre_normal_et_gras(self):
        """Fira Code n'a qu'une fonte variable droite officielle."""
        self.ecrire('FiraCode-VariableFont_wght.ttf', '')
        css, familles = dc.generer_font_faces(self.racine)

        self.assertEqual(familles, ['Fira Code'])
        self.assertEqual(css.count('font-family: "Fira Code"'), 1)
        self.assertIn('font-weight: 400 700', css)
        self.assertIn('font-style: normal', css)
        self.assertNotIn('font-style: italic', css)

    def test_distribution_ne_garde_que_les_polices_variables(self):
        """Évite de réintroduire les nombreuses variantes statiques."""
        dossier = Path(dc.__file__).resolve().parent / 'fonts'
        polices = sorted(p.name for p in dossier.glob('*.ttf'))
        self.assertEqual(polices, [
            'EBGaramond-Italic-VariableFont_wght.ttf',
            'EBGaramond-VariableFont_wght.ttf',
            'FiraCode-VariableFont_wght.ttf',
            'RobotoMono-Italic-VariableFont_wght.ttf',
            'RobotoMono-VariableFont_wght.ttf',
            'SourceSerif4-Italic-VariableFont_opsz,wght.ttf',
            'SourceSerif4-VariableFont_opsz,wght.ttf',
        ])


if __name__ == '__main__':
    unittest.main()
