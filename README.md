# Visionneuse de fichiers

Application desktop PySide6 avec deux onglets :

- **Général** : ouvre un dossier et affiche tous ses fichiers récursivement, avec aperçu des images et ouverture par double-clic.
- **Astro** : mémorise le dossier mère dans les réglages Windows de l'application, détecte les objets dans l'arborescence et trie les photos par catégorie puis par date extraite des dossiers `AAAA-MM-JJ` ou `AAAA_MM_JJ`.

La sélection Astro peut être exportée en archive ZIP.

Les noms courts des dossiers Astro peuvent être affichés avec un libellé plus explicite dans `astro_labels.json` (par exemple `Jup` devient `Jupiter`).

## Lancer l'application

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Les chemins Astro sont enregistrés par `QSettings` dans les réglages utilisateur Windows, sous `Visionneuse/VisionneuseFichier`.

## Créer l'exécutable Windows

Avec l'environnement Python configuré et PyInstaller installé :

```powershell
.\build.ps1
```

L'exécutable autonome est créé ici : `dist\VisionneuseAstro.exe`.
