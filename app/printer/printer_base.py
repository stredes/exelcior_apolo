class PrinterBase:
    def print(self, filepath, mode, config_columns, df):
        raise NotImplementedError("Este método debe ser implementado por una subclase")
