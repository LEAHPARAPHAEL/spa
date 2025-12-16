import tkinter as tk
from tkinter import ttk
import sqlite3
import requests
from PIL import Image, ImageTk
from io import BytesIO
import difflib
import webbrowser

# --- Matplotlib Imports ---
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- Database Manager ---
class DBManager:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row 
        self.cur = self.conn.cursor()

    def search_dogs(self, name=None, breed_query=None, categories=None, sexes=None, sources=None):
        sql = "SELECT id, name, source, age_text, matched_breed, breed, category FROM dogs WHERE 1=1"
        params = []

        if name:
            sql += " AND name LIKE ?"
            params.append(f"%{name}%")

        if categories:
            placeholders = ','.join(['?'] * len(categories))
            sql += f" AND category IN ({placeholders})"
            params.extend(categories)

        # --- FIX: Sex Filter (Robust 'Starts With' Logic) ---
        # If exactly one sex is selected, we filter. If 0 or 2, we show all.
        if sexes and len(sexes) == 1:
            target_sex = sexes[0] # Will be "Male" or "Female" passed from GUI
            
            if target_sex == "Male":
                # Match 'Male', 'Mâle', 'M', 'm', etc.
                sql += " AND (sex LIKE 'M%' OR sex LIKE 'm%')"
            elif target_sex == "Female":
                # Match 'Female', 'Femelle', 'F', 'f', etc.
                sql += " AND (sex LIKE 'F%' OR sex LIKE 'f%')"
            
        if sources:
            placeholders = ','.join(['?'] * len(sources))
            sql += f" AND source IN ({placeholders})"
            params.extend(sources)

        self.cur.execute(sql, params)
        rows = self.cur.fetchall()

        if not breed_query:
            return rows

        filtered_rows = []
        breed_query = breed_query.lower()
        for row in rows:
            b1 = row['breed'].lower() if row['breed'] else ""
            b2 = row['matched_breed'].lower() if row['matched_breed'] else ""
            ratio1 = difflib.SequenceMatcher(None, breed_query, b1).ratio()
            ratio2 = difflib.SequenceMatcher(None, breed_query, b2).ratio()
            if max(ratio1, ratio2) >= 0.6:
                filtered_rows.append(row)

        return filtered_rows

    def get_dog_details(self, dog_id):
        self.cur.execute("SELECT * FROM dogs WHERE id = ?", (dog_id,))
        return self.cur.fetchone()

    def get_dog_images(self, dog_id):
        self.cur.execute("SELECT image_url FROM images WHERE dog_id = ?", (dog_id,))
        return [row['image_url'] for row in self.cur.fetchall()]

    def get_breed_info(self, breed_name):
        if not breed_name: return None
        self.cur.execute("SELECT * FROM breeds WHERE breed_name = ?", (breed_name,))
        return self.cur.fetchone()

# --- Main GUI ---
class DogApp:
    def __init__(self, root):
        self.db = DBManager("data/shelters.db")
        self.root = root
        self.root.title("Shelter Dog Browser")
        self.root.geometry("1400x900")
        
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=('Arial', 10, 'bold'))

        self.current_dog_id = None 
        self.gallery_images = [] 

        # --- Layout ---
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 1. Left Panel (Filters)
        self.panel_left = tk.Frame(root, bg="#f0f0f0", width=260, padx=10, pady=10)
        self.panel_left.grid(row=0, column=0, sticky="ns")
        self.panel_left.grid_propagate(False)
        self.setup_filters()

        # 2. Right Panel (Container)
        self.container = tk.Frame(root, bg="white")
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        # Pages
        self.page_list = tk.Frame(self.container, bg="white")
        self.page_list.grid(row=0, column=0, sticky="nsew")
        self.setup_list_view()

        self.page_detail = tk.Frame(self.container, bg="white")
        self.page_detail.grid(row=0, column=0, sticky="nsew")
        self.setup_detail_view()

        self.page_breed = tk.Frame(self.container, bg="white")
        self.page_breed.grid(row=0, column=0, sticky="nsew")
        self.setup_breed_view()

        self.page_gallery = tk.Frame(self.container, bg="white")
        self.page_gallery.grid(row=0, column=0, sticky="nsew")
        self.setup_gallery_view()

        self.show_list_view()
        self.run_search()

    # ================= UI SETUP =================

    def setup_filters(self):
        tk.Label(self.panel_left, text="Find a Dog", font=("Arial", 16, "bold"), bg="#f0f0f0").pack(pady=(0, 15))
        
        # Keywords
        fr_kw = tk.LabelFrame(self.panel_left, text="Keywords", bg="#f0f0f0", font=("Arial", 9, "bold"), padx=5, pady=5)
        fr_kw.pack(fill="x", pady=(0, 10))
        tk.Label(fr_kw, text="Name:", bg="#f0f0f0").pack(anchor="w")
        self.entry_name = tk.Entry(fr_kw)
        self.entry_name.pack(fill="x", pady=(0, 5))
        tk.Label(fr_kw, text="Breed:", bg="#f0f0f0").pack(anchor="w")
        self.entry_breed = tk.Entry(fr_kw)
        self.entry_breed.pack(fill="x", pady=(0, 5))

        # Characteristics
        fr_char = tk.LabelFrame(self.panel_left, text="Characteristics", bg="#f0f0f0", font=("Arial", 9, "bold"), padx=5, pady=5)
        fr_char.pack(fill="x", pady=(0, 10))
        
        tk.Label(fr_char, text="Sex:", bg="#f0f0f0").pack(anchor="w")
        self.var_male = tk.BooleanVar()
        self.var_female = tk.BooleanVar()
        f_sex = tk.Frame(fr_char, bg="#f0f0f0")
        f_sex.pack(fill="x", pady=(0, 5))
        tk.Checkbutton(f_sex, text="Male", variable=self.var_male, bg="#f0f0f0").pack(side="left")
        tk.Checkbutton(f_sex, text="Female", variable=self.var_female, bg="#f0f0f0").pack(side="left", padx=10)

        tk.Label(fr_char, text="Age Category:", bg="#f0f0f0").pack(anchor="w")
        self.var_junior = tk.BooleanVar()
        self.var_adult = tk.BooleanVar()
        self.var_senior = tk.BooleanVar()
        f_cat = tk.Frame(fr_char, bg="#f0f0f0")
        f_cat.pack(fill="x", pady=(0, 5))
        tk.Checkbutton(f_cat, text="Junior", variable=self.var_junior, bg="#f0f0f0").pack(anchor="w")
        tk.Checkbutton(f_cat, text="Adult", variable=self.var_adult, bg="#f0f0f0").pack(anchor="w")
        tk.Checkbutton(f_cat, text="Senior", variable=self.var_senior, bg="#f0f0f0").pack(anchor="w")

        # Source
        fr_src = tk.LabelFrame(self.panel_left, text="Source", bg="#f0f0f0", font=("Arial", 9, "bold"), padx=5, pady=5)
        fr_src.pack(fill="x", pady=(0, 10))
        self.var_spa = tk.BooleanVar(value=True)
        self.var_sc = tk.BooleanVar(value=True)
        tk.Checkbutton(fr_src, text="SPA", variable=self.var_spa, bg="#f0f0f0").pack(anchor="w")
        tk.Checkbutton(fr_src, text="Seconde Chance", variable=self.var_sc, bg="#f0f0f0").pack(anchor="w")

        tk.Button(self.panel_left, text="Search", bg="#007bff", fg="white", font=("Arial", 10, "bold"), command=self.run_search).pack(fill="x", pady=10)
        tk.Button(self.panel_left, text="Reset Filters", command=self.reset_search).pack(fill="x")

    def setup_list_view(self):
        self.tree_scroll = ttk.Scrollbar(self.page_list)
        self.tree_scroll.pack(side="right", fill="y")
        self.tree = ttk.Treeview(self.page_list, columns=("ID", "Name", "Source", "Age"), show='headings', yscrollcommand=self.tree_scroll.set)
        
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Source", text="Source")
        self.tree.heading("Age", text="Age")
        self.tree.column("ID", width=0, stretch=False)
        self.tree.column("Name", width=200)
        self.tree.column("Source", width=200)
        self.tree.column("Age", width=100)
        
        self.tree.pack(fill="both", expand=True)
        self.tree_scroll.config(command=self.tree.yview)
        self.tree.bind("<Double-1>", self.open_dog_details)

    def setup_detail_view(self):
        head = tk.Frame(self.page_detail, bg="#e9ecef", height=50)
        head.pack(fill="x", side="top")
        tk.Button(head, text="< Back to List", command=self.show_list_view).pack(side="left", padx=10, pady=10)
        self.lbl_detail_title = tk.Label(head, text="Dog Name", font=("Arial", 16, "bold"), bg="#e9ecef")
        self.lbl_detail_title.pack(side="left", padx=20)

        content = tk.Frame(self.page_detail, bg="white")
        content.pack(fill="both", expand=True, padx=20, pady=20)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)
        
        left_col = tk.Frame(content, bg="white")
        left_col.grid(row=0, column=0, padx=(0, 30), sticky="n")

        self.lbl_big_image = tk.Label(left_col, text="[No Image]", bg="#eee", width=400, height=400)
        self.lbl_big_image.pack()
        self.btn_gallery = tk.Button(left_col, text="View All Photos", bg="#6c757d", fg="white", font=("Arial", 10), command=self.open_gallery)
        self.btn_gallery.pack(fill="x", pady=10)

        self.stats_container = tk.Frame(content, bg="white")
        self.stats_container.grid(row=0, column=1, sticky="nsew")
        self.stats_container.columnconfigure(0, weight=1)

        self.fr_basic = tk.LabelFrame(self.stats_container, text="Basic Information", font=("Arial", 10, "bold"), bg="white", padx=10, pady=10)
        self.fr_basic.pack(fill="x", pady=(0, 15))
        self.lbl_species = self.create_info_row(self.fr_basic, 0, "Species:")
        self.lbl_breed = self.create_info_row(self.fr_basic, 1, "Breed:")
        self.lbl_sex = self.create_info_row(self.fr_basic, 2, "Sex:")
        self.lbl_age = self.create_info_row(self.fr_basic, 3, "Age:")
        self.lbl_color = self.create_info_row(self.fr_basic, 4, "Color:")
        self.lbl_source = self.create_info_row(self.fr_basic, 5, "Source:")

        self.fr_compat = tk.LabelFrame(self.stats_container, text="Compatibility", font=("Arial", 10, "bold"), bg="white", padx=10, pady=10)
        self.fr_compat.pack(fill="x", pady=(0, 15))
        self.lbl_dogs = self.create_info_row(self.fr_compat, 0, "With Dogs:")
        self.lbl_cats = self.create_info_row(self.fr_compat, 1, "With Cats:")
        self.lbl_kids = self.create_info_row(self.fr_compat, 2, "With Kids:")

        self.fr_loc = tk.LabelFrame(self.stats_container, text="Location & Contact", font=("Arial", 10, "bold"), bg="white", padx=10, pady=10)
        self.fr_loc.pack(fill="x", pady=(0, 15))
        self.lbl_est = self.create_info_row(self.fr_loc, 0, "Establishment:")
        tk.Label(self.fr_loc, text="More Info:", font=("Arial", 10, "bold"), bg="white").grid(row=1, column=0, sticky="w", pady=2)
        self.lbl_url = tk.Label(self.fr_loc, text="Click here", font=("Arial", 10, "underline"), fg="blue", cursor="hand2", bg="white")
        self.lbl_url.grid(row=1, column=1, sticky="w", pady=2)

        self.fr_action = tk.Frame(self.stats_container, bg="white")
        self.fr_action.pack(fill="x", pady=10)
        self.lbl_match_info = tk.Label(self.fr_action, text="", font=("Arial", 10, "italic"), bg="white", fg="#555")
        self.lbl_match_info.pack(anchor="w")
        self.btn_breed_link = tk.Button(self.fr_action, text="View Breed Details >", bg="#28a745", fg="white", font=("Arial", 10, "bold"))

    def create_info_row(self, parent, row_idx, label_text):
        tk.Label(parent, text=label_text, font=("Arial", 10, "bold"), bg="white").grid(row=row_idx, column=0, sticky="w", pady=2, padx=(0, 10))
        val_label = tk.Label(parent, text="--", font=("Arial", 10), bg="white")
        val_label.grid(row=row_idx, column=1, sticky="w", pady=2)
        return val_label

    def setup_breed_view(self):
        self.breed_canvas = tk.Canvas(self.page_breed, bg="white")
        self.breed_scroll = ttk.Scrollbar(self.page_breed, orient="vertical", command=self.breed_canvas.yview)
        
        self.breed_content_frame = tk.Frame(self.breed_canvas, bg="white")
        self.breed_content_frame.bind("<Configure>", lambda e: self.breed_canvas.configure(scrollregion=self.breed_canvas.bbox("all")))
        self.breed_window_id = self.breed_canvas.create_window((0, 0), window=self.breed_content_frame, anchor="nw")

        def on_canvas_configure(event):
            self.breed_canvas.itemconfig(self.breed_window_id, width=event.width)
        self.breed_canvas.bind("<Configure>", on_canvas_configure)

        self.breed_canvas.pack(side="left", fill="both", expand=True)
        self.breed_scroll.pack(side="right", fill="y")
        self.breed_canvas.configure(yscrollcommand=self.breed_scroll.set)
        
        # Header
        head = tk.Frame(self.breed_content_frame, bg="#e9ecef", height=50)
        head.pack(fill="x", side="top", pady=(0, 20))
        tk.Button(head, text="< Back to Dog", command=self.back_to_dog_from_breed).pack(side="left", padx=10, pady=10)
        self.lbl_breed_title = tk.Label(head, text="Breed Name", font=("Arial", 16, "bold"), bg="#e9ecef")
        self.lbl_breed_title.pack(side="left", padx=20)

        content = tk.Frame(self.breed_content_frame, bg="white", padx=20)
        content.pack(fill="both", expand=True)

        self.fr_standards = tk.LabelFrame(content, text="Breed Standards", font=("Arial", 12, "bold"), bg="white", padx=10, pady=10)
        self.fr_standards.pack(fill="x", pady=(0, 20))
        self.lbl_br_group = self.create_info_row(self.fr_standards, 0, "Group:")
        self.lbl_br_size = self.create_info_row(self.fr_standards, 1, "Size Category:")
        self.lbl_br_height = self.create_info_row(self.fr_standards, 2, "Height:")
        self.lbl_br_weight = self.create_info_row(self.fr_standards, 3, "Weight:")
        self.lbl_br_life = self.create_info_row(self.fr_standards, 4, "Life Span:")

        self.fr_chart = tk.LabelFrame(content, text="Trait Scores", font=("Arial", 12, "bold"), bg="white", padx=10, pady=10)
        self.fr_chart.pack(fill="both", expand=True, pady=(0, 20))
        self.chart_frame = tk.Frame(self.fr_chart, bg="white")
        self.chart_frame.pack(fill="both", expand=True)

    def setup_gallery_view(self):
        self.gal_canvas = tk.Canvas(self.page_gallery, bg="white")
        self.gal_scroll = ttk.Scrollbar(self.page_gallery, orient="vertical", command=self.gal_canvas.yview)
        
        self.gal_content = tk.Frame(self.gal_canvas, bg="white")
        self.gal_content.bind("<Configure>", lambda e: self.gal_canvas.configure(scrollregion=self.gal_canvas.bbox("all")))
        self.gal_win_id = self.gal_canvas.create_window((0, 0), window=self.gal_content, anchor="nw")

        def on_gal_config(event): self.gal_canvas.itemconfig(self.gal_win_id, width=event.width)
        self.gal_canvas.bind("<Configure>", on_gal_config)

        self.gal_canvas.pack(side="left", fill="both", expand=True)
        self.gal_scroll.pack(side="right", fill="y")
        self.gal_canvas.configure(yscrollcommand=self.gal_scroll.set)

        head = tk.Frame(self.gal_content, bg="#e9ecef", height=50)
        head.pack(fill="x", side="top", pady=(0, 20))
        tk.Button(head, text="< Back to Dog", command=self.back_to_dog_from_gallery).pack(side="left", padx=10, pady=10)
        tk.Label(head, text="Photo Gallery", font=("Arial", 16, "bold"), bg="#e9ecef").pack(side="left", padx=20)

        self.gal_grid = tk.Frame(self.gal_content, bg="white")
        self.gal_grid.pack(fill="both", expand=True, padx=20)

    # --- FIX: Global MouseWheel Binding ---
    def _bind_to_mousewheel(self, canvas):
        def _on_mousewheel(event):
            if event.delta: 
                 canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # We bind to the ROOT window so focus doesn't matter,
        # but only when this specific view is active.
        self.root.bind_all("<MouseWheel>", _on_mousewheel)

    def _unbind_mousewheel(self):
        self.root.unbind_all("<MouseWheel>")

    # ================= NAVIGATION =================
    def _hide_all(self):
        self.page_list.grid_remove()
        self.page_detail.grid_remove()
        self.page_breed.grid_remove()
        self.page_gallery.grid_remove()
        self._unbind_mousewheel() # Clean up scrolling

    def show_list_view(self):
        self._hide_all()
        self.page_list.grid()

    def show_detail_view(self):
        self._hide_all()
        self.page_detail.grid()

    def show_breed_view(self):
        self._hide_all()
        self.page_breed.grid()
        self._bind_to_mousewheel(self.breed_canvas) # Activate scroll for Breed

    def show_gallery_view(self):
        self._hide_all()
        self.page_gallery.grid()
        self._bind_to_mousewheel(self.gal_canvas) # Activate scroll for Gallery

    def back_to_dog_from_breed(self):
        self.show_detail_view() if self.current_dog_id else self.show_list_view()

    def back_to_dog_from_gallery(self):
        self.show_detail_view()

    def open_url(self, url):
        if url and url.startswith("http"): webbrowser.open(url)

    # ================= LOGIC =================
    def reset_search(self):
        self.entry_name.delete(0, tk.END)
        self.entry_breed.delete(0, tk.END)
        self.var_junior.set(False); self.var_adult.set(False); self.var_senior.set(False)
        self.var_male.set(False); self.var_female.set(False)
        self.var_spa.set(True); self.var_sc.set(True)
        self.run_search()

    def run_search(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        
        cats = [c for c, v in [("junior", self.var_junior), ("adult", self.var_adult), ("senior", self.var_senior)] if v.get()]
        # Pass "Male" / "Female" directly to search logic
        sexes = [s for s, v in [("Male", self.var_male), ("Female", self.var_female)] if v.get()]
        sources = [s for s, v in [("SPA", self.var_spa), ("Seconde Chance", self.var_sc)] if v.get()]

        results = self.db.search_dogs(self.entry_name.get(), self.entry_breed.get(), cats, sexes, sources)
        for row in results:
            self.tree.insert("", "end", values=(row['id'], row['name'], row['source'], row['age_text']))

    def open_dog_details(self, event):
        sel = self.tree.selection()
        if not sel: return
        self.current_dog_id = self.tree.item(sel)['values'][0]
        self.show_detail_view()
        self.load_dog_data(self.current_dog_id)

    def load_dog_data(self, dog_id):
        self.lbl_big_image.config(image='', text="[No Image]", width=50, height=20)
        dog = self.db.get_dog_details(dog_id)
        
        self.lbl_detail_title.config(text=f"{dog['name']}")
        self.lbl_species.config(text=dog['species'])
        self.lbl_breed.config(text=dog['breed'])
        self.lbl_sex.config(text=dog['sex'])
        self.lbl_age.config(text=f"{dog['age_text']} ({dog['category']})")
        self.lbl_color.config(text=dog['colors'])
        self.lbl_source.config(text=dog['source'])

        def set_compat(l, v):
            l.config(text="Yes" if v else "No", fg="green" if v else "red", font=("Arial", 10, "bold"))
        set_compat(self.lbl_dogs, dog['accepts_dogs'])
        set_compat(self.lbl_cats, dog['accepts_cats'])
        set_compat(self.lbl_kids, dog['accepts_children'])

        self.lbl_est.config(text=dog['establishment'])
        if dog['url']:
            self.lbl_url.config(text=dog['url'][:50] + "...")
            self.lbl_url.bind("<Button-1>", lambda e: self.open_url(dog['url']))
        else:
            self.lbl_url.config(text="--")
            self.lbl_url.unbind("<Button-1>")

        if dog['matched_breed']:
            self.lbl_match_info.config(text=f"Note: This dog is identified as a {dog['matched_breed']}.")
            self.btn_breed_link.config(command=lambda: self.load_breed_data(dog['matched_breed']))
            self.btn_breed_link.pack(pady=5, anchor="w")
        else:
            self.lbl_match_info.config(text="")
            self.btn_breed_link.pack_forget()

        try:
            urls = self.db.get_dog_images(dog_id)
            if urls:
                self.load_image_to_label(urls[0], self.lbl_big_image)
            else:
                self.lbl_big_image.config(text="No Image Available")
        except:
            self.lbl_big_image.config(text="Image Error")

    def open_gallery(self):
        if not self.current_dog_id: return
        self.show_gallery_view()
        
        for w in self.gal_grid.winfo_children(): w.destroy()
        self.gallery_images = [] 
        
        urls = self.db.get_dog_images(self.current_dog_id)
        
        if not urls:
            tk.Label(self.gal_grid, text="No images found for this dog.", bg="white", font=("Arial", 12)).pack(pady=20)
            return

        tk.Label(self.gal_grid, text="Loading images...", bg="white").pack(pady=10)
        self.root.update()
        for w in self.gal_grid.winfo_children(): w.destroy()

        for i, url in enumerate(urls):
            frame = tk.Frame(self.gal_grid, bg="white", padx=10, pady=10)
            frame.grid(row=i//2, column=i%2, sticky="n")
            
            lbl = tk.Label(frame, text="Loading...", bg="#eee", width=400, height=300)
            lbl.pack()
            
            try:
                response = requests.get(url, timeout=2)
                img = Image.open(BytesIO(response.content))
                img.thumbnail((400, 300))
                photo = ImageTk.PhotoImage(img)
                self.gallery_images.append(photo) 
                lbl.config(image=photo, text="", width=400, height=300)
            except:
                lbl.config(text="Error", width=50, height=20)
        
    def load_breed_data(self, breed_name):
        self.show_breed_view()
        self.lbl_breed_title.config(text=breed_name)
        data = self.db.get_breed_info(breed_name)
        
        if data:
            self.lbl_br_group.config(text=data['dog_breed_group'] or "--")
            self.lbl_br_size.config(text=data['dog_size'] or "--")
            self.lbl_br_height.config(text=f"{data['height_text']} ({data['avg_height_cm']} cm)")
            self.lbl_br_weight.config(text=f"{data['weight_text']} ({data['avg_weight_kg']} kg)")
            self.lbl_br_life.config(text=f"{data['life_span_text']} ({data['avg_life_span_years']} years)")
        else:
             return

        for widget in self.chart_frame.winfo_children(): widget.destroy()

        metrics = [
            ("Adaptability", data['adaptability']),
            (" - Apt. Living", data['adapts_well_to_apartment_living']),
            (" - Novice Owners", data['good_for_novice_owners']),
            (" - Sensitivity", data['sensitivity_level']),
            (" - Alone", data['tolerates_being_alone']),
            (" - Cold", data['tolerates_cold_weather']),
            (" - Hot", data['tolerates_hot_weather']),
            ("Friendliness", data['all_around_friendliness']),
            (" - Family", data['affectionate_with_family']),
            (" - Kids", data['kid_friendly']),
            (" - Dogs", data['dog_friendly']),
            (" - Strangers", data['friendly_toward_strangers']),
            ("Health", data['general_health']),
            (" - Shedding", data['amount_of_shedding']),
            (" - Drooling", data['drooling_potential']),
            (" - Grooming", data['easy_to_groom']),
            (" - Weight Gain", data['potential_for_weight_gain']),
            ("Trainability", data['trainability']),
            (" - Easy to Train", data['easy_to_train']),
            (" - Intelligence", data['intelligence']),
            (" - Prey Drive", data['prey_drive']),
            (" - Barking", data['tendency_to_bark_or_howl']),
            ("Energy", data['energy_level']),
            (" - Intensity", data['intensity']),
            (" - Exercise", data['exercise_needs']),
            (" - Playfulness", data['potential_for_playfulness']),
        ]
        labels = [m[0] for m in metrics]
        values = [m[1] if m[1] is not None else 0 for m in metrics]

        fig_height = len(labels) * 0.35 
        fig = Figure(figsize=(6, fig_height), dpi=100)
        ax = fig.add_subplot(111)
        ax.barh(range(len(labels)), values, height=0.6, color='#007bff')
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        ax.set_xlim(0, 5)
        ax.invert_yaxis()
        ax.grid(axis='x', linestyle='--', alpha=0.7)
        ax.set_xlabel("Score (0-5)")
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def load_image_to_label(self, url, label):
        label.config(text="Loading...", image='')
        self.root.update()
        try:
            response = requests.get(url, timeout=3)
            img = Image.open(BytesIO(response.content))
            img.thumbnail((400, 400))
            photo = ImageTk.PhotoImage(img)
            label.config(image=photo, text="", width=400, height=400)
            label.image = photo 
        except:
            label.config(image='', text="Image Unavailable", width=50, height=20)

if __name__ == "__main__":
    root = tk.Tk()
    app = DogApp(root)
    root.mainloop()