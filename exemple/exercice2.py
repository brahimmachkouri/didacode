#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exercice 2 — Numéro de sécurité sociale

Énoncé :
    Un numéro de sécurité sociale français comporte 15 chiffres : 13 pour le
    numéro lui-même, puis 2 pour la clé de contrôle. Cette clé vaut
    97 - (numéro modulo 97). Écrire un programme qui vérifie un numéro saisi
    et affiche les informations qu'il contient.

Notions mobilisées : chaînes, slicing, modulo, dictionnaires, conversions.
"""

SEXES = {"1": "masculin", "2": "féminin"}

MOIS = {
    "01": "janvier", "02": "février", "03": "mars",
    "04": "avril", "05": "mai", "06": "juin",
    "07": "juillet", "08": "août", "09": "septembre",
    "10": "octobre", "11": "novembre", "12": "décembre",
}


def nettoyer(numero):
    """Supprime les espaces de mise en forme du numéro."""
    return numero.replace(" ", "")


def cle_attendue(numero):
    """Calcule la clé de contrôle des 13 premiers chiffres."""
    return 97 - int(numero[:13]) % 97


def verifier(numero):
    """Vérifie la longueur et la clé de contrôle d'un numéro."""
    numero = nettoyer(numero)

    if len(numero) != 15:
        return False, f"Longueur incorrecte : {len(numero)} chiffres au lieu de 15"

    if not numero.isdigit():
        return False, "Le numéro ne doit contenir que des chiffres"

    cle_lue = int(numero[-2:])
    cle_calculee = cle_attendue(numero)

    if cle_lue != cle_calculee:
        return False, f"Clé invalide : {cle_lue} au lieu de {cle_calculee}"

    return True, "Numéro valide"


def decrire(numero):
    """Extrait le sexe, l'année et le mois de naissance."""
    numero = nettoyer(numero)
    return {
        "sexe": SEXES.get(numero[0], "inconnu"),
        "annee": numero[1:3],
        "mois": MOIS.get(numero[3:5], "inconnu"),
        "departement": numero[5:7],
    }


if __name__ == "__main__":
    exemples = [
        "1 85 07 75 123 456 08",   # clé correcte
        "2 90 12 33 001 002 45",   # clé erronée
    ]

    for exemple in exemples:
        valide, message = verifier(exemple)
        print(f"\n{exemple} -> {message}")

        if valide:
            infos = decrire(exemple)
            for cle, valeur in infos.items():
                print(f"  {cle:12} : {valeur}")
