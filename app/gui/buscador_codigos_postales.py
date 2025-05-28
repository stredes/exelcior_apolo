import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from pathlib import Path

from app.core.logger_eventos import capturar_log_bod1
from app.utils.utils import guardar_ultimo_path, load_config_from_file

class BuscadorCodigosPostales(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Buscador de Códigos Postales")
        self.geometry("800x500")
        self.config(bg="#F9FAFB")

        self.df = self._cargar_datos_excel()
        if self.df.empty:
            self.destroy()
            return
        self._crear_widgets()

    def _cargar_datos_excel(self) -> pd.DataFrame:
        config = load_config_from_file()
        ruta_config = config.get("archivo_codigos_postales")

        if not ruta_config or not Path(ruta_config).exists():
            ruta_config = filedialog.askopenfilename(
                title="Selecciona el archivo de Códigos Postales",
                filetypes=[("Archivos Excel", "*.xlsx *.xls")]
            )
            if not ruta_config:
                messagebox.showerror("Error", "Archivo no seleccionado.")
                self.destroy()
                return pd.DataFrame()
            guardar_ultimo_path(ruta_config, clave="archivo_codigos_postales")
            capturar_log_bod1(f"Ruta de códigos postales guardada: {ruta_config}", "info")

        try:
            df = pd.read_excel(ruta_config, header=1)
            df.columns = df.columns.str.strip()  # Eliminar espacios en los encabezados

            df.rename(columns={
                "Comuna/Localidad": "COMUNA",
                "Provincia": "PROVINCIA",
                "Region": "REGIÓN",
                "Codigo Postal": "CÓDIGO POSTAL"
            }, inplace=True)

            columnas_esperadas = {"REGIÓN", "COMUNA", "CÓDIGO POSTAL"}
            if not columnas_esperadas.issubset(set(df.columns)):
                raise ValueError(f"Faltan columnas requeridas: {columnas_esperadas - set(df.columns)}")

            capturar_log_bod1(f"Archivo de códigos postales cargado: {ruta_config}", "info")
            return df

        except Exception as e:
            capturar_log_bod1(f"Error al cargar archivo de códigos postales: {e}", "error")
            messagebox.showerror("Error", str(e))
            self.destroy()
            return pd.DataFrame()

    def _crear_widgets(self):
        frame_busqueda = tk.Frame(self, bg="#F9FAFB")
        frame_busqueda.pack(pady=10)

        tk.Label(frame_busqueda, text="Buscar por Comuna o Región:",
                 bg="#F9FAFB", font=("Segoe UI", 11)).grid(row=0, column=0, padx=5)

        self.entrada_busqueda = tk.Entry(frame_busqueda, width=40)
        self.entrada_busqueda.grid(row=0, column=1, padx=5)
        self.entrada_busqueda.bind("<Return>", lambda event: self._buscar())

        btn_buscar = ttk.Button(frame_busqueda, text="Buscar", command=self._buscar)
        btn_buscar.grid(row=0, column=2, padx=5)

        self.tree = ttk.Treeview(self, columns=("REGIÓN", "COMUNA", "CÓDIGO POSTAL"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=200)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.btn_copiar = ttk.Button(self, text="Copiar Código Postal", command=self._copiar_codigo_postal)
        self.btn_copiar.pack(pady=(0, 10))
        self.btn_copiar["state"] = "disabled"

        self.tree.bind("<<TreeviewSelect>>", self._habilitar_boton_copiar)

    def _buscar(self):
        termino = self.entrada_busqueda.get().strip().lower()
        if not termino:
            messagebox.showinfo("Buscar", "Debe ingresar una comuna o región.")
            return

        df_filtrado = self.df[
            self.df["COMUNA"].astype(str).str.lower().str.contains(termino) |
            self.df["REGIÓN"].astype(str).str.lower().str.contains(termino)
        ]

        self.tree.delete(*self.tree.get_children())
        if df_filtrado.empty:
            messagebox.showinfo("Sin resultados", "No se encontraron coincidencias.")
            self.btn_copiar["state"] = "disabled"
        else:
            for _, row in df_filtrado.iterrows():
                self.tree.insert("", "end", values=(row["REGIÓN"], row["COMUNA"], row["CÓDIGO POSTAL"]))
            capturar_log_bod1(f"Búsqueda exitosa: '{termino}', resultados: {len(df_filtrado)}", "info")

    def _habilitar_boton_copiar(self, event=None):
        seleccion = self.tree.selection()
        if seleccion:
            self.btn_copiar["state"] = "normal"
        else:
            self.btn_copiar["state"] = "disabled"

    def _copiar_codigo_postal(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Copia", "Seleccione una fila primero.")
            return

        item = self.tree.item(seleccion[0])
        codigo_postal = item["values"][2]
        self.clipboard_clear()
        self.clipboard_append(str(codigo_postal))
        self.update()
        messagebox.showinfo("Copiado", f"Código Postal copiado: {codigo_postal}")
