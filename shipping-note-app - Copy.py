import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import pandas as pd
import sqlite3
import reportlab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

class OperaterLogin:
    def __init__(self, master):
        self.master = master
        master.title("Prijava Operatera")
        master.geometry("300x200")

        tk.Label(master, text="Korisničko ime:").pack(pady=5)
        self.username_entry = tk.Entry(master)
        self.username_entry.pack(pady=5)

        tk.Label(master, text="Lozinka:").pack(pady=5)
        self.password_entry = tk.Entry(master, show="*")
        self.password_entry.pack(pady=5)

        tk.Button(master, text="Prijava", command=self.login).pack(pady=10)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        # Ovde dodati logiku validacije korisnika iz baze
        if username and password:
            self.master.destroy()
            root = tk.Tk()
            app = OtpremnicaApp(root)
            root.mainloop()
        else:
            messagebox.showerror("Greška", "Unesite korisničko ime i lozinku")

class OtpremnicaApp:
    def __init__(self, master):
        self.master = master
        master.title("Sistem za Izdavanje Otpremnica")
        master.geometry("1200x800")

        # Inicijalizacija baze podataka
        self.init_database()

        # Registrovanje UTF-8 fonts za PDF
        self.register_fonts()

        # Meni bar
        menubar = tk.Menu(master)
        master.config(menu=menubar)

        # Meni za pregled otpremnica
        otpremnice_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Otpremnice", menu=otpremnice_menu)
        otpremnice_menu.add_command(label="Pregled sačuvanih otpremnica", command=self.view_saved_shipping_notes)

        # Uvoz artikala iz Excel-a
        self.import_excel_button = tk.Button(master, text="Uvoz Artikala", command=self.import_excel)
        self.import_excel_button.pack(pady=10)

        # Pretraga artikala
        tk.Label(master, text="Pretraga artikala:").pack()
        self.search_entry = tk.Entry(master, width=50)
        self.search_entry.pack()
        tk.Button(master, text="Pretraži", command=self.search_articles).pack(pady=5)

        # Tabela za pretragu artikala
        self.search_tree = ttk.Treeview(master, columns=("Šifra", "Naziv", "Jedinica mere"), show="headings")
        self.search_tree.heading("Šifra", text="Šifra")
        self.search_tree.heading("Naziv", text="Naziv")
        self.search_tree.heading("Jedinica mere", text="Jedinica mere")
        self.search_tree.pack(pady=10, fill=tk.BOTH, expand=True)
        self.search_tree.bind("<Double-1>", self.add_to_cart)

        # Korpa za otpremnicu
        tk.Label(master, text="Artikli u otpremnici:").pack()
        self.cart_tree = ttk.Treeview(master, columns=("Šifra", "Naziv", "Jedinica mere", "Tražena količina", "Izdata količina"), show="headings")
        self.cart_tree.heading("Šifra", text="Šifra")
        self.cart_tree.heading("Naziv", text="Naziv")
        self.cart_tree.heading("Jedinica mere", text="Jedinica mere")
        self.cart_tree.heading("Tražena količina", text="Tražena količina")
        self.cart_tree.heading("Izdata količina", text="Izdata količina")
        self.cart_tree.pack(pady=10, fill=tk.BOTH, expand=True)

        # Buttons za brisanje i generisanje PDF-a
        button_frame = tk.Frame(master)
        button_frame.pack(pady=5)

        tk.Button(button_frame, text="Obriši selektovan artikal", command=self.remove_from_cart).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Generiši PDF Otpremnicu", command=self.generate_pdf).pack(side=tk.LEFT, padx=5)

    def register_fonts(self):
        # Registrovanje UTF-8 fontova za PDF
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))

    def init_database(self):
        # Kreiranje SQLite baze i tabela
        self.conn = sqlite3.connect('otpremnice.db')
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS artikli (
                sifra TEXT PRIMARY KEY,
                naziv TEXT,
                jedinica_mere TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS otpremnice (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datum DATE,
                pdf_putanja TEXT,
                sadrzaj TEXT
            )
        ''')
        
        self.conn.commit()

    def import_excel(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file_path:
            df = pd.read_excel(file_path)
            
            # Provera strukture Excel fajla
            expected_columns = ['sifra', 'naziv', 'jedinica_mere']
            if not all(col in df.columns for col in expected_columns):
                messagebox.showerror("Greška", "Pogrešan format Excel fajla")
                return

            # Unos artikala u bazu
            for _, row in df.iterrows():
                self.cursor.execute('''
                    INSERT OR REPLACE INTO artikli (sifra, naziv, jedinica_mere) 
                    VALUES (?, ?, ?)
                ''', (row['sifra'], row['naziv'], row['jedinica_mere']))
            
            self.conn.commit()
            messagebox.showinfo("Uspeh", "Artikli uvezeni uspešno")

    def search_articles(self):
        search_term = self.search_entry.get()
        
        # Pretraga po bilo kom kriterijumu
        self.cursor.execute('''
            SELECT sifra, naziv, jedinica_mere 
            FROM artikli 
            WHERE sifra LIKE ? OR naziv LIKE ? OR jedinica_mere LIKE ?
        ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
        
        results = self.cursor.fetchall()
        
        # Brisanje prethodnih rezultata
        for i in self.search_tree.get_children():
            self.search_tree.delete(i)
        
        for result in results:
            self.search_tree.insert("", tk.END, values=result)

    def add_to_cart(self, event):
        selected_item = self.search_tree.selection()
        if selected_item:
            item_details = self.search_tree.item(selected_item)['values']
            
            # Dijalog za unos tražene i date količine
            quantity_dialog = tk.Toplevel(self.master)
            quantity_dialog.title("Unos Količina")
            
            tk.Label(quantity_dialog, text="Tražena količina:").pack()
            requested_quantity_entry = tk.Entry(quantity_dialog)
            requested_quantity_entry.pack()

            tk.Label(quantity_dialog, text="Izdata količina:").pack()
            issued_quantity_entry = tk.Entry(quantity_dialog)
            issued_quantity_entry.pack()
            
            def confirm_quantity():
                try:
                    requested_quantity = float(requested_quantity_entry.get())
                    issued_quantity = float(issued_quantity_entry.get())
                    
                    if issued_quantity > requested_quantity:
                        messagebox.showerror("Greška", "Izdata količina ne može biti veća od tražene")
                        return

                    self.cart_tree.insert("", tk.END, values=(*item_details, requested_quantity, issued_quantity))
                    quantity_dialog.destroy()
                except ValueError:
                    messagebox.showerror("Greška", "Unesite validne brojeve")
            
            tk.Button(quantity_dialog, text="Potvrdi", command=confirm_quantity).pack()

    def remove_from_cart(self):
        selected_item = self.cart_tree.selection()
        if selected_item:
            self.cart_tree.delete(selected_item)

    def generate_pdf(self):
        cart_items = [self.cart_tree.item(item)['values'] for item in self.cart_tree.get_children()]
        
        if not cart_items:
            messagebox.showerror("Greška", "Korpa je prazna")
            return

        # Generisanje PDF-a
        pdf_path = f"otpremnica_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        title_style.fontName = 'DejaVuSans-Bold'
        
        # Naslov dokumenta
        title = Paragraph("Otpremnica", title_style)
        
        # Pripema podataka za tabelu
        data = [['Šifra', 'Naziv', 'Jedinica mere', 'Tražena količina', 'Izdata količina']] + cart_items
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,-1), 'DejaVuSans'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        
        elements = [title, table]
        doc.build(elements)

        # Čuvanje informacija o otpremnici u bazi
        sadrzaj = '\n'.join([' | '.join(map(str, item)) for item in cart_items])
        self.cursor.execute('INSERT INTO otpremnice (datum, pdf_putanja, sadrzaj) VALUES (?, ?, ?)', 
                            (pd.Timestamp.now(), pdf_path, sadrzaj))
        self.conn.commit()

        messagebox.showinfo("Uspeh", f"PDF otpremnica generisana: {pdf_path}")

    def view_saved_shipping_notes(self):
        # Prozor za pregled otpremnica
        shipping_window = tk.Toplevel(self.master)
        shipping_window.title("Sačuvane Otpremnice")
        shipping_window.geometry("800x400")

        # Tabela za prikaz otpremnica
        columns = ("ID", "Datum", "PDF Putanja", "Sadržaj")
        shipping_tree = ttk.Treeview(shipping_window, columns=columns, show="headings")
        for col in columns:
            shipping_tree.heading(col, text=col)
        shipping_tree.pack(fill=tk.BOTH, expand=True)

        # Učitavanje otpremnica iz baze
        self.cursor.execute('SELECT * FROM otpremnice')
        otpremnice = self.cursor.fetchall()

        for otpremnica in otpremnice:
            shipping_tree.insert("", tk.END, values=otpremnica)

        def open_pdf(event):
            selected_item = shipping_tree.selection()
            if selected_item:
                pdf_path = shipping_tree.item(selected_item)['values'][2]
                try:
                    os.startfile(pdf_path)
                except Exception as e:
                    messagebox.showerror("Greška", f"Nije moguće otvoriti PDF: {e}")

        shipping_tree.bind("<Double-Click>", open_pdf)

# Pokretanje aplikacije
if __name__ == "__main__":
    root = tk.Tk()
    login_window = OperaterLogin(root)
    root.mainloop()
