# Multi-Agent Bias Output Browser

A static React interface for exploring and downloading saved outputs from BBQ, CBBQ, and KoBBQ experiments under three conditions:

- Single Agent
- Multi-Agent Without Revision
- Multi-Agent With Revision

The website does not call any model at runtime. It converts `stages.jsonl`, `item_level_results.csv`, and the original split CSV files into browser-ready JSON and downloadable archives.

## Live Site

https://bae-hyunwoo.github.io/multiagent-bias-output-browser/

## 1. Import Existing Experiment Data

Copy the complete experiment output folder into this project. Do not move or delete the original files.

```text
Source:
C:\Users\samsung-user\Desktop\multiagent_bias_experiment\outputs\runs\split001

Destination:
<project-root>\source_data\outputs\split001
```

The split CSV is also required to display the original context, question, and answer options.

```text
Source:
C:\Users\samsung-user\Desktop\multiagent_bias_experiment\data\splits\bbq_cbbq_kobbq_pair20_split001.csv

Destination:
<project-root>\source_data\splits\bbq_cbbq_kobbq_pair20_split001.csv
```

The easiest method is to run the following command from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\import_split001.ps1
```

This script copies the data from the source locations above.

## 2. Generate UI Data

```powershell
.\scripts\rebuild_data.ps1
```

The generated files are written mainly to:

```text
public\data\
public\downloads\
```

The standard download archives include the questions, item-level results, and nine-stage outputs.

To include `raw_calls.jsonl` in an additional large archive, run:

```powershell
.\scripts\rebuild_data.ps1 -IncludeRawZip
```

Large raw archives should not be committed directly to the GitHub repository.

## 3. Install Packages

Run once after cloning the repository:

```powershell
.\scripts\setup.ps1
```

## 4. Run Locally

Development mode:

```powershell
.\scripts\run_local.ps1
```

Static build mode:

```powershell
.\scripts\run_static.ps1
```

The local site is normally available at:

```text
http://localhost:5173
```

## 5. Interface Structure

```text
BBQ / CBBQ / KoBBQ
  └─ Category folders
      └─ Problem list
          ├─ Ambiguous / Disambiguated variant
          ├─ Model selection
          ├─ Single Agent
          ├─ Multi-Agent Without Revision
          └─ Multi-Agent With Revision
```

Individual problems can be downloaded as JSON or CSV. Category and dataset results are available as ZIP archives, and the home page provides the complete processed-results archive.

## 6. GitHub Pages Deployment

The site is deployed automatically through GitHub Actions whenever a commit is pushed to the `main` branch.

The deployment workflow is:

```text
.github/workflows/build.yml
```

GitHub Pages must use the following repository setting:

```text
Settings → Pages → Build and deployment → Source: GitHub Actions
```

The production build uses the repository base path:

```text
/multiagent-bias-output-browser/
```

## 7. Add Another Split

Add the next output folder and split CSV:

```text
source_data\outputs\split002
source_data\splits\bbq_cbbq_kobbq_pair20_split002.csv
```

Then regenerate the browser data:

```powershell
.\scripts\rebuild_data.ps1
```

Multiple splits are merged automatically into the same interface.

## 8. Main Files

```text
scripts/build_ui_data.py            Converts experiment outputs into UI JSON and ZIP files
scripts/validate_ui_data.py         Validates generated file paths and manifests
src/pages/HomePage.tsx              Dataset and category browser
src/pages/DatasetPage.tsx           Dataset-level category view
src/pages/CategoryPage.tsx          Redirects a category to its first problem
src/pages/ProblemPage.tsx           Problem selector and detailed result view
src/components/ConditionViewer.tsx  Displays the three agent-result conditions
```
