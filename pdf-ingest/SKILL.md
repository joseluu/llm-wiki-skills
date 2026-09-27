---
name: pdf-ingest
description: Convert PDF documents to Markdown using docling, run via `uv run` (dependencies declared inline in the script, no venv to set up). Use when the user asks to convert PDF(s) to markdown/.md, extract text/tables from a PDF, or mentions docling or pdf-ingest.
---

# pdf-ingest — conversion PDF -> Markdown via docling

Le script companion `convert_pdfs.py` vit dans `scripts\` a cote de ce
SKILL.md et se lance via `uv run` — ses dependances (`docling`,
`python-dotenv`, `torch`) sont declarees en metadonnees PEP 723 en tete
du fichier ; `uv` resout et met en cache un environnement dedie tout
seul, aucun venv a preparer a la main.

## Usage

```
uv run C:\Users\josel\.claude\skills\pdf-ingest\scripts\convert_pdfs.py <repertoire_pdf> <repertoire_sortie_md>
```

(en Git Bash: `uv run` fonctionne identiquement avec des chemins `/`)

- Convertit tous les `*.pdf` du repertoire source, ecrit un `.md` par PDF
  (meme nom de base) dans le repertoire de sortie (cree si absent).
- Traite les fichiers du plus petit au plus gros (les gros/scannes sont
  plus lents a cause de l'OCR).
- Chaque PDF est converti dans un **sous-processus dedie** (le script se
  rappelle lui-meme avec `--single <pdf> <out.md>`) pour que la memoire
  (modeles torch + images de page) soit liberee par l'OS entre chaque
  fichier plutot que de s'accumuler sur tout le lot.
- Formules mathematiques decodees en LaTeX (`do_formula_enrichment=True`,
  modele `CodeFormulaV2` deja present dans le cache initial — voir plus
  bas) : rendues `$...$` (inline) / `$$...$$` (bloc) dans le markdown de
  sortie au lieu du placeholder `<!-- formula-not-decoded -->`.
- Images/figures du PDF extraites (`generate_picture_images=True` +
  `save_as_markdown(..., image_mode=REFERENCED)`) dans un dossier
  `<nom_pdf>_artifacts/` a cote du `.md`, referencees par liens relatifs
  — au lieu d'etre perdues comme avec `export_to_markdown()` seul.
- A la fin: `Termine: N/M conversions reussies.` + liste des echecs.

## Configuration (.env)

`HF_CACHE_DIR` (chemin machine-specifique vers le cache de modeles, voir
section suivante) est lu depuis un fichier `.env` a cote de ce SKILL.md,
**non versionne** (`.gitignore` du skill l'exclut). Copier `.env.template`
vers `.env` et adapter le chemin avant le premier usage sur une nouvelle
machine.

## Cache de modeles HuggingFace (offline-first)

`convert_pdfs.py` force `HF_HOME` vers `HF_CACHE_DIR` **avant**
d'importer `docling`/`huggingface_hub` (l'emplacement du cache est resolu
a l'import — le faire plus tard ne marche pas). Ce dossier a ete
initialise a partir d'un `models.tar` (export d'un cache HF recent,
~1 Go) fourni par l'utilisateur, extrait tel quel (structure standard
`models/hub/models--<org>--<name>/...`).

Modeles presents dans ce tar initial: `docling-project/CodeFormulaV2`,
`docling-project/docling-models` (tableformer fast+accurate),
`docling-project/DocumentFigureClassifier-v2.0`.

**Il manquait le modele de layout par defaut** (`docling-project/docling-layout-heron`)
et les modeles OCR (RapidOCR telecharge separement depuis modelscope.cn
vers `venv\Lib\site-packages\rapidocr\models\`, pas via le cache HF). Au
premier lancement ces pieces manquantes sont telechargees automatiquement
et viennent s'ajouter au meme cache local — les lancements suivants les
reutilisent sans reseau. Si le PC n'a pas d'acces reseau au tout premier
run, la conversion echouera sur le telechargement du layout model: pas de
mode strictement offline configure (`HF_HUB_OFFLINE` non force), c'est
voulu vu que le tar fourni etait incomplet.

## Contrainte memoire connue sur cette machine

Cette machine tourne souvent avec tres peu de RAM libre (Chrome a lui
seul peut consommer >10 Go sur 24 Go total). Docling + torch + OCR sur
CPU sont gourmands: un run a deja ete tue (`status: killed`, "low on
memory") meme sur le plus petit PDF du lot pendant le chargement du
modele de layout. L'isolation par sous-processus (voir plus haut) limite
la casse mais ne garantit pas de reussir si la RAM libre est descendue
sous ~1 Go. Si une conversion est tuee pour cause de memoire:

1. Verifier la RAM libre: `powershell -NoProfile -Command "Get-CimInstance Win32_OperatingSystem | Select FreePhysicalMemory"`
2. Identifier les gros consommateurs: `powershell -NoProfile -Command "Get-Process | Group-Object Name | Select Name,@{N='TotalMB';E={[math]::Round(($_.Group|Measure-Object WorkingSet -Sum).Sum/1MB)}} | Sort TotalMB -Descending | Select -First 10"`
3. **Ne pas fermer Chrome ou d'autres apps de l'utilisateur sans demander** —
   proposer de liberer de la memoire, ou relancer tel quel si l'utilisateur
   l'assume.

## Notes

- Repertoire de travail pas de depot git — pas de commit a faire ici.
- Le premier `uv run` resout et telecharge ~100 dependances (torch,
  transformers, opencv, etc.) — plusieurs minutes et plusieurs centaines
  de Mo. `uv` met ensuite ces wheels en cache (cache `uv` global, pas
  lie a ce repertoire) : les lancements suivants, meme depuis un autre
  script/projet demandant les memes paquets, reutilisent le cache et
  demarrent vite, sans reinstaller.
- Pour un autre repertoire source/sortie, juste relancer la commande
  Usage ci-dessus avec d'autres chemins — rien d'autre a reconfigurer.
