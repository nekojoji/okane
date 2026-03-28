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

        # --- UI構築 ---
        tool_frame = ttk.Frame(root)
        tool_frame.pack(fill='x', padx=10, pady=5)
        self.entry_ym = ttk.Entry(tool_frame, width=8)
        self.entry_ym.insert(0, "202603")
        self.entry_ym.pack(side='left', padx=5)
        
        ttk.Button(tool_frame, text="リストに追加", command=self.add_list_item).pack(side='left')
        ttk.Button(tool_frame, text="削除", command=self.delete_sheet).pack(side='left', padx=5)
        ttk.Button(tool_frame, text="保存する", command=self.save_data).pack(side='right')

        # PanedWindowで左右分割（左リスト、右メイン）
        self.main_paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_paned.pack(expand=True, fill='both', padx=5, pady=5)

        # 左側リスト
        list_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(list_frame, weight=0)
        self.listbox = tk.Listbox(list_frame, font=("Arial", 12), width=10)
        self.listbox.pack(expand=True, fill='both', padx=2, pady=5)
        self.listbox.bind('<<ListboxSelect>>', self.on_select_list)

        # 右側メインエリア
        self.right_paned = ttk.PanedWindow(self.main_paned, orient=tk.HORIZONTAL)
        self.main_paned.add(self.right_paned, weight=1)

        # 右側家計簿エリア（Canvasでスクロール対応）
        self.right_container = ttk.Frame(self.right_paned)
        self.right_paned.add(self.right_container, weight=1)

        # --- 計算機エリア ---
        self.calc_area = tk.Frame(self.right_paned, bd=2, relief="groove", bg="#F0F0F0")
        self.right_paned.add(self.calc_area, weight=0)
        self.calc_area.bind("<Enter>", self.on_calc_enter)
        self.calc_area.bind("<Leave>", self.on_calc_leave)
        
        tk.Label(self.calc_area, text="計算機(ホバーで有効)", fg="blue", bg="#F0F0F0").pack(pady=5)
        self.calc_display = tk.Entry(self.calc_area, font=("Arial", 24), width=12, justify="right")
        self.calc_display.pack(pady=10, padx=10)
        
        btn_container = tk.Frame(self.calc_area, bg="#F0F0F0")
        btn_container.pack(pady=5)
        buttons = [["7","8","9","/"],["4","5","6","*"],["1","2","3","-"],["0","C","=","+"],["Enter","Copy"]]
        for row in buttons:
            r_f = tk.Frame(btn_container, bg="#F0F0F0")
            r_f.pack()
            for b in row:
                tk.Button(r_f, text=b, width=5, height=2, font=("Arial", 14, "bold"), 
                          command=lambda x=b: self.calc_press(x)).pack(side="left", padx=1, pady=1)

        self.lbl_total = tk.Label(root, text="収入: 0 | 支出: 0 | 収支: 0", font=("Arial", 16, "bold"), bg="#9400d3", fg="white", relief="sunken")
        self.lbl_total.pack(fill='x', padx=10, pady=5)

        self.restore_all_sheets()
        root.after(200, lambda: self.main_paned.sashpos(0, 150))

    def get_base_path(self):
        if getattr(sys, 'frozen', False): return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.dirname(os.path.abspath(__file__))

    def load_templates(self):
        path = os.path.join(self.base_path, "categories.txt")
        return [line.strip() for line in open(path, "r", encoding="utf-8")] if os.path.exists(path) else []

    def on_calc_enter(self, event):
        self.calc_area.configure(bg="#E0F7FA")
        self.root.bind("<Return>", lambda e: self.calc_press("Enter"))
        self.root.bind("<KP_Enter>", lambda e: self.calc_press("Enter"))
        self.root.bind("<Escape>", lambda e: self.calc_press("C"))

    def on_calc_leave(self, event):
        self.calc_area.configure(bg="#F0F0F0")
        self.root.unbind("<Return>"); self.root.unbind("<KP_Enter>"); self.root.unbind("<Escape>")

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
        canvas = tk.Canvas(self.right_container)
        vsb = ttk.Scrollbar(self.right_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((10, 10), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        
        income = self.create_list_section(scrollable_frame, "収入", 0)
        expense = self.create_list_section(scrollable_frame, "支出", 1)
        fixed = self.create_list_section(scrollable_frame, "固定費", 2, is_fixed=True)
        
        self.tabs[name] = {"frame": canvas, "vsb": vsb, "income": income, "expense": expense, "fixed": fixed}
        self.load_sheet_data(name)
        canvas.pack_forget()
        vsb.pack_forget()

    def create_list_section(self, parent, title, col_idx, is_fixed=False):
        frame = ttk.LabelFrame(parent, text=title)
        frame.grid(row=0, column=col_idx, padx=5, pady=5, sticky='n')
        for i, h in enumerate(["品目", "日付", "金額"]): tk.Label(frame, text=h).grid(row=0, column=i)
        rows = []
        for i in range(1, 41): # 40行
            item = tk.Entry(frame, width=22)
            date = tk.Entry(frame, width=8)
            amt = tk.Entry(frame, width=10)
            if is_fixed and i <= len(self.fixed_templates): item.insert(0, self.fixed_templates[i-1])
            item.grid(row=i, column=0, padx=2, pady=1)
            date.grid(row=i, column=1, padx=2, pady=1)
            amt.grid(row=i, column=2, padx=2, pady=1)
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
        for n, data in self.tabs.items(): 
            data["frame"].pack_forget()
            data["vsb"].pack_forget()
        self.tabs[name]["frame"].pack(side="left", expand=True, fill='both')
        self.tabs[name]["vsb"].pack(side="right", fill='y')
        self.update_totals()

    def restore_all_sheets(self):
        files = sorted(glob.glob(os.path.join(self.data_dir, "data_*.json")))
        for file in files:
            name = os.path.basename(file).replace("data_", "").replace(".json", "")
            self.listbox.insert(tk.END, name); self.create_sheet_ui(name)
        if self.listbox.size() > 0:
            self.listbox.select_set(0); self.on_select_list(None)

    def delete_sheet(self):
        selection = self.listbox.curselection()
        if not selection: return
        idx = selection[0]; name = self.listbox.get(idx)
        if messagebox.askyesno("削除", f"{name} を削除しますか？"):
            path = os.path.join(self.data_dir, f"data_{name}.json")
            if os.path.exists(path): os.remove(path)
            self.tabs[name]["frame"].destroy()
            self.tabs[name]["vsb"].destroy()
            del self.tabs[name]; self.listbox.delete(idx)

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