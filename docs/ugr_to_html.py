import json

JSON_STRING = '{"reflectance_configs":[{"id":0,"ceiling":0.7,"walls":0.5,"plane":0.2},{"id":1,"ceiling":0.7,"walls":0.3,"plane":0.2},{"id":2,"ceiling":0.5,"walls":0.5,"plane":0.2},{"id":3,"ceiling":0.5,"walls":0.3,"plane":0.2},{"id":4,"ceiling":0.3,"walls":0.3,"plane":0.2}],"room_index":[[2,2],[2,3],[2,4],[2,6],[2,8],[2,12],[4,2],[4,3],[4,4],[4,6],[4,8],[4,12],[8,4],[8,6],[8,8],[8,12],[12,4],[12,6],[12,8]],"values":[[17.1,18.2,17.5,18.5,18.8,19.9,21.0,20.3,21.3,21.6],[17.5,18.4,17.8,18.7,19.1,19.9,20.9,20.3,21.2,21.6],[17.6,18.5,18.0,18.8,19.2,19.9,20.8,20.3,21.2,21.5],[17.7,18.5,18.1,18.9,19.3,19.9,20.7,20.4,21.1,21.5],[17.7,18.5,18.2,18.9,19.3,19.9,20.7,20.4,21.1,21.5],[17.7,18.4,18.1,18.8,19.2,19.9,20.6,20.4,21.0,21.4],[17.1,17.9,17.5,18.3,18.7,19.7,20.6,20.1,21.0,21.3],[17.5,18.2,17.9,18.6,19.0,19.8,20.5,20.2,20.9,21.3],[17.7,18.4,18.2,18.8,19.2,19.9,20.5,20.3,20.9,21.4],[17.9,18.5,18.4,18.9,19.4,19.9,20.5,20.4,20.9,21.4],[17.9,18.4,18.4,18.9,19.3,19.9,20.4,20.4,20.9,21.4],[17.9,18.3,18.4,18.8,19.3,19.9,20.4,20.4,20.9,21.3],[17.7,18.2,18.2,18.7,19.1,19.8,20.3,20.3,20.7,21.2],[17.9,18.3,18.4,18.8,19.3,19.9,20.3,20.4,20.8,21.3],[17.9,18.3,18.5,18.8,19.3,19.9,20.3,20.5,20.8,21.3],[17.9,18.2,18.4,18.7,19.3,20.0,20.3,20.5,20.8,21.3],[17.7,18.1,18.2,18.6,19.1,19.7,20.2,20.2,20.6,21.1],[17.9,18.3,18.4,18.7,19.3,19.8,20.2,20.4,20.7,21.2],[17.9,18.2,18.4,18.7,19.3,19.9,20.2,20.4,20.7,21.3]]}'

HIGHLIGHT_CELLS = {(10, 0), (10, 5), (12, 0), (12, 5)}
ROW_GROUP_STARTS = {0, 6, 12, 16}


def pct(v):
    return str(int(round(v * 100)))


def ugr_json_to_html(json_str: str, highlight_cells: set = None, output_path: str = "ugr_table.html"):
    data = json.loads(json_str)
    rc_list = data["reflectance_configs"]
    room_index = data["room_index"]
    values = data["values"]

    if highlight_cells is None:
        highlight_cells = set()

    p = []

    p.append("""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>UGR Table</title>
<style>
  body {
    font-family: 'Segoe UI', Calibri, Arial, sans-serif;
    font-size: 12.5px;
    background: #eef2f6;
    display: flex;
    justify-content: center;
    padding: 36px 20px;
  }
  .wrapper { overflow-x: auto; }
  table {
    border-collapse: collapse;
    background: #fff;
    box-shadow: 0 3px 12px rgba(0,0,0,0.13);
  }
  caption {
    font-size: 13px;
    font-weight: 700;
    text-align: left;
    padding: 0 0 8px 2px;
    color: #22304a;
    letter-spacing: 0.02em;
  }
  th, td {
    border: 1px solid #c8d2dc;
    padding: 5px 12px;
    text-align: center;
    white-space: nowrap;
  }
  /* Label de réflectance (colonne gauche, lignes 1-3) */
  th.rho-label {
    background: #e5eaf0;
    font-weight: 600;
    color: #2c3e50;
    text-align: left;
    padding-left: 10px;
  }
  /* Valeurs de réflectance */
  th.rho-val {
    background: #e5eaf0;
    font-weight: 600;
    color: #2c3e50;
  }
  /* En-tête orientation (ligne 4) */
  th.orient {
    background: #d0dce8;
    font-style: italic;
    font-weight: 600;
    color: #1e3050;
    font-size: 11.5px;
  }
  /* En-tête Room size (ligne 4) */
  th.room-header {
    background: #e5eaf0;
    font-weight: 700;
    color: #1e3050;
    font-size: 12px;
    vertical-align: middle;
    text-align: center;
  }
  /* Cellules de dimension locale */
  td.label {
    background: #f0f4f8;
    font-weight: 600;
    color: #2c3e50;
  }
  /* Valeurs UGR */
  td.value {
    color: #1a1a2e;
  }
  /* Séparateur vertical orientations */
  .sep-left {
    border-left: 2px solid #7a8fa6 !important;
  }
  /* Séparateur horizontal groupes X/H */
  tr.row-sep > td, tr.row-sep > th {
    border-top: 2px solid #7a8fa6 !important;
  }
  /* Surbrillance */
  td.highlight {
    background-color: #ffe566 !important;
    font-weight: 700;
    color: #7a4800;
  }
</style>
</head>
<body>
<div class="wrapper">
<table>
<caption>UGR Table &mdash; Unified Glare Rating</caption>
<thead>
""")

    # --- Ligne 1 : ρ Ceiling ---
    # col 0-1 : cellule "ρ Ceiling" (rowspan=1, colspan=2 pour couvrir X et Y)
    # col 2-6 : 5 valeurs ceiling crosswise
    # col 7-11 : 5 valeurs ceiling endwise
    p.append("<tr>")
    p.append('<th class="rho-label" colspan="2">&#961; Ceiling</th>')
    for orient_idx in range(2):
        for i, rc in enumerate(rc_list):
            cls = "rho-val sep-left" if (orient_idx == 1 and i == 0) else "rho-val"
            p.append(f'<th class="{cls}">{pct(rc["ceiling"])}</th>')
    p.append("</tr>\n")

    # --- Ligne 2 : ρ Walls ---
    p.append("<tr>")
    p.append('<th class="rho-label" colspan="2">&#961; Walls</th>')
    for orient_idx in range(2):
        for i, rc in enumerate(rc_list):
            cls = "rho-val sep-left" if (orient_idx == 1 and i == 0) else "rho-val"
            p.append(f'<th class="{cls}">{pct(rc["walls"])}</th>')
    p.append("</tr>\n")

    # --- Ligne 3 : ρ Floor ---
    p.append("<tr>")
    p.append('<th class="rho-label" colspan="2">&#961; Floor</th>')
    for orient_idx in range(2):
        for i, rc in enumerate(rc_list):
            cls = "rho-val sep-left" if (orient_idx == 1 and i == 0) else "rho-val"
            p.append(f'<th class="{cls}">{pct(rc["plane"])}</th>')
    p.append("</tr>\n")

    # --- Ligne 4 : Room size | Orientations ---
    p.append("<tr>")
    p.append('<th class="room-header">Room size<br>X &nbsp;&nbsp; Y</th>')
    # La cellule room-header couvre 2 colonnes (X et Y sont fusionnés ici en 1 th avec colspan=2 ci-dessus)
    # mais dans le tbody on a 2 td distinctes -> on met colspan=2 pour room-header
    # Correction : on utilise colspan=2 pour la cellule Room size dans cette ligne
    # (déjà fait ci-dessus avec colspan=1 -> à corriger)
    # On reconstruit :
    p.pop()  # retire le th room-header mal formé
    p.pop()  # retire le <tr>
    p.append("<tr>")
    p.append('<th class="room-header" colspan="2">Room size<br><span style="display:inline-block;width:36px">X</span>Y</th>')
    p.append('<th class="orient" colspan="5">Viewing direction at right angles (crosswise)</th>')
    p.append('<th class="orient sep-left" colspan="5">Viewing direction parallel (endwise)</th>')
    p.append("</tr>\n")

    p.append("</thead>\n<tbody>\n")

    # --- Lignes de données ---
    for row_idx, (x, y) in enumerate(room_index):
        row_cls = ' class="row-sep"' if row_idx in ROW_GROUP_STARTS else ""
        p.append(f"<tr{row_cls}>")
        p.append(f'<td class="label">{x}H</td>')
        p.append(f'<td class="label">{y}H</td>')
        for col_idx in range(10):
            val = values[row_idx][col_idx]
            is_hl = (row_idx, col_idx) in highlight_cells
            is_sep = col_idx == 5

            if is_hl and is_sep:
                cls = "highlight sep-left"
            elif is_hl:
                cls = "highlight"
            elif is_sep:
                cls = "value sep-left"
            else:
                cls = "value"

            p.append(f'<td class="{cls}">{val:.1f}</td>')
        p.append("</tr>\n")

    p.append("</tbody>\n</table>\n</div>\n</body>\n</html>")

    html = "".join(p)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Fichier généré : {output_path}")
    return html


if __name__ == "__main__":
    ugr_json_to_html(JSON_STRING, highlight_cells=HIGHLIGHT_CELLS, output_path="/home/claude/ugr_table.html")
