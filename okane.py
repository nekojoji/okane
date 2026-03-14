import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import glob
import sys

class KakeiboApp:
    def __init__(self, root):
        self.root = root
        self.root.title("家計簿アプリ - 月別管理")
        self.root.geometry("1400x800")
        
        self.base_path = self.get_base_path()
        self.data_dir = os.path.join(self.base_path, "okane_data")
        if not os.path.exists(self.data_dir): os.makedirs(self.data_dir)
            
        self.fixed_templates = self.load_templates()
        self.tabs = {} 

        # --- キーボードイベントのバインド ---
        self.root.bind("<Return>", lambda e: self.calc_press("="))
        self.root.bind("<KP_Enter>", lambda e: self.calc_press("="))
        self.root.bind("<Escape>", lambda e: self.calc_press("C"))

        # --- UI構築 ---
        tool_frame = ttk.Frame(root)
        tool_frame.pack(fill='x', padx=10, pady=5)
        self.entry_ym = ttk.Entry(tool_frame, width=8)
        self.entry_ym.insert(0, "202603")
        self.entry_ym.pack(side='left', padx=5)
        
        ttk.Button(tool_frame, text="リストに追加", command=self.add_list_item).pack(side='left')
        ttk.Button(tool_frame, text="削除", command=self.delete_sheet).pack(side='left', padx=5)
        ttk.Button(tool_frame, text="保存する", command=self.save_data).pack(side='right')

        main_paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        main_paned.pack(expand=True, fill='both', padx=5, pady=5)

        list_frame = ttk.Frame(main_paned)
        main_paned.add(list_frame, weight=0)
        self.listbox = tk.Listbox(list_frame, font=("Arial", 12), width=8)
        self.listbox.pack(expand=True, fill='both', padx=2, pady=5)
        self.listbox.bind('<<ListboxSelect>>', self.on_select_list)

        self.right_frame = ttk.Frame(main_paned)
        main_paned.add(self.right_frame, weight=3)

        # --- 計算機エリア ---
        self.calc_area = tk.Frame(main_paned, bd=2, relief="groove", bg="#F0F0F0")
        main_paned.add(self.calc_area, weight=0)
        self.calc_area.bind("<Enter>", lambda e: self.calc_area.configure(bg="#E0F7FA"))
        self.calc_area.bind("<Leave>", lambda e: self.calc_area.configure(bg="#F0F0F0"))
        
        tk.Label(self.calc_area, text="計算機エリア(カーソルホバーで有効)\nYou can use the calculator here.", fg="blue", bg="#F0F0F0").pack(pady=5)
        self.calc_display = tk.Entry(self.calc_area, font=("Arial", 24), width=12, justify="right")
        self.calc_display.pack(pady=10, padx=10)
        
        btn_container = tk.Frame(self.calc_area, bg="#F0F0F0")
        btn_container.pack(pady=5)
        buttons = [["7","8","9","/"],["4","5","6","*"],["1","2","3","-"],["0","C","=","+"],["Enter","Copy"]]
        for row in buttons:
            r_f = tk.Frame(btn_container, bg="#F0F0F0")
            r_f.pack(fill='x')
            for b in row:
                tk.Button(r_f, text=b, width=6, height=2, font=("Arial", 16, "bold"), 
                          command=lambda x=b: self.calc_press(x)).pack(side="left", padx=2, pady=2)

        self.lbl_total = tk.Label(root, text="収入: 0 | 支出: 0 | 収支: 0", font=("Arial", 16, "bold"), bg="#9400d3", fg="white", relief="sunken")
        self.lbl_total.pack(fill='x', padx=10, pady=5)

        self.restore_all_sheets()
        root.after(100, lambda: main_paned.sashpos(0, 100))

    def get_base_path(self):
        if getattr(sys, 'frozen', False): return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.dirname(os.path.abspath(__file__))

    def load_templates(self):
        path = os.path.join(self.base_path, "categories.txt")
        return [line.strip() for line in open(path, "r", encoding="utf-8")] if os.path.exists(path) else []

    def calc_press(self, key):
        if key == "C": self.calc_display.delete(0, tk.END)
        elif key == "=" or key == "Enter":
            try:
                res = eval(self.calc_display.get())
                self.calc_display.delete(0, tk.END); self.calc_display.insert(0, str(res))
            except: self.calc_display.insert(tk.END, "Error")
        elif key == "Copy":
            self.root.clipboard_clear(); self.root.clipboard_append(self.calc_display.get())
        else: self.calc_display.insert(tk.END, key)

    def create_sheet_ui(self, name):
        frame = ttk.Frame(self.right_frame)
        income = self.create_list_section(frame, "収入", 0)
        expense = self.create_list_section(frame, "支出", 1)
        fixed = self.create_list_section(frame, "固定費", 2, is_fixed=True)
        self.tabs[name] = {"frame": frame, "income": income, "expense": expense, "fixed": fixed}
        self.load_sheet_data(name)
        frame.pack_forget()

    def create_list_section(self, parent, title, col_idx, is_fixed=False):
        frame = ttk.LabelFrame(parent, text=title)
        frame.grid(row=0, column=col_idx, padx=2, sticky='nsew')
        parent.columnconfigure(col_idx, weight=1)
        for i, h in enumerate(["品目", "日付", "金額"]): tk.Label(frame, text=h).grid(row=0, column=i)
        rows = []
        for i in range(1, 16):
            item, date, amt = tk.Entry(frame, width=12), tk.Entry(frame, width=6), tk.Entry(frame, width=8)
            if is_fixed and i <= len(self.fixed_templates): item.insert(0, self.fixed_templates[i-1])
            item.grid(row=i, column=0, padx=1, pady=1); date.grid(row=i, column=1, padx=1, pady=1); amt.grid(row=i, column=2, padx=1, pady=1)
            amt.bind("<KeyRelease>", self.update_totals)
            rows.append((item, date, amt))
        return rows

    def add_list_item(self):
        name = self.entry_ym.get()
        if name and name not in self.tabs:
            self.listbox.insert(tk.END, name); self.create_sheet_ui(name)

    def on_select_list(self, event):
        selection = self.listbox.curselection()
        if not selection: return
        name = self.listbox.get(selection[0])
        for n, data in self.tabs.items(): data["frame"].pack_forget()
        self.tabs[name]["frame"].pack(expand=True, fill='both')
        self.update_totals()

    def restore_all_sheets(self):
        files = sorted(glob.glob(os.path.join(self.data_dir, "data_*.json")))
        for file in files:
            name = os.path.basename(file).replace("data_", "").replace(".json", "")
            self.listbox.insert(tk.END, name); self.create_sheet_ui(name)

    def delete_sheet(self):
        selection = self.listbox.curselection()
        if not selection: return
        idx = selection[0]; name = self.listbox.get(idx)
        if messagebox.askyesno("削除", f"{name} を削除しますか？"):
            path = os.path.join(self.data_dir, f"data_{name}.json")
            if os.path.exists(path): os.remove(path)
            self.tabs[name]["frame"].destroy(); del self.tabs[name]; self.listbox.delete(idx)

    def save_data(self):
        selection = self.listbox.curselection()
        if not selection: return
        name = self.listbox.get(selection[0])
        data = {key: [[r[0].get(), r[1].get(), r[2].get()] for r in self.tabs[name][key]] for key in ["income", "expense", "fixed"]}
        with open(os.path.join(self.data_dir, f"data_{name}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        messagebox.showinfo("保存", f"{name} を保存しました")

    def load_sheet_data(self, name):
        path = os.path.join(self.data_dir, f"data_{name}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key in ["income", "expense", "fixed"]:
                    for i, vals in enumerate(data.get(key, [])):
                        for j in range(3): self.tabs[name][key][i][j].delete(0, tk.END); self.tabs[name][key][i][j].insert(0, vals[j])

    def update_totals(self, event=None):
        selection = self.listbox.curselection()
        if not selection: return
        name = self.listbox.get(selection[0])
        rows = self.tabs[name]
        inc = sum([float(r[2].get() or 0) for r in rows["income"]])
        exp = sum([float(r[2].get() or 0) for r in rows["expense"]]) + sum([float(r[2].get() or 0) for r in rows["fixed"]])
        self.lbl_total.config(text=f"収入: {inc:,.0f} | 支出: {exp:,.0f} | 収支: {inc-exp:,.0f}")

root = tk.Tk()
app = KakeiboApp(root)
root.mainloop()