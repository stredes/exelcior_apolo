class PrinterBase:
    def print(self, filepath, mode, config_columns, df):
        raise NotImplementedError("Este m�todo debe ser implementado por una subclase")
