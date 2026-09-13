#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exercice 1 — Bulletin de notes

Énoncé :
    Écrire un programme qui calcule la moyenne d'une liste de notes,
    détermine la mention correspondante et affiche un bulletin.
    Une note invalide (hors de l'intervalle 0-20) doit être ignorée.

Notions mobilisées : listes, fonctions, conditions, boucle for, f-strings.
"""

NOTE_MINI = 0
NOTE_MAXI = 20


def est_valide(note):
    """Vérifie qu'une note appartient bien à l'intervalle autorisé."""
    return NOTE_MINI <= note <= NOTE_MAXI


def filtrer_notes(notes):
    """Renvoie uniquement les notes valides, et signale les autres."""
    valides = []
    for note in notes:
        if est_valide(note):
            valides.append(note)
        else:
            print(f"Note ignorée : {note}")
    return valides


def moyenne(notes):
    """Calcule la moyenne d'une liste de notes.

    Renvoie 0.0 si la liste est vide, pour éviter une division par zéro.
    """
    if not notes:
        return 0.0
    return sum(notes) / len(notes)


def mention(moy):
    """Associe une mention à une moyenne sur 20."""
    if moy >= 16:
        return "Très bien"
    elif moy >= 14:
        return "Bien"
    elif moy >= 12:
        return "Assez bien"
    elif moy >= 10:
        return "Passable"
    else:
        return "Ajourné"


def afficher_bulletin(nom, notes):
    """Affiche le détail des notes, la moyenne et la mention."""
    valides = filtrer_notes(notes)
    moy = moyenne(valides)

    print(f"\nBulletin de {nom}")
    print("-" * 30)
    for numero, note in enumerate(valides, start=1):
        print(f"  Devoir {numero} : {note}/20")
    print("-" * 30)
    print(f"  Moyenne : {moy:.2f}/20")
    print(f"  Mention : {mention(moy)}")


if __name__ == "__main__":
    afficher_bulletin("Alice", [15, 18, 12, 16])
    afficher_bulletin("Bob", [9, 25, 11, -3, 13])
