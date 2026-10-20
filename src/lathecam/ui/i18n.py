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
        "toolbar.simulate": "▶ Simulate Toolpath",
        "toolbar.tool_library": "🛠 Tool Library",
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

        # Tool Turret Dock & Library Editor
        "tools.dock_title": "Tool Turret Library (ISO)",
        "tools.col_pocket": "Pocket",
        "tools.col_desc": "Description",
        "tools.col_shape": "Shape",
        "tools.col_nose_r": "Nose R",
        "tools.col_ic": "IC (mm)",
        "tools.col_angles": "Clearance / Lead",
        "tools.col_orient": "Orient (Q)",
        "tools.lib_title": "Tool Turret & ISO Insert Library Editor",
        "tools.btn_edit_lib": "🛠 Tool Library Editor",
        "tools.turret_header": "Turret Pockets & Library",
        "tools.btn_add_tool": "➕ Add Tool",
        "tools.btn_duplicate": "📋 Duplicate",
        "tools.btn_delete_tool": "✕ Delete",
        "tools.btn_reset_defaults": "↺ Defaults",
        "tools.group_dimensions": "ISO Insert Geometry & Dimensions",
        "tools.iso_preset": "ISO Standard Preset:",
        "tools.preset_custom": "— Custom Dimensions —",
        "tools.pocket_name": "Pocket & Name:",
        "tools.shape_hand": "ISO Shape & Hand:",
        "tools.dimensions": "Dimensions (IC, s, rε):",
        "tools.cut_limits": "Edge & Cutting Limits:",
        "tools.angles_orient": "Angles & Orient (Q):",
        "tools.import_lib": "📁 Import Library (.json)",
        "tools.export_lib": "💾 Export Library (.json)",
        "common.cancel": "Cancel",
        "common.apply_and_close": "Apply to Project",

        # Tool Parameter Labels
        "tools.param_ic": "IC (d):",
        "tools.param_thickness": "Thickness (s):",
        "tools.param_nose_r": "Nose (rε):",
        "tools.param_edge_len": "Edge (l):",
        "tools.param_tip_width": "Width (w):",
        "tools.param_max_doc": "Max DOC:",
        "tools.param_lead_angle": "Lead (κr):",
        "tools.param_clearance": "Clearance (α):",
        "tools.param_orient": "Orient:",

        # Tool Hand
        "tools.hand_r": "Right Hand (R)",
        "tools.hand_l": "Left Hand (L)",
        "tools.hand_n": "Neutral (N)",

        # Tool Orientations
        "tools.orient_q1": "Q1 (+Z, +X)",
        "tools.orient_q2": "Q2 (-Z, +X)",
        "tools.orient_q3": "Q3: OD Turning Right-Hand (-Z, -X)",
        "tools.orient_q4": "Q4 (+Z, -X)",
        "tools.orient_q5": "Q5 (+Z, 0)",
        "tools.orient_q6": "Q6 (0, +X)",
        "tools.orient_q7": "Q7: Axial Drill (-Z, 0)",
        "tools.orient_q8": "Q8: Facing / Threading (0, -X)",
        "tools.orient_q9": "Q9: Round / Centerline (0, 0)",

        # ISO Shapes
        "tools.shape_c": "80° Rhombic / Diamond (CNMG, CCMT)",
        "tools.shape_d": "55° Rhombic / Diamond (DNMG, DCMT)",
        "tools.shape_v": "35° Rhombic / Diamond (VNMG, VBMT)",
        "tools.shape_w": "80° Trigon (WNMG)",
        "tools.shape_t": "60° Triangular (TNMG, TCMT)",
        "tools.shape_s": "90° Square (SNMG, SCMT)",
        "tools.shape_r": "Round / Circular (RNMG, RCMT)",
        "tools.shape_k": "55° Parallelogram (KNUX)",
        "tools.shape_part": "Parting & Grooving Blade",
        "tools.shape_thread": "60° External/Internal Threading",
        "tools.shape_drill": "Axial Twist / Center Drill",

        # Tool Library Dialog Messages
        "tools.msg_pocket_collision_title": "Pocket Collision",
        "tools.msg_pocket_collision": "Pocket T{tool_id} already exists!",
        "tools.msg_delete_min_title": "Delete Tool",
        "tools.msg_delete_min": "At least one tool must remain in the library.",
        "tools.msg_reset_title": "Reset Turret",
        "tools.msg_reset_confirm": "Reset all tools in the library to standard defaults (CNMG, DNMG, VNMG, Parting, Threading, Drill)?",
        "tools.msg_export_title": "Export Tool Library",
        "tools.msg_export_success_title": "Export Successful",
        "tools.msg_export_success": "Saved {count} tools to {name}.",
        "tools.msg_import_title": "Import Tool Library",
        "tools.msg_import_success_title": "Import Successful",
        "tools.msg_import_success": "Imported {count} tools from {name}.",
        "tools.msg_import_error_title": "Import Error",
        "tools.msg_import_error": "Failed to import tool library:\n{err}",

        # 2D Blueprint Preview
        "tools.preview_tip": "Tip (0, 0)",
        "tools.preview_width": "Width",
        "tools.preview_thickness": "Thickness (s)",
        "tools.preview_ic": "IC",
        "tools.preview_nose_r": "Nose (rε)",
        "tools.preview_lead": "Lead",
        "tools.preview_clearance": "Clearance",
        "tools.preview_orient": "Orient",

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

        # Simulation Bar
        "sim.btn_play": "▶ Play",
        "sim.btn_pause": "⏸ Pause",
        "sim.btn_stop": "⏹ Stop",
        "sim.step_back": "⏮ Step Back",
        "sim.step_fwd": "⏭ Step Fwd",
        "sim.speed": "Speed",
        "sim.idle": "Simulation Ready",
        "sim.finished": "Simulation Finished",
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
        "toolbar.simulate": "▶ Simuler Parcours",
        "toolbar.tool_library": "🛠 Bibliothèque d'Outils",
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
        "tree.ops_folder": "🛠 Gamme d'Usinage Tournage ({dialect})",
        "tree.ops_count": "{count} Opér.",
        "tree.cmds_count": "T{tool_id} • {count} inst.",

        # Property Inspector Dock
        "props.dock_title": "Inspecteur de Propriétés",
        "props.stock_group": "Configuration du Brut & Limites Tour",
        "props.stock_od": "Ø Extérieur Brut (OD) :",
        "props.stock_id": "Ø Alésage Intérieur (ID) :",
        "props.stock_z_start": "Surépaisseur Dressage Face (Z+) :",
        "props.stock_z_end": "Garde Mandrin / Butée (Z-) :",
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
        "props.lbl_doc": "Profondeur de Passe (ap) :",
        "props.lbl_allowance": "Surépaisseur Finition :",
        "props.lbl_feed": "Avance par Tour (fn - G95) :",
        "props.lbl_css": "Vitesse de Coupe (Vc - G96 S) :",
        "props.lbl_max_rpm": "Vitesse Broche Max (G96 D) :",
        "props.lbl_comp": "Compensation Rayon de Bec :",
        "props.lbl_pitch": "Pas de Filetage (P) :",
        "props.lbl_peck": "Débourrage Perçage (Q) :",
        "props.comp_computer": "Calculée FAO (PyClipper)",
        "props.comp_controller": "Armoire CNC (G41/G42)",
        "props.sim_group": "Vérification Matière & Collisions",
        "props.lbl_rest_area": "Matière Restante :",
        "props.lbl_gouge_check": "Contrôle Talonnement :",
        "props.gouge_detected": "⚠ COLLISION DÉTECTÉE ({area:.3f} mm²)",
        "props.collision_free": "✓ Sans Collision / Conforme (0.000 mm²)",
        "props.btn_recalc": "⟳ Recalculer Trajectoires && G-Code",

        # Face Action Bar & Context Menu
        "face.menu_header": "🎯 Assigner une Opération de Tournage à {label}",
        "face.act_rough": "➕ Ébauche Chariotage de cette Face",
        "face.act_finish": "➕ Finition Chariotage de cette Face",
        "face.act_thread": "➕ Filetage Extérieur (Cycle G76)",
        "face.act_part": "➕ Gorge / Tronçonnage Épaulement",
        "face.act_clear": "✕ Désélectionner la Face",

        # Tool Turret Dock & Library Editor
        "tools.dock_title": "Tourelle Outils & Plaquettes ISO",
        "tools.col_pocket": "Poste",
        "tools.col_desc": "Désignation",
        "tools.col_shape": "Forme ISO",
        "tools.col_nose_r": "Rayon rε",
        "tools.col_ic": "IC (mm)",
        "tools.col_angles": "Dépouille / Dir.",
        "tools.col_orient": "Quadrant (Q)",
        "tools.lib_title": "Éditeur de Bibliothèque d'Outils de Tournage & Plaquettes ISO",
        "tools.btn_edit_lib": "🛠 Éditeur de Bibliothèque",
        "tools.turret_header": "Postes de Tourelle & Outils",
        "tools.btn_add_tool": "➕ Ajouter Outil",
        "tools.btn_duplicate": "📋 Dupliquer",
        "tools.btn_delete_tool": "✕ Supprimer",
        "tools.btn_reset_defaults": "↺ Défauts Usine",
        "tools.group_dimensions": "Géométrie & Dimensions de Plaquette ISO",
        "tools.iso_preset": "Préréglage Standard ISO :",
        "tools.preset_custom": "— Dimensions Personnalisées —",
        "tools.pocket_name": "Poste & Désignation :",
        "tools.shape_hand": "Forme ISO & Sens de Coupe :",
        "tools.dimensions": "Dimensions Plaquette (IC, s, rε) :",
        "tools.cut_limits": "Arête Utile & Limites de Coupe :",
        "tools.angles_orient": "Angles de Coupe & Orientation (Q) :",
        "tools.import_lib": "📁 Importer Bibliothèque (.json)",
        "tools.export_lib": "💾 Exporter Bibliothèque (.json)",
        "common.cancel": "Annuler",
        "common.apply_and_close": "Appliquer au Projet",

        # Tool Parameter Labels
        "tools.param_ic": "Cercle inscrit IC (d) :",
        "tools.param_thickness": "Épaisseur plaquette (s) :",
        "tools.param_nose_r": "Rayon de bec (rε) :",
        "tools.param_edge_len": "Longueur d'arête (l) :",
        "tools.param_tip_width": "Largeur tronçonnage (w) :",
        "tools.param_max_doc": "Passe max (ap) :",
        "tools.param_lead_angle": "Angle d'attaque (κr) :",
        "tools.param_clearance": "Angle de dépouille (α) :",
        "tools.param_orient": "Orientation (Q) :",

        # Tool Hand
        "tools.hand_r": "À droite (R)",
        "tools.hand_l": "À gauche (L)",
        "tools.hand_n": "Neutre (N)",

        # Tool Orientations
        "tools.orient_q1": "Q1 (+Z, +X)",
        "tools.orient_q2": "Q2 (-Z, +X)",
        "tools.orient_q3": "Q3 : Tournage extérieur à droite (-Z, -X)",
        "tools.orient_q4": "Q4 (+Z, -X)",
        "tools.orient_q5": "Q5 (+Z, 0)",
        "tools.orient_q6": "Q6 (0, +X)",
        "tools.orient_q7": "Q7 : Perçage axial (-Z, 0)",
        "tools.orient_q8": "Q8 : Dressage / Filetage (0, -X)",
        "tools.orient_q9": "Q9 : Plaquette ronde / Axe neutre (0, 0)",

        # ISO Shapes
        "tools.shape_c": "Losange 80° (CNMG, CCMT)",
        "tools.shape_d": "Losange 55° (DNMG, DCMT)",
        "tools.shape_v": "Losange 35° (VNMG, VBMT - Finition)",
        "tools.shape_w": "Trigone 80° (WNMG)",
        "tools.shape_t": "Triangulaire 60° (TNMG, TCMT)",
        "tools.shape_s": "Carrée 90° (SNMG, SCMT)",
        "tools.shape_r": "Ronde / Bouton (RNMG, RCMT)",
        "tools.shape_k": "Parallélogramme 55° (KNUX - Copiage)",
        "tools.shape_part": "Lame à gorge & tronçonnage",
        "tools.shape_thread": "Plaquette filetage 60° (16ER/16IR)",
        "tools.shape_drill": "Foret hélicoïdal / Foret à centrer",

        # Tool Library Dialog Messages
        "tools.msg_pocket_collision_title": "Conflit de Poste",
        "tools.msg_pocket_collision": "Le poste T{tool_id} existe déjà dans la tourelle !",
        "tools.msg_delete_min_title": "Suppression d'Outil",
        "tools.msg_delete_min": "Au moins un outil de tournage doit rester dans la bibliothèque.",
        "tools.msg_reset_title": "Réinitialiser la Tourelle",
        "tools.msg_reset_confirm": "Réinitialiser tous les outils de la tourelle aux standards usine (CNMG, DNMG, VNMG, Tronçonnage, Filetage, Perçage) ?",
        "tools.msg_export_title": "Exporter la Bibliothèque d'Outils",
        "tools.msg_export_success_title": "Exportation Réussie",
        "tools.msg_export_success": "{count} outils de tournage enregistrés avec succès dans {name}.",
        "tools.msg_import_title": "Importer une Bibliothèque d'Outils",
        "tools.msg_import_success_title": "Importation Réussie",
        "tools.msg_import_success": "{count} outils importés avec succès depuis {name}.",
        "tools.msg_import_error_title": "Erreur d'Importation",
        "tools.msg_import_error": "Échec de l'importation de la bibliothèque :\n{err}",

        # 2D Blueprint Preview
        "tools.preview_tip": "Bec (0, 0)",
        "tools.preview_width": "Largeur",
        "tools.preview_thickness": "Épaisseur (s)",
        "tools.preview_ic": "IC",
        "tools.preview_nose_r": "Rayon (rε)",
        "tools.preview_lead": "Dir. d'attaque",
        "tools.preview_clearance": "Dépouille",
        "tools.preview_orient": "Orient",

        # G-Code Preview Dock
        "gcode.dock_title": "Sortie G-Code Post-Processeur Tournage",
        "gcode.btn_copy": "📋 Copier",
        "gcode.btn_export": "💾 Exporter",
        "gcode.stats": "Plan G18 ZX • {count} Lignes",

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
            "<span style='color:#0891b2; font-weight:bold;'>━━ G2/G3 Interpolation Circulaire</span> &nbsp;&nbsp;"
            "<span style='color:#ca8a04; font-weight:bold;'>━━ G76/G33 Filetage</span>"
        ),

        # Simulation Bar
        "sim.btn_play": "▶ Lecture",
        "sim.btn_pause": "⏸ Pause",
        "sim.btn_stop": "⏹ Arrêt",
        "sim.step_back": "⏮ Reculer",
        "sim.step_fwd": "⏭ Avancer",
        "sim.speed": "Vitesse",
        "sim.idle": "Simulation Prête",
        "sim.finished": "Simulation Terminée",
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
