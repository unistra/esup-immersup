========
ImmerSup
========

**Master**

.. image:: https://git.unistra.fr/di/immersionlyceens/badges/master/pipeline.svg
   :target: https://git.unistra.fr/di/immersionlyceens/commits/master
   :alt: Tests

.. image:: https://git.unistra.fr/di/immersionlyceens/badges/master/coverage.svg
   :target: https://git.unistra.fr/di/immersionlyceens/commits/master
   :alt: Coverage


**Develop**

.. image:: https://git.unistra.fr/di/immersionlyceens/badges/develop/pipeline.svg
   :target: https://git.unistra.fr/di/immersionlyceens/commits/develop
   :alt: Tests

.. image:: https://git.unistra.fr/di/immersionlyceens/badges/develop/coverage.svg
   :target: https://git.unistra.fr/di/immersionlyceens/commits/develop
   :alt: Coverage

Installation env. de dev
========================

Prérequis
===================
pip, virtualenv, virtualenvwrapper, python (>=3.6) doivent être installés.

Procédure pour un env de dev
============================

Création de l'environnement virtuel
-----------------------------------

Pour créer l'environnement virtuel, se placer dans le répertoire du projet::

    $ mkvirtualenv immersionlyceens

Ou en spécifiant la version de python::

    $ mkvirtualenv immersionlyceens -p /usr/bin/python3.8

Configuration du projet
-----------------------

Pour configurer le projet dans l'environnement virtuel::

    $ setvirtualenvproject $VIRTUAL_ENV $(pwd)

    # Edition du fichier postactivate
    $ echo "export DJANGO_SETTINGS_MODULE=immersionlyceens.settings.dev" >> $VIRTUAL_ENV/bin/postactivate

    # Edition du fichier postdeactivate
    $ echo "unset DJANGO_SETTINGS_MODULE" >> $VIRTUAL_ENV/bin/postdeactivate

    # Rechargement de l'environnement virtuel
    $ workon immersionlyceens

Installation des librairies
---------------------------

Pour installer les librairies ::

    $ cdproject
    $ pip install -r requirements/dev.txt

Lancer le serveur de développement
----------------------------------

Pour finaliser l'installation et lancer le serveur::

    $ chmod u+x manage.py
    $ ./manage.py migrate
    $ ./manage.py runserver


