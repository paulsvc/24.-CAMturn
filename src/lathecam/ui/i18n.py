from __future__ import annotations

_CURRENT_LANG: str = "en"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # Window & Toolbar
        "window.title": "LatheCAM — CNC Turning CAD/CAM Workbench (LinuxCNC G18 / G7)",
        "toolbar.import_cad": "📂 Import CAD",
        "toolbar.open_lcam": "📁 Open .lcam",
        "toolbar.save_lcam": "💾 Save .lcam",
        "toolbar.load_demo": "⚙ Demo Shaft",
        "toolbar.view_all": "👁 All Ops",
        "toolbar.add_face": "➕ Face",
        "toolbar.add_rough": "➕ Rough",
        "toolbar.add_finish": "➕ Finish",
        "toolbar.add_thread": "➕ Thread G76",
        "toolbar.add_drill": "➕ Drill G83",
        "toolbar.add_part": "➕ Part-Off",
        "toolbar.post_gcode": "💾 Post G-Code",
        "toolbar.theme_dark": "🌙 Dark Theme",
        "toolbar.theme_light": "☀️ White Theme",
        "toolbar.lang_label": "🌐",

        # Status Bar
        "status.ready": "Ready • Kernel: Shapely 2.2 (GEOS) + PyClipper • Post: LinuxCNC G18 ZX Plane / G7 Diameter Mode",
        "status.inspecting": "Inspecting {name} • Tool T{tool_id} • {count} MotionCmds",
        "status.inspecting_face": "Selected {label} • Z=[{z_max:.1f} → {z_min:.1f}mm] • Right-click or use Face Actions to assign operation",
        "status.showing_all": "Showing all enabled operations for '{name}'",
        "status.demo_loaded": "Loaded Stepped Threaded Drive Shaft Demo Project",
        "status.dialect_switched": "Switched Post-Processor Dialect to: {dialect}",
        "status.project_loaded": "Loaded project from {path}",
        "status.project_saved": "Saved project to {path}",
        "status.cad_imported": "Successfully imported {name} ({count} profile points)",
        "status.gcode_exported": "Exported G-Code to {path}",
        "status.theme_changed": "Switched UI appearance to {theme} theme",
        "status.lang_changed": "Language switched to English",

        # Feature Tree Dock
        "tree.dock_title": "FeatureManager Tree",
        "tree.col_feature": "Feature / Operation",
        "tree.col_status": "Tool / Status",
        "tree.btn_up": "▲ Up",
        "tree.btn_down": "▼ Down",
        "tree.btn_remove": "✕ Remove",
        "tree.stock_node": "📦 Stock Cylinder",
        "tree.profile_node": "📐 2D Turning Silhouette",
        "tree.faces_folder": "🎯 CAD Machinable Faces",
        "tree.faces_count": "{count} Faces",
        "tree.ops_folder": "🛠 Turning Setup ({dialect})",
        "tree.ops_count": "{count} Ops",
        "tree.cmds_count": "T{tool_id} • {count} cmds",

        # Property Inspector Dock
        "props.dock_title": "Property Inspector",
        "props.stock_group": "Workpiece Stock Setup",
        "props.stock_od": "Stock Outer Ø (OD):",
        "props.stock_id": "Stock Inner Ø (ID):",
        "props.stock_z_start": "Face Allowance (Z+):",
        "props.stock_z_end": "Chuck Limit (Z-):",
        "props.op_group": "Selected CAM Operation",
        "props.all_ops_overview": "All Operations (Full Setup)",
        "props.lbl_op": "Operation:",
        "props.lbl_scope": "Geometry Scope:",
        "props.scope_all": "Full Workpiece Profile",
        "props.scope_face": "Selected Face / Z-Bounds",
        "props.lbl_target_face": "Target CAD Face:",
        "props.face_custom": "Custom Z-Range",
        "props.lbl_z_bounds": "Cut Z Bounds:",
        "props.lbl_tool": "Turret Tool:",
        "props.lbl_doc": "Depth of Cut (DOC):",
        "props.lbl_allowance": "Finish Allowance:",
        "props.lbl_feed": "Feed Rate (G95):",
        "props.lbl_css": "CSS Speed (G96 S):",
        "props.lbl_max_rpm": "Max Spindle (G96 D):",
        "props.lbl_comp": "Nose Comp Mode:",
        "props.lbl_pitch": "Thread Pitch (P):",
        "props.lbl_peck": "Peck Depth (Q):",
        "props.comp_computer": "Computer TNRC (PyClipper)",
        "props.comp_controller": "Controller Comp (G41/G42)",
        "props.sim_group": "2D Shapely Verification",
        "props.lbl_rest_area": "Uncut Rest Area:",
        "props.lbl_gouge_check": "Gouge Check:",
        "props.gouge_detected": "⚠ GOUGE DETECTED ({area:.3f} mm²)",
        "props.collision_free": "✓ Collision-Free (0.000 mm²)",
        "props.btn_recalc": "⟳ Recalculate Toolpaths && G-Code",

        # Face Action Bar & Context Menu
        "face.menu_header": "🎯 Assign Operation to {label}",
        "face.act_rough": "➕ OD Rough This Face",
        "face.act_finish": "➕ OD Finish This Face",
        "face.act_thread": "➕ Thread This Cylinder (G76)",
        "face.act_part": "➕ Groove / Part at Shoulder",
        "face.act_clear": "✕ Clear Face Selection",

        # Tool Turret Dock
        "tools.dock_title": "Tool Turret Library (ISO)",
        "tools.col_pocket": "Pocket",
        "tools.col_desc": "Description",
        "tools.col_shape": "Shape",
        "tools.col_nose_r": "Nose R",
        "tools.col_angles": "Clearance / Lead",
        "tools.col_orient": "Orient (Q)",

        # G-Code Preview Dock
        "gcode.dock_title": "G-Code Post-Processor Output",
        "gcode.btn_copy": "📋 Copy",
        "gcode.btn_export": "💾 Export",
        "gcode.stats": "G18 ZX • {count} Lines",

        # Viewport HUD
        "viewport.btn_iso": "🧊 3D Isometric",
        "viewport.btn_zx": "📐 2D ZX Lathe Plane",
        "viewport.btn_pick_on": "🎯 Pick Face: ON",
        "viewport.btn_pick_off": "🎯 Pick Face: OFF",
        "viewport.btn_stock_on": "📦 Stock: ON",
        "viewport.btn_stock_off": "📦 Stock: OFF",
        "viewport.btn_sim_on": "🔬 Cut Sim: ON",
        "viewport.btn_sim_off": "🔬 Cut Sim: OFF",
        "viewport.legend": (
            "<span style='color:#ef4444; font-weight:bold;'>━━ G0 Rapid</span> &nbsp;&nbsp;"
            "<span style='color:#16a34a; font-weight:bold;'>━━ G1 Linear Cut</span> &nbsp;&nbsp;"
            "<span style='color:#0891b2; font-weight:bold;'>━━ G2/G3 Arc</span> &nbsp;&nbsp;"
            "<span style='color:#ca8a04; font-weight:bold;'>━━ G76/G33 Thread</span>"
        ),
    },
    "fr": {
        # Window & Toolbar
        "window.title": "LatheCAM — Atelier CAO/FAO de Tournage CNC (LinuxCNC G18 / G7)",
        "toolbar.import_cad": "📂 Importer CAO",
        "toolbar.open_lcam": "📁 Ouvrir .lcam",
        "toolbar.save_lcam": "💾 Sauver .lcam",
        "toolbar.load_demo": "⚙ Pièce Démo",
        "toolbar.view_all": "👁 Toutes Opér.",
        "toolbar.add_face": "➕ Dressage",
        "toolbar.add_rough": "➕ Ébauche",
        "toolbar.add_finish": "➕ Finition",
        "toolbar.add_thread": "➕ Filetage G76",
        "toolbar.add_drill": "➕ Perçage G83",
        "toolbar.add_part": "➕ Tronçonnage",
        "toolbar.post_gcode": "💾 Générer G-Code",
        "toolbar.theme_dark": "🌙 Thème Sombre",
        "toolbar.theme_light": "☀️ Thème Clair",
        "toolbar.lang_label": "🌐",

        # Status Bar
        "status.ready": "Prêt • Noyau : Shapely 2.2 (GEOS) + PyClipper • Post : LinuxCNC Plan ZX G18 / Mode Diamètre G7",
        "status.inspecting": "Inspection de {name} • Outil T{tool_id} • {count} blocs MotionCmd",
        "status.inspecting_face": "Face sélectionnée {label} • Z=[{z_max:.1f} → {z_min:.1f}mm] • Clic droit ou barre d'actions pour usiner cette face",
        "status.showing_all": "Affichage de toutes les opérations actives pour « {name} »",
        "status.demo_loaded": "Projet démo « Arbre Étagé Fileté » chargé avec succès",
        "status.dialect_switched": "Dialecte du post-processeur changé en : {dialect}",
        "status.project_loaded": "Projet chargé depuis {path}",
        "status.project_saved": "Projet enregistré dans {path}",
        "status.cad_imported": "Importation réussie de {name} ({count} points de profil)",
        "status.gcode_exported": "G-Code exporté vers {path}",
        "status.theme_changed": "Apparence basculée vers le thème {theme}",
        "status.lang_changed": "Langue basculée en Français",

        # Feature Tree Dock
        "tree.dock_title": "Arbre FeatureManager",
        "tree.col_feature": "Fonction / Opération",
        "tree.col_status": "Outil / État",
        "tree.btn_up": "▲ Monter",
        "tree.btn_down": "▼ Descendre",
        "tree.btn_remove": "✕ Supprimer",
        "tree.stock_node": "📦 Brut Cylindrique",
        "tree.profile_node": "📐 Profil de Tournage 2D",
        "tree.faces_folder": "🎯 Faces CAO Usinables",
        "tree.faces_count": "{count} Faces",
        "tree.ops_folder": "🛠 Gamme d'Usinage ({dialect})",
        "tree.ops_count": "{count} Opér.",
        "tree.cmds_count": "T{tool_id} • {count} inst.",

        # Property Inspector Dock
        "props.dock_title": "Inspecteur de Propriétés",
        "props.stock_group": "Configuration du Brut",
        "props.stock_od": "Ø Extérieur Brut (OD) :",
        "props.stock_id": "Ø Intérieur Brut (ID) :",
        "props.stock_z_start": "Surépaisseur Dressage (Z+) :",
        "props.stock_z_end": "Limite Mandrin (Z-) :",
        "props.op_group": "Opération FAO Sélectionnée",
        "props.all_ops_overview": "Toutes les Opérations (Gamme Complète)",
        "props.lbl_op": "Opération :",
        "props.lbl_scope": "Zone d'Usinage :",
        "props.scope_all": "Profil Complet de la Pièce",
        "props.scope_face": "Face Sélectionnée / Limites Z",
        "props.lbl_target_face": "Face CAO Cible :",
        "props.face_custom": "Plage Z Personnalisée",
        "props.lbl_z_bounds": "Limites Z Coupe :",
        "props.lbl_tool": "Outil Tourelle :",
        "props.lbl_doc": "Profondeur de Passe (DOC) :",
        "props.lbl_allowance": "Surépaisseur Finition :",
        "props.lbl_feed": "Avance par Tour (G95) :",
        "props.lbl_css": "Vitesse de Coupe (G96 S) :",
        "props.lbl_max_rpm": "Vitesse Broche Max (G96 D) :",
        "props.lbl_comp": "Compensation Rayon Bec :",
        "props.lbl_pitch": "Pas de Filetage (P) :",
        "props.lbl_peck": "Profondeur Débourrage (Q) :",
        "props.comp_computer": "Calculée FAO (PyClipper)",
        "props.comp_controller": "Armoire CNC (G41/G42)",
        "props.sim_group": "Vérification Géométrique 2D",
        "props.lbl_rest_area": "Matière Restante :",
        "props.lbl_gouge_check": "Contrôle Collision :",
        "props.gouge_detected": "⚠ COLLISION DÉTECTÉE ({area:.3f} mm²)",
        "props.collision_free": "✓ Sans Collision (0.000 mm²)",
        "props.btn_recalc": "⟳ Recalculer Trajectoires && G-Code",

        # Face Action Bar & Context Menu
        "face.menu_header": "🎯 Assigner une Opération à {label}",
        "face.act_rough": "➕ Ébaucher cette Face",
        "face.act_finish": "➕ Finir cette Face",
        "face.act_thread": "➕ Fileter ce Cylindre (G76)",
        "face.act_part": "➕ Gorge / Tronçonner ici",
        "face.act_clear": "✕ Désélectionner la Face",

        # Tool Turret Dock
        "tools.dock_title": "Bibliothèque d'Outils Tourelle (ISO)",
        "tools.col_pocket": "Poste",
        "tools.col_desc": "Désignation",
        "tools.col_shape": "Plaquette",
        "tools.col_nose_r": "Rayon R",
        "tools.col_angles": "Dépouille / Dir.",
        "tools.col_orient": "Orient. (Q)",

        # G-Code Preview Dock
        "gcode.dock_title": "Sortie G-Code Post-Processeur",
        "gcode.btn_copy": "📋 Copier",
        "gcode.btn_export": "💾 Exporter",
        "gcode.stats": "G18 ZX • {count} Lignes",

        # Viewport HUD
        "viewport.btn_iso": "🧊 Vue 3D Isométrique",
        "viewport.btn_zx": "📐 Plan 2D ZX Tour",
        "viewport.btn_pick_on": "🎯 Sélect. Face : OUI",
        "viewport.btn_pick_off": "🎯 Sélect. Face : NON",
        "viewport.btn_stock_on": "📦 Brut : OUI",
        "viewport.btn_stock_off": "📦 Brut : NON",
        "viewport.btn_sim_on": "🔬 Simu Coupe : OUI",
        "viewport.btn_sim_off": "🔬 Simu Coupe : NON",
        "viewport.legend": (
            "<span style='color:#ef4444; font-weight:bold;'>━━ G0 Rapide</span> &nbsp;&nbsp;"
            "<span style='color:#16a34a; font-weight:bold;'>━━ G1 Usinage</span> &nbsp;&nbsp;"
            "<span style='color:#0891b2; font-weight:bold;'>━━ G2/G3 Arc</span> &nbsp;&nbsp;"
            "<span style='color:#ca8a04; font-weight:bold;'>━━ G76/G33 Filetage</span>"
        ),
    },
}


def get_language() -> str:
    """Returns the active UI language code ('en' or 'fr')."""
    return _CURRENT_LANG


def set_language(lang: str) -> None:
    """Sets the active UI language code ('en' or 'fr')."""
    global _CURRENT_LANG
    if lang in TRANSLATIONS:
        _CURRENT_LANG = lang


def tr(key: str, **kwargs: object) -> str:
    """Translates a UI string key into the active language with optional formatting args."""
    table = TRANSLATIONS.get(_CURRENT_LANG, TRANSLATIONS["en"])
    template = table.get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
