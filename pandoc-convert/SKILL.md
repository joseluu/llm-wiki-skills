---
name: pandoc-convert
description: Convert HTML and ODT documents to Markdown using the portable pandoc binary at C:\Users\josel\softs_portable\pandoc-3.8.3\pandoc.exe. Use when the user asks to convert HTML/.odt to markdown/.md, or mentions pandoc.
---

# pandoc-convert — conversion HTML/ODT -> Markdown via pandoc

Installation portable dans `C:\Users\josel\softs_portable\pandoc-3.8.3\pandoc.exe` (v3.8.3), pas sur le PATH.

## Usage

HTML -> Markdown (GFM) :
```
"C:\Users\josel\softs_portable\pandoc-3.8.3\pandoc.exe" -f html -t gfm --wrap=none <entree.html> -o <sortie.md>
```

ODT -> Markdown (GFM) :
```
"C:\Users\josel\softs_portable\pandoc-3.8.3\pandoc.exe" -f odt -t gfm --wrap=none --extract-media=<dossier_media> <entree.odt> -o <sortie.md>
```

(en Git Bash : mêmes chemins avec `/`)

## Images embarquées

- **HTML** : pandoc convertit `<img src="...">` en lien markdown `![alt](src)` mais ne télécharge rien — c'est juste une référence (URL relative ou absolue vers la page source). Télécharger chaque image séparément (curl) et réécrire les liens vers les copies locales.
- **ODT** : les images embarquées dans le document sont de vrais octets dans le conteneur ODT (zip). Toujours passer `--extract-media=<dossier_media>` : pandoc les extrait dans ce dossier et réécrit les liens markdown en conséquence. Sans ce flag, les liens pointent vers un chemin interne au zip qui n'existe pas sur disque.

## Notes

- `--wrap=none` évite que pandoc ne redécoupe les paragraphes en lignes fixes (plus lisible, plus facile à diffser).
- Tableaux complexes (cellules fusionnées) : pas de garantie de rendu parfait, vérifier la sortie si le document source en contient.
- Binaire autonome, aucune dépendance Python ni venv à activer.
- Cible d'usage typique : ingestion dans le wiki LLM (skill `karpathy-llm-wiki`), qui archive systématiquement le fichier source original à côté du `.md` converti (voir sa règle sur les sources converties).
